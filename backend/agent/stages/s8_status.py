from __future__ import annotations
from pydantic import BaseModel, Field
from backend.agent.models import Finding, ResourceState

class Gate8Result(BaseModel):
    ok: bool
    status: str
    errors: list[str] = Field(default_factory=list)

def decide_status(
    is_deletion: bool,
    findings: list[Finding],
    states: list[ResourceState],
) -> tuple[str, Gate8Result]:
    if not is_deletion:
        status = "NOT_APPLICABLE"
    elif len(findings) > 0:
        status = "INCOMPLETE"
    else:
        status = "COMPLETE"

    gate8 = Gate8Result(ok=True, status=status)
    return status, gate8
