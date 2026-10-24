from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from backend.agent.models import Fact, Coverage

def parse_log_lines(
    file_path: Path | str,
    file_id: str,
    default_time: datetime | None = None,
    resource_system_map: dict[str, str] | None = None,
) -> tuple[list[Fact], list[Coverage]]:
    path = Path(file_path)
    facts: list[Fact] = []
    systems_seen: set[str] = set()
    sys_map = resource_system_map or {}
    latest_time = default_time or datetime.now()
    trace_to_ident: dict[str, str] = {}

    # First pass: collect trace_id -> identifier mappings
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            kv_matches = re.findall(r'(\w+)=(?:"([^"]*)"|(\S+))', s)
            fields = {k: (v1 if v1 != "" else v2) for k, v1, v2 in kv_matches}
            t_id = fields.get("trace_id")
            ident = fields.get("lookup_key") or fields.get("subject_key") or fields.get("correlation_key") or fields.get("match_key")
            if t_id and ident:
                trace_to_ident[t_id] = ident

    # Second pass: construct facts
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue

            parts = s.split(maxsplit=1)
            ts_str = parts[0]
            try:
                line_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if default_time is None or line_time > latest_time:
                    latest_time = line_time
            except Exception:
                pass

            kv_matches = re.findall(r'(\w+)=(?:"([^"]*)"|(\S+))', s)
            fields = {k: (v1 if v1 != "" else v2) for k, v1, v2 in kv_matches}
            fields["raw_line"] = s

            t_id = fields.get("trace_id")
            if t_id and t_id in trace_to_ident and not fields.get("lookup_key"):
                fields["lookup_key"] = trace_to_ident[t_id]

            res_id = fields.get("resource_id")
            service = fields.get("service", "unknown_service")

            if res_id:
                prefix = res_id.rsplit("_", 1)[0] if "_" in res_id else res_id
                system_id = sys_map.get(prefix, service)
            else:
                system_id = service
            systems_seen.add(system_id)

            ev = fields.get("event", "")
            if ev.endswith("_started"):
                continue  # Ignore transient query start lines

            rows_val = fields.get("rows")
            http_val = fields.get("http_status")
            enabled_val = fields.get("enabled")
            marker_found = fields.get("marker_found")

            if rows_val == "0" or http_val == "404":
                raw_state = "ABSENT"
            elif rows_val == "1" or marker_found == "false":
                raw_state = "PRESENT"
            elif enabled_val == "false" or fields.get("last_delivery_status") == "stopped":
                raw_state = "DISABLED"
            elif enabled_val == "true":
                raw_state = "ACTIVE"
            elif fields.get("blocked") == "true":
                raw_state = "BLOCKED"
            elif fields.get("anonymized") == "true":
                raw_state = "ANONYMIZED"
            else:
                raw_state = "PRESENT" if res_id else ev

            if res_id or fields.get("lookup_key") or fields.get("match_key"):
                category = "DATA_FLOW" if "data_flow" in (res_id or "") else ("SUPPORT_MESSAGE" if "support" in system_id else None)
                facts.append(
                    Fact(
                        file_id=file_id,
                        system_id=system_id,
                        collection="log_stream",
                        resource_id=res_id or f"log_entry_{idx}",
                        category=category,
                        raw_state=raw_state,
                        fields=fields,
                        locator=f"line:{idx}",
                        confidence=1.0,
                    )
                )

    coverage = [
        Coverage(
            file_id=file_id,
            system_id=sys,
            collection="log_stream",
            captured_at=latest_time,
            row_count=sum(1 for f in facts if f.system_id == sys),
        )
        for sys in sorted(systems_seen)
    ]
    return facts, coverage
