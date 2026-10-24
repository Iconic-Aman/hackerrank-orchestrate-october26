from __future__ import annotations
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from backend.agent.models import Fact, Coverage

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

            # Guess system_id from table name or fallback
            default_sys = "account_service" if "account" in tbl else "data_store"

            coverage.append(
                Coverage(
                    file_id=file_id,
                    system_id=default_sys,
                    collection=tbl,
                    captured_at=cap_time,
                    row_count=len(rows),
                )
            )

            for r_idx, row_data in enumerate(rows):
                fields = {col_names[i]: (str(row_data[i]) if row_data[i] is not None else None) for i in range(len(col_names))}
                
                # Identify resource_id
                res_id = fields.get("resource_id") or fields.get("id") or f"{tbl}_{r_idx}"
                prefix = res_id.rsplit("_", 1)[0] if "_" in res_id else res_id
                system_id = sys_map.get(prefix, default_sys)
                
                raw_state = fields.get("account_status") or fields.get("status")
                facts.append(
                    Fact(
                        file_id=file_id,
                        system_id=system_id,
                        collection=tbl,
                        resource_id=str(res_id),
                        category="USER_PROFILE" if "profile" in tbl else None,
                        raw_state=raw_state,
                        fields=fields,
                        locator=f"{tbl}:rowid_{r_idx}",
                        confidence=1.0,
                    )
                )
    finally:
        conn.close()

    return facts, coverage
