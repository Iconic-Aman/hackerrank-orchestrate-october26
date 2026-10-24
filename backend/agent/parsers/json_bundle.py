from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from backend.agent.models import Fact, Coverage

def parse_json_bundle(
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
        data = json.load(f)

    # 1. Standard snapshots bundle (e.g. evidence_51)
    if isinstance(data, dict) and "snapshots" in data:
        for s_idx, snap in enumerate(data.get("snapshots", [])):
            system_id = snap.get("data_store", "unknown_system")
            collection = snap.get("collection", "default_collection")
            cap_time = _parse_time(snap.get("captured_at"), default_time)
            records = snap.get("records", [])

            coverage.append(
                Coverage(file_id=file_id, system_id=system_id, collection=collection, captured_at=cap_time, row_count=len(records))
            )
            for r_idx, rec in enumerate(records):
                facts.append(_build_fact(rec, file_id, system_id, collection, f"snapshots[{s_idx}].records[{r_idx}]", sys_map))

    # 2. Service exports bundle (e.g. evidence_92)
    elif isinstance(data, dict) and "service_exports" in data:
        cap_time = _parse_time(data.get("exported_at") or data.get("captured_at"), default_time)
        exports = data.get("service_exports", {})
        for system_id, collections in exports.items():
            if isinstance(collections, dict):
                for coll_name, records in collections.items():
                    if isinstance(records, list):
                        coverage.append(
                            Coverage(file_id=file_id, system_id=system_id, collection=coll_name, captured_at=cap_time, row_count=len(records))
                        )
                        for r_idx, rec in enumerate(records):
                            facts.append(_build_fact(rec, file_id, system_id, coll_name, f"{system_id}.{coll_name}[{r_idx}]", sys_map))

    # 3. Top-level records format (e.g. evidence_56, evidence_59)
    elif isinstance(data, dict) and "records" in data:
        cap_time = _parse_time(data.get("captured_at"), default_time)
        coll_name = data.get("collection", "records")
        source = data.get("source", "system")
        
        records = data.get("records", [])
        # Infer system_id from collection or records
        first_res = records[0].get("resource_id", "") if records else ""
        prefix = first_res.rsplit("_", 1)[0] if "_" in first_res else first_res
        system_id = sys_map.get(prefix, source)

        coverage.append(
            Coverage(file_id=file_id, system_id=system_id, collection=coll_name, captured_at=cap_time, row_count=len(records))
        )
        for r_idx, rec in enumerate(records):
            facts.append(_build_fact(rec, file_id, system_id, coll_name, f"records[{r_idx}]", sys_map))

    return facts, coverage

def _parse_time(t_str: str | None, default_time: datetime | None) -> datetime:
    if t_str:
        try:
            return datetime.fromisoformat(t_str.replace("Z", "+00:00"))
        except Exception:
            pass
    return default_time or datetime.now()

def _build_fact(rec: dict, file_id: str, system_id: str, collection: str, locator: str, sys_map: dict[str, str]) -> Fact:
    res_id = str(rec.get("resource_id") or rec.get("id") or f"{collection}_{locator}")
    prefix = res_id.rsplit("_", 1)[0] if "_" in res_id else res_id
    effective_sys = sys_map.get(prefix, system_id)
    fields = {str(k): (str(v) if v is not None else None) for k, v in rec.items()}
    raw_state = rec.get("account_status") or rec.get("status")

    return Fact(
        file_id=file_id,
        system_id=effective_sys,
        collection=collection,
        resource_id=res_id,
        category=rec.get("category"),
        raw_state=raw_state,
        fields=fields,
        locator=locator,
        confidence=1.0,
    )
