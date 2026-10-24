from __future__ import annotations
from datetime import datetime
from pathlib import Path
from backend.agent.models import Fact, Coverage

def parse_pipe_table(file_path: Path | str, file_id: str, default_time: datetime | None = None) -> tuple[list[Fact], list[Coverage]]:
    path = Path(file_path)
    facts: list[Fact] = []
    systems_seen: set[str] = set()
    snapshot_time = default_time or datetime.fromtimestamp(path.stat().st_mtime)

    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            s = line.strip()
            if s.startswith("Snapshot:"):
                try:
                    snapshot_time = datetime.fromisoformat(s.split("Snapshot:", 1)[1].strip().replace("Z", "+00:00"))
                except Exception:
                    pass
                continue
            if not s.startswith("- ") or "|" not in s:
                continue

            # Strip leading '- '
            content = s[2:].strip()
            parts = [p.strip() for p in content.split("|")]
            if len(parts) < 6:
                continue

            ts_str, system_id, resource_id, category, raw_state, identifier_field = parts[:6]
            systems_seen.add(system_id)
            
            facts.append(
                Fact(
                    file_id=file_id,
                    system_id=system_id,
                    collection="handover_log",
                    resource_id=resource_id,
                    category=category,
                    raw_state=raw_state,
                    fields={"identifier": identifier_field, "timestamp": ts_str},
                    locator=f"line:{idx}",
                    confidence=1.0,
                )
            )

    coverage = [
        Coverage(
            file_id=file_id,
            system_id=sys,
            collection="handover_log",
            captured_at=snapshot_time,
            row_count=sum(1 for f in facts if f.system_id == sys),
        )
        for sys in sorted(systems_seen)
    ]
    return facts, coverage
