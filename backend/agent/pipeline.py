from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path
from backend.agent.models import CaseResult, Coverage, Fact, Request
from backend.agent.parsers.dispatcher import parse_evidence_file
from backend.agent.stages.s0_profile import profile_dataset
from backend.agent.stages.s1_classify import classify_request
from backend.agent.stages.s2_identity import IdentityStore, resolve_identity
from backend.agent.stages.s4_match import match_observations
from backend.agent.stages.s5_state import resolve_resource_states
from backend.agent.stages.s6_policy import derive_treatments
from backend.agent.stages.s7_compare import compare_states_and_treatments
from backend.agent.stages.s8_status import decide_status
from backend.agent.stages.s9_plan import build_plan
from backend.agent.stages.s10_output import write_output_csv
from backend.config.loader import OperationsConfig, load_operations_config

class AuditEngine:
    def __init__(self, dataset_dir: Path | str, config_dir: Path | str | None = None) -> None:
        self.dataset_path = Path(dataset_dir)
        self.cfg: OperationsConfig = load_operations_config()
        self.schema_map, self.gate0 = profile_dataset(self.dataset_path)
        self.identity_store = IdentityStore(self.dataset_path)
        
        # Load rules
        self.rules: dict[str, str] = {}
        with open(self.dataset_path / "deletion_rules.csv", "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                self.rules[r["data_category"]] = r["required_action"]

        # Parse evidence index once
        self.facts: list[Fact] = []
        self.coverage: list[Coverage] = []
        self.file_capture_times: dict[str, datetime] = {}
        self._load_evidence_index()

        # Load system activities
        self.system_activities: list[dict] = []
        act_path = self.dataset_path / "system_activity.csv"
        if act_path.exists():
            with open(act_path, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    try:
                        etime = datetime.fromisoformat(r["event_time"].replace("Z", "+00:00"))
                    except Exception:
                        etime = datetime.min
                    self.system_activities.append({
                        "activity_id": r["activity_id"],
                        "event_time": etime,
                        "event_type": r["event_type"],
                        "source_system": r["source_system"],
                        "target_system": r["target_system"],
                        "resource_id": r["resource_id"],
                        "reported_result": r["reported_result"],
                        "details": r["details"],
                    })

    def _load_evidence_index(self) -> None:
        with open(self.dataset_path / "evidence_files.csv", "r", encoding="utf-8") as f:
            manifest_rows = list(csv.DictReader(f))

        for row in manifest_rows:
            fid = row["file_id"]
            rel_path = row["file_path"]
            full_path = self.dataset_path / rel_path
            if not full_path.exists():
                continue

            cap_time = datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00"))
            self.file_capture_times[fid] = cap_time
            file_facts, file_cov = parse_evidence_file(
                full_path, fid, captured_at=cap_time, resource_system_map=self.schema_map.resource_system_map
            )
            self.facts.extend(file_facts)
            self.coverage.extend(file_cov)

    def audit_case(self, req: Request) -> CaseResult:
        # S1: Classify
        is_del, _, _ = classify_request(req.request_text, req.reported_status)
        if not is_del:
            return CaseResult(case_id=req.case_id, status="NOT_APPLICABLE", steps=[], stage_reached="S1")

        # S2: Resolve Identity
        user, gate2 = resolve_identity(req.email, req.audit_at, self.identity_store)
        if not gate2.ok:
            return CaseResult(case_id=req.case_id, status="COMPLETE", steps=[], stage_reached="S2")

        # S4: Match Observations
        obs, res_set, _ = match_observations(user, self.facts, req.audit_at, self.file_capture_times)

        # Correlate system activities near reported_at to identify target resources
        rep_time = req.reported_at
        for act in self.system_activities:
            if abs((act["event_time"] - rep_time).total_seconds()) <= 600:
                if any(k in act["event_type"] for k in ("DELETE", "ANONYMIZE", "INDEX", "SYNC", "UPDATE")):
                    sys_id = act["target_system"] or act["source_system"]
                    res_id = act["resource_id"]
                    if sys_id and res_id:
                        res_set.add((sys_id, res_id))


        # S5: Resolve States
        states, _ = resolve_resource_states(
            res_set, obs, self.coverage, req.audit_at,
            category_kinds=self.schema_map.category_kinds,
            state_vocab=self.schema_map.state_vocab,
        )

        # S6: Derive Treatments
        treatments, _ = derive_treatments(states, self.rules, self.cfg)

        # S7: Compare States vs Policy
        findings, _ = compare_states_and_treatments(states, treatments, self.cfg)

        # S8: Status
        status, _ = decide_status(is_del, findings, states)

        # S9: Plan
        steps, _ = build_plan(status, findings, states, treatments, self.cfg)

        return CaseResult(case_id=req.case_id, status=status, steps=steps, stage_reached="S9")

    def run_all(self, requests_csv: Path | str, output_csv: Path | str) -> list[CaseResult]:
        requests: list[Request] = []
        with open(requests_csv, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                requests.append(
                    Request(
                        case_id=r["case_id"],
                        email=r["email"],
                        requested_at=datetime.fromisoformat(r["requested_at"].replace("Z", "+00:00")),
                        reported_status=r["reported_status"],
                        reported_at=datetime.fromisoformat(r["reported_at"].replace("Z", "+00:00")),
                        audit_at=datetime.fromisoformat(r["audit_at"].replace("Z", "+00:00")),
                        request_text=r["request_text"],
                    )
                )

        results = [self.audit_case(req) for req in requests]
        write_output_csv(results, output_csv, expected_count=len(requests))
        return results
