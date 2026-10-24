from __future__ import annotations
from pydantic import BaseModel, Field
from backend.agent.models import ResourceState, Treatment
from backend.config.loader import OperationsConfig

class Gate6Result(BaseModel):
    ok: bool
    treatments_count: int = 0
    errors: list[str] = Field(default_factory=list)

def derive_treatments(
    states: list[ResourceState],
    rules: dict[str, str],  # category -> action
    ops_cfg: OperationsConfig,
) -> tuple[list[Treatment], Gate6Result]:
    treatments: list[Treatment] = []
    errors: list[str] = []

    for state in states:
        kind = state.kind
        action: str | None = None

        if kind == "flow":
            action = "*"
        elif kind == "restore_path":
            action = "*"
        else:
            action = rules.get(state.category)
            if not action:
                if state.category == "DATA_FLOW":
                    kind = "flow"
                    action = "*"
                elif state.category == "BACKUP_ARCHIVE":
                    kind = "restore_path"
                    action = "*"
                else:
                    action = "DELETE"

        # Lookup in treatments config
        matched_t = None
        for t in ops_cfg.treatments:
            if t.kind == kind and (t.action == action or t.action == "*"):
                matched_t = t
                break

        if not matched_t:
            errors.append(f"No treatment definition for kind={kind}, action={action}")
            continue

        treatments.append(
            Treatment(
                key=state.key,
                rule_id=None,
                action=action,
                kind=kind,
                target_state=matched_t.target,
            )
        )

    gate6 = Gate6Result(ok=(len(errors) == 0), treatments_count=len(treatments), errors=errors)
    return treatments, gate6
