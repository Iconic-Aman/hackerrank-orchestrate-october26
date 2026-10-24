from __future__ import annotations
from pydantic import BaseModel, Field
from backend.agent.models import Finding, ResourceState, Step, Treatment
from backend.config.loader import OperationsConfig

class Gate9Result(BaseModel):
    ok: bool
    steps_count: int = 0
    errors: list[str] = Field(default_factory=list)

def build_plan(
    status: str,
    findings: list[Finding],
    states: list[ResourceState],
    treatments: list[Treatment],
    ops_cfg: OperationsConfig,
) -> tuple[list[Step], Gate9Result]:
    if status == "NOT_APPLICABLE":
        return [], Gate9Result(ok=True, steps_count=0)

    raw_steps: list[dict] = []
    treatment_by_key = {t.key: t for t in treatments}
    state_by_key = {s.key: s for s in states}

    # Map treatment kind/action to fix and verify operations
    fix_op_map: dict[tuple[str, str], tuple[str, str]] = {}
    verify_op_map: dict[tuple[str, str], tuple[str, str]] = {}
    for t_def in ops_cfg.treatments:
        if t_def.fix:
            fix_op_map[(t_def.kind, t_def.action)] = (t_def.fix, t_def.target)
        if t_def.verify:
            verify_op_map[(t_def.kind, t_def.action)] = (t_def.verify, t_def.target)

    if status == "INCOMPLETE":
        # Phase 1: FINDINGS
        for f in findings:
            raw_steps.append({
                "phase": "FINDING",
                "system_id": f.key[0],
                "resource_id": f.key[1],
                "operation": f.operation,
                "state": f.state,
                "evidence_id": f.evidence_id,
            })

        # Phase 2: REMEDIATION (one fix per finding)
        finding_keys = {f.key for f in findings}
        for f_key in sorted(finding_keys):
            treatment = treatment_by_key.get(f_key)
            if not treatment:
                continue
            pair = fix_op_map.get((treatment.kind, treatment.action)) or fix_op_map.get((treatment.kind, "*"))
            if pair:
                fix_op, target_st = pair
                raw_steps.append({
                    "phase": "REMEDIATION",
                    "system_id": f_key[0],
                    "resource_id": f_key[1],
                    "operation": fix_op,
                    "state": target_st,
                    "evidence_id": ops_cfg.evidence_id_empty,
                })

        # Phase 3: VERIFICATION (covers all resources in user's set)
        for t in treatments:
            pair = verify_op_map.get((t.kind, t.action)) or verify_op_map.get((t.kind, "*"))
            if pair:
                verify_op, target_st = pair
                raw_steps.append({
                    "phase": "VERIFICATION",
                    "system_id": t.key[0],
                    "resource_id": t.key[1],
                    "operation": verify_op,
                    "state": target_st,
                    "evidence_id": ops_cfg.evidence_id_empty,
                })

    elif status == "COMPLETE":
        # VERIFICATION only, citing evidence
        for t in treatments:
            pair = verify_op_map.get((t.kind, t.action)) or verify_op_map.get((t.kind, "*"))
            if pair:
                verify_op, target_st = pair
                curr_state = state_by_key.get(t.key)
                ev_id = curr_state.evidence_id if curr_state and curr_state.evidence_id else ""
                raw_steps.append({
                    "phase": "VERIFICATION",
                    "system_id": t.key[0],
                    "resource_id": t.key[1],
                    "operation": verify_op,
                    "state": target_st,
                    "evidence_id": ev_id,
                })

    # Sort steps by (phase_order, operation_order, system_id, resource_id)
    phase_order = {p: i for i, p in enumerate(ops_cfg.phases)}
    
    def sort_key(s: dict):
        p_idx = phase_order.get(s["phase"], 99)
        op_info = ops_cfg.operations.get(s["operation"])
        op_idx = op_info.order if op_info else 99
        return (p_idx, op_idx, s["system_id"], s["resource_id"])

    # Deduplicate steps on (phase, operation, system_id, resource_id)
    seen = set()
    deduped = []
    for s in raw_steps:
        k = (s["phase"], s["operation"], s["system_id"], s["resource_id"])
        if k not in seen:
            seen.add(k)
            deduped.append(s)

    deduped.sort(key=sort_key)

    steps = [
        Step(
            step_no=i,
            phase=s["phase"],
            system_id=s["system_id"],
            resource_id=s["resource_id"],
            operation=s["operation"],
            state=s["state"],
            evidence_id=s["evidence_id"],
        )
        for i, s in enumerate(deduped, start=1)
    ]

    gate9 = Gate9Result(ok=True, steps_count=len(steps))
    return steps, gate9
