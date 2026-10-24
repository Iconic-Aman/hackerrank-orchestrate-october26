from __future__ import annotations
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from backend.agent.models import Fact, Coverage

TABLE_CATEGORIES = {
    "customer_profiles": "USER_PROFILE",
    "customer_profiles_primary": "USER_PROFILE",
    "customer_profiles_failover_replica": "USER_PROFILE",
    "customer_search_documents": "SEARCH_INDEX_ENTRY",
    "customer_analytics_profiles": "ANALYTICS_PROFILE",
    "support_records": "SUPPORT_MESSAGE",
    "customer_exports": "USER_EXPORT",
    "connector_subscriptions": "DATA_FLOW",
    "backup_restore_entries": "BACKUP_ARCHIVE",
    "security_audit_records": "SECURITY_AUDIT_LOG",
}

def parse_sql_snapshot(
    file_path: Path | str,
    file_id: str,
    default_time: datetime | None = None,
    resource_system_map: dict[str, str] | None = None,
) -> tuple[list[Fact], list[Coverage]]:
    path = Path(file_path)
    facts: list[Fact] = []
    coverage: list[Coverage] = []
    sys_map = resource_system_map or {}

    with open(path, "r", encoding="utf-8") as f:
        sql_text = f.read()

    cap_time = default_time or datetime.now()
    m = re.search(r"-- Captured at:\s*([^\r\n]+)", sql_text)
    if m:
        try:
            cap_time = datetime.fromisoformat(m.group(1).strip().replace("Z", "+00:00"))
        except Exception:
            pass

    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(sql_text)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [r[0] for r in cursor.fetchall()]

        for tbl in tables:
            cursor.execute(f"PRAGMA table_info('{tbl}')")
            col_info = cursor.fetchall()
            col_names = [c[1] for c in col_info]

            cursor.execute(f"SELECT * FROM '{tbl}'")
            rows = cursor.fetchall()

            category = TABLE_CATEGORIES.get(tbl, "USER_PROFILE" if "profile" in tbl else None)
            default_sys = "account_service"
            if category == "BACKUP_ARCHIVE":
                default_sys = "backup_service"
            elif category == "DATA_FLOW":
                default_sys = "integration_service"
            elif category == "SEARCH_INDEX_ENTRY":
                default_sys = "search_service"
            elif category == "ANALYTICS_PROFILE":
                default_sys = "analytics_platform"
            elif category == "SECURITY_AUDIT_LOG":
                default_sys = "security_service"
            elif category == "SUPPORT_MESSAGE":
                default_sys = "support_platform"

            coverage.append(
                Coverage(file_id=file_id, system_id=default_sys, collection=tbl, captured_at=cap_time, row_count=len(rows))
            )

            for r_idx, row_data in enumerate(rows):
                fields = {col_names[i]: (str(row_data[i]) if row_data[i] is not None else None) for i in range(len(col_names))}
                res_id = fields.get("resource_id") or fields.get("id") or f"{tbl}_{r_idx}"
                prefix = str(res_id).rsplit("_", 1)[0] if "_" in str(res_id) else str(res_id)
                system_id = sys_map.get(prefix, default_sys)

                # Determine raw_state
                raw_state = fields.get("account_status") or fields.get("status")
                if fields.get("restore_allowed") == "1":
                    raw_state = "ACTIVE"
                elif fields.get("restore_allowed") == "0":
                    raw_state = "BLOCKED"
                elif fields.get("connector_active") == "1" or fields.get("enabled") == "1":
                    raw_state = "ACTIVE"
                elif fields.get("connector_active") == "0" or fields.get("enabled") == "0":
                    raw_state = "DISABLED"
                elif not raw_state:
                    raw_state = "PRESENT"

                facts.append(
                    Fact(
                        file_id=file_id,
                        system_id=system_id,
                        collection=tbl,
                        resource_id=str(res_id),
                        category=category,
                        raw_state=raw_state,
                        fields=fields,
                        locator=f"{tbl}:rowid_{r_idx}",
                        confidence=1.0,
                    )
                )
    finally:
        conn.close()

    return facts, coverage
