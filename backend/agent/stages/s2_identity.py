from __future__ import annotations
import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from backend.agent.models import Identifier, ResolvedUser

class Gate2Result(BaseModel):
    ok: bool
    user_ids: list[str] = Field(default_factory=list)
    identifier_count: int = 0
    errors: list[str] = Field(default_factory=list)

def norm_email(val: str) -> str:
    return val.strip().lower() if val else ""

def norm_phone(val: str) -> str:
    return re.sub(r"\D", "", val) if val else ""

def norm_name(val: str) -> str:
    return " ".join(val.lower().split()) if val else ""

def hash_email(email: str) -> str:
    return hashlib.sha256(norm_email(email).encode("utf-8")).hexdigest()

class IdentityStore:
    def __init__(self, dataset_dir: Path | str) -> None:
        self.dataset_path = Path(dataset_dir)
        self.identities: dict[str, dict[str, str]] = {}
        self.user_by_current_email: dict[str, str] = {}
        self.user_by_historical_ident: dict[str, set[str]] = {}
        self.audit_events_by_user: dict[str, list[dict[str, str]]] = {}
        self._load()

    def _load(self) -> None:
        with open(self.dataset_path / "user_identities.csv", "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                uid = r["user_id"]
                self.identities[uid] = r
                if r.get("email"):
                    self.user_by_current_email[norm_email(r["email"])] = uid

        with open(self.dataset_path / "user_audit_log.csv", "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                uid = r["user_id"]
                self.audit_events_by_user.setdefault(uid, []).append(r)
                for val in (r.get("old_value"), r.get("new_value")):
                    if val and r["field_name"] == "email":
                        self.user_by_historical_ident.setdefault(norm_email(val), set()).add(uid)

def resolve_identity(
    request_email: str,
    audit_at: datetime,
    store: IdentityStore,
) -> tuple[ResolvedUser, Gate2Result]:
    clean_req_email = norm_email(request_email)
    matched_uids: set[str] = set()

    # Current email match
    if clean_req_email in store.user_by_current_email:
        matched_uids.add(store.user_by_current_email[clean_req_email])
    # Historical email match
    if clean_req_email in store.user_by_historical_ident:
        matched_uids.update(store.user_by_historical_ident[clean_req_email])

    errors: list[str] = []
    if not matched_uids:
        errors.append(f"No user found for email: {request_email}")
        return ResolvedUser(user_ids=[], identifiers=[]), Gate2Result(ok=False, errors=errors)

    identifiers: list[Identifier] = []
    seen_keys: set[tuple[str, str]] = set()

    for uid in sorted(matched_uids):
        # 1. user_id identifier
        identifiers.append(
            Identifier(kind="user_id", raw=uid, norm=uid, strength="strong", source_ref=f"identity:{uid}")
        )
        seen_keys.add(("user_id", uid))

        curr = store.identities.get(uid, {})
        # Current email
        if curr.get("email"):
            em = curr["email"]
            identifiers.append(Identifier(kind="email", raw=em, norm=norm_email(em), strength="strong", source_ref=f"identity:{uid}"))
            h = curr.get("email_hash") or hash_email(em)
            identifiers.append(Identifier(kind="email_hash", raw=h, norm=h, strength="strong", source_ref=f"identity:{uid}"))
            seen_keys.add(("email", norm_email(em)))
            seen_keys.add(("email_hash", h))
        # Current phone
        if curr.get("phone"):
            ph = curr["phone"]
            identifiers.append(Identifier(kind="phone", raw=ph, norm=norm_phone(ph), strength="strong", source_ref=f"identity:{uid}"))
            seen_keys.add(("phone", norm_phone(ph)))
        # Current name
        if curr.get("name"):
            nm = curr["name"]
            identifiers.append(Identifier(kind="name", raw=nm, norm=norm_name(nm), strength="weak", source_ref=f"identity:{uid}"))
            seen_keys.add(("name", norm_name(nm)))

        # 2. Historical changes from audit log
        for event in store.audit_events_by_user.get(uid, []):
            try:
                ev_time = datetime.fromisoformat(event["event_time"].replace("Z", "+00:00"))
                if ev_time > audit_at:
                    continue
            except Exception:
                pass

            field = event["field_name"]
            aid = event["audit_id"]
            for val in [event.get("old_value"), event.get("new_value")]:
                if not val:
                    continue
                if field == "email":
                    norm_v = norm_email(val)
                    if ("email", norm_v) not in seen_keys:
                        identifiers.append(Identifier(kind="email", raw=val, norm=norm_v, strength="strong", source_ref=aid))
                        h = hash_email(val)
                        identifiers.append(Identifier(kind="email_hash", raw=h, norm=h, strength="strong", source_ref=aid))
                        seen_keys.add(("email", norm_v))
                        seen_keys.add(("email_hash", h))
                elif field == "phone":
                    norm_v = norm_phone(val)
                    if ("phone", norm_v) not in seen_keys:
                        identifiers.append(Identifier(kind="phone", raw=val, norm=norm_v, strength="strong", source_ref=aid))
                        seen_keys.add(("phone", norm_v))
                elif field == "name":
                    norm_v = norm_name(val)
                    if ("name", norm_v) not in seen_keys:
                        identifiers.append(Identifier(kind="name", raw=val, norm=norm_v, strength="weak", source_ref=aid))
                        seen_keys.add(("name", norm_v))

    user_obj = ResolvedUser(user_ids=sorted(matched_uids), identifiers=identifiers)
    gate2 = Gate2Result(ok=True, user_ids=user_obj.user_ids, identifier_count=len(identifiers))
    return user_obj, gate2
