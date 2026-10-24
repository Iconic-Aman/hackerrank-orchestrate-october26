from __future__ import annotations
import re
from datetime import datetime
from pydantic import BaseModel, Field
from backend.agent.models import Fact, Identifier, Observation, ResolvedUser

class Gate4Result(BaseModel):
    ok: bool
    observations_count: int = 0
    resources_count: int = 0
    errors: list[str] = Field(default_factory=list)

def _norm_email(v: str) -> str:
    return v.strip().lower() if v else ""

def _norm_phone(v: str) -> str:
    return re.sub(r"\D", "", v) if v else ""

def match_observations(
    user: ResolvedUser,
    facts: list[Fact],
    audit_at: datetime,
    file_capture_times: dict[str, datetime] | None = None,
) -> tuple[list[Observation], set[tuple[str, str]], Gate4Result]:
    cap_times = file_capture_times or {}
    observations: list[Observation] = []
    
    user_id_idents = {i.norm: i for i in user.identifiers if i.kind == "user_id"}
    email_idents = {i.norm: i for i in user.identifiers if i.kind == "email"}
    phone_idents = {i.norm: i for i in user.identifiers if i.kind == "phone"}
    hash_idents = {i.norm: i for i in user.identifiers if i.kind == "email_hash"}
    name_idents = {i.norm: i for i in user.identifiers if i.kind == "name"}

    for fact in facts:
        # 1. Temporal filter: ignore facts captured after audit_at
        file_time = cap_times.get(fact.file_id)
        if file_time and file_time > audit_at:
            continue

        matched: list[Identifier] = []
        via = "identifier"

        # Check user_id in common columns
        for uid_col in ["user_id", "subject_reference"]:
            val = fact.fields.get(uid_col)
            if val and val in user_id_idents:
                matched.append(user_id_idents[val])
                via = "user_id"

        # Check all text values in fields
        for field_name, field_val in fact.fields.items():
            if not field_val or field_name in ["user_id", "subject_reference"]:
                continue
            
            str_val = str(field_val)
            val_lower = str_val.lower()

            # Email match
            for em_norm, ident in email_idents.items():
                if em_norm in val_lower and ident not in matched:
                    matched.append(ident)

            # Email hash match
            for h_norm, ident in hash_idents.items():
                if h_norm in val_lower and ident not in matched:
                    matched.append(ident)

            # Phone match
            digits = re.sub(r"\D", "", str_val)
            for ph_norm, ident in phone_idents.items():
                if len(ph_norm) >= 7 and ph_norm in digits and ident not in matched:
                    matched.append(ident)

            # Name match (weak)
            for nm_norm, ident in name_idents.items():
                if len(nm_norm) >= 4 and nm_norm in val_lower and ident not in matched:
                    matched.append(ident)

        if not matched:
            continue

        # Strength rule: name alone is weak and cannot be the sole basis of observation
        strong_matches = [m for m in matched if m.strength == "strong"]
        if not strong_matches:
            continue

        observations.append(Observation(fact=fact, matched=matched, via=via))

    resource_set = {(obs.fact.system_id, obs.fact.resource_id) for obs in observations}
    
    gate4 = Gate4Result(
        ok=True,
        observations_count=len(observations),
        resources_count=len(resource_set),
    )
    return observations, resource_set, gate4
