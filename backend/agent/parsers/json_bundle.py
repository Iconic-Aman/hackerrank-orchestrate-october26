from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from backend.agent.models import Fact, Coverage

def parse_json_bundle(file_path: Path | str, file_id: str, default_time: datetime | None = None) -> tuple[list[Fact], list[Coverage]]:
    path = Path(file_path)
    facts: list[Fact] = []
    coverage: list[Coverage] = []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    snapshots = data.get("snapshots", [])
    for s_idx, snap in enumerate(snapshots):
        system_id = snap.get("data_store", "unknown_system")
        collection = snap.get("collection", "default_collection")
        cap_str = snap.get("captured_at")
        if cap_str:
            try:
                cap_time = datetime.fromisoformat(cap_str.replace("Z", "+00:00"))
            except Exception:
                cap_time = default_time or datetime.now()
        else:
            cap_time = default_time or datetime.now()

        records = snap.get("records", [])
        coverage.append(
            Coverage(
                file_id=file_id,
                system_id=system_id,
                collection=collection,
                captured_at=cap_time,
                row_count=len(records),
            )
        )

        for r_idx, rec in enumerate(records):
            resource_id = rec.get("resource_id") or rec.get("id") or f"{collection}_{r_idx}"
            fields = {str(k): (str(v) if v is not None else None) for k, v in rec.items()}
            
            raw_state = rec.get("account_status") or rec.get("status")
            facts.append(
                Fact(
                    file_id=file_id,
                    system_id=system_id,
                    collection=collection,
                    resource_id=str(resource_id),
                    category=rec.get("category"),
                    raw_state=raw_state,
                    fields=fields,
                    locator=f"snapshots[{s_idx}].records[{r_idx}]",
                    confidence=1.0,
                )
            )

    return facts, coverage
