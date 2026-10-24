from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from backend.agent.models import Coverage, Fact, Observation, ResourceKey, ResourceState

class Gate5Result(BaseModel):
    ok: bool
    states_count: int = 0
    unverified_count: int = 0
    errors: list[str] = Field(default_factory=list)

def _derive_state_from_facts(
    facts: list[Fact],
    category: str,
    state_vocab: dict[str, str],
) -> tuple[str, list[str]]:
    # Tombstone check: if tombstone category, inspect direct PII fields
    if category == "ACCOUNT_TOMBSTONE" or any("tombstone" in f.resource_id for f in facts):
        for f in facts:
            pii_exposed = []
            for k in ["name", "email", "phone", "email_hash"]:
                if f.fields.get(k):
                    pii_exposed.append(k)
            if pii_exposed:
                return "PRESENT", pii_exposed
        return "REDACTED", []

    # Check raw_state tokens
    worst_state = "ABSENT"
    state_severity = {
        "ABSENT": 0, "REDACTED": 1, "ANONYMIZED": 1, "DISABLED": 1, "BLOCKED": 1,
        "IDENTIFIABLE": 2, "ACTIVE": 3, "PRESENT": 3
    }
    
    for f in facts:
        token = (f.raw_state or "").upper()
        mapped = state_vocab.get(token)
        
        if not mapped:
            if token == "IDENTIFIABLE":
                mapped = "IDENTIFIABLE"
            elif token in ("NOT_FOUND", "ABSENT"):
                mapped = "ABSENT"
            elif token in ("FOUND", "PRESENT"):
                mapped = "PRESENT"
            elif token in ("ACTIVE", "DISABLED", "BLOCKED", "REDACTED", "ANONYMIZED"):
                mapped = token
            else:
                mapped = "PRESENT" if token else "PRESENT"
            
        if state_severity.get(mapped, 2) >= state_severity.get(worst_state, 0):
            worst_state = mapped

    return worst_state, []

def resolve_resource_states(
    resource_set: set[ResourceKey],
    observations: list[Observation],
    coverage: list[Coverage],
    audit_at: datetime,
    category_kinds: dict[str, str] | None = None,
    state_vocab: dict[str, str] | None = None,
) -> tuple[list[ResourceState], Gate5Result]:
    cat_kinds = category_kinds or {}
    vocab = state_vocab or {}
    resource_states: list[ResourceState] = []
    unverified = 0

    obs_by_res_file: dict[tuple[ResourceKey, str], list[Fact]] = {}
    cat_by_res: dict[ResourceKey, str] = {}
    for obs in observations:
        k = (obs.fact.system_id, obs.fact.resource_id)
        obs_by_res_file.setdefault((k, obs.fact.file_id), []).append(obs.fact)
        if obs.fact.category and k not in cat_by_res:
            cat_by_res[k] = obs.fact.category

    for sys_id, res_id in sorted(resource_set):
        k = (sys_id, res_id)
        prefix = res_id.rsplit("_", 1)[0] if "_" in res_id else res_id
        
        category = cat_by_res.get(k)
        if not category:
            if "account" in prefix:
                category = "USER_PROFILE"
            elif "search" in prefix:
                category = "SEARCH_INDEX_ENTRY"
            elif "analytics" in prefix:
                category = "ANALYTICS_PROFILE"
            elif "support" in prefix:
                category = "SUPPORT_MESSAGE"
            elif "data_flow" in prefix:
                category = "DATA_FLOW"
            elif "backup" in prefix:
                category = "BACKUP_ARCHIVE"
            elif "audit_record" in prefix:
                category = "SECURITY_AUDIT_LOG"
            elif "tombstone" in prefix:
                category = "ACCOUNT_TOMBSTONE"
            else:
                category = "USER_PROFILE"

        kind = cat_kinds.get(category, "record")
        valid_snaps = [c for c in coverage if c.system_id == sys_id and c.captured_at <= audit_at]

        if not valid_snaps:
            obs_files = [obs.fact.file_id for obs in observations if (obs.fact.system_id, obs.fact.resource_id) == k]
            if obs_files:
                winning_file = obs_files[-1]
                facts = obs_by_res_file.get((k, winning_file), [])
                st, exposed = _derive_state_from_facts(facts, category, vocab)
                resource_states.append(
                    ResourceState(key=k, category=category, kind=kind, state=st, evidence_id=winning_file, exposed_fields=exposed)
                )
            else:
                unverified += 1
                resource_states.append(
                    ResourceState(key=k, category=category, kind=kind, state="UNVERIFIED", evidence_id=None)
                )
            continue

        winning_snap = sorted(valid_snaps, key=lambda c: (c.captured_at, c.file_id), reverse=True)[0]
        winning_file = winning_snap.file_id

        facts = obs_by_res_file.get((k, winning_file), [])
        if not facts:
            st = "ABSENT"
            exposed = []
        else:
            st, exposed = _derive_state_from_facts(facts, category, vocab)

        resource_states.append(
            ResourceState(
                key=k,
                category=category,
                kind=kind,
                state=st,
                as_of=winning_snap.captured_at,
                evidence_id=winning_file,
                exposed_fields=exposed,
            )
        )

    gate5 = Gate5Result(ok=True, states_count=len(resource_states), unverified_count=unverified)
    return resource_states, gate5
