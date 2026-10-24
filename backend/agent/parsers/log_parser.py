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

    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue

            parts = s.split()
            if not parts:
                continue

            ts_str = parts[0]
            try:
                line_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if default_time is None or line_time > latest_time:
                    latest_time = line_time
            except Exception:
                pass

            # Extract key=value pairs
            kv_pairs = re.findall(r'(\w+)=([^\s]+)', s)
            fields = {k: v for k, v in kv_pairs}
            fields["raw_line"] = s

            res_id = fields.get("resource_id")
            service = fields.get("service", "unknown_service")
            
            # Map system
            if res_id:
                prefix = res_id.rsplit("_", 1)[0] if "_" in res_id else res_id
                system_id = sys_map.get(prefix, service)
            else:
                system_id = service
            systems_seen.add(system_id)

            if res_id or fields.get("lookup_key"):
                raw_state = "PRESENT" if fields.get("marker_found") == "false" or fields.get("rows") == "1" else fields.get("event")
                facts.append(
                    Fact(
                        file_id=file_id,
                        system_id=system_id,
                        collection="log_stream",
                        resource_id=res_id or f"log_entry_{idx}",
                        category="SUPPORT_MESSAGE" if "support" in system_id else None,
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
