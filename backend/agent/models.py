from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field

ResourceKey = tuple[str, str]

class Request(BaseModel):
    case_id: str
    email: str
    requested_at: datetime
    reported_status: str
    reported_at: datetime
    audit_at: datetime
    request_text: str

class IdentityRow(BaseModel):
    user_id: str
    values: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime

class AuditEvent(BaseModel):
    audit_id: str
    user_id: str
    event_time: datetime
    field_name: str
    old_value: str
    new_value: str

class ActivityEvent(BaseModel):
    activity_id: str
    event_time: datetime
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    reported_result: str
    details: str

class Rule(BaseModel):
    rule_id: str
    category: str
    condition_text: str
    action: str

class EvidenceFile(BaseModel):
    file_id: str
    path: str
    origin: str
    captured_at: datetime

class Identifier(BaseModel):
    kind: str
    raw: str
    norm: str
    strength: str
    source_ref: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    contested: bool = False

class ResolvedUser(BaseModel):
    user_ids: list[str]
    identifiers: list[Identifier]

class Coverage(BaseModel):
    file_id: str
    system_id: str
    collection: str
    captured_at: datetime
    row_count: int

class Fact(BaseModel):
    file_id: str
    system_id: str
    collection: str
    resource_id: str
    category: str | None = None
    raw_state: str | None = None
    fields: dict[str, str | None] = Field(default_factory=dict)
    locator: str = ""
    confidence: float = 1.0
    quote: str | None = None

class Observation(BaseModel):
    fact: Fact
    matched: list[Identifier] = Field(default_factory=list)
    via: str = "identifier"

class ResourceState(BaseModel):
    key: ResourceKey
    category: str
    kind: str
    state: str
    as_of: datetime | None = None
    evidence_id: str | None = None
    exposed_fields: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)

class Treatment(BaseModel):
    key: ResourceKey
    rule_id: str | None = None
    action: str
    kind: str
    target_state: str

class Finding(BaseModel):
    key: ResourceKey
    operation: str
    state: str
    evidence_id: str

class Step(BaseModel):
    step_no: int
    phase: str
    system_id: str
    resource_id: str
    operation: str
    state: str
    evidence_id: str

class Flag(BaseModel):
    code: str
    case_id: str | None = None
    stage: str
    message: str

class CaseResult(BaseModel):
    case_id: str
    status: str
    steps: list[Step] = Field(default_factory=list)
    flags: list[Flag] = Field(default_factory=list)
    stage_reached: str = ""
