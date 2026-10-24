from datetime import datetime
from pathlib import Path
from backend.agent.stages.s2_identity import IdentityStore, resolve_identity

def test_s2_resolve_current_email_case_01():
    store = IdentityStore(Path("dataset"))
    audit_at = datetime.fromisoformat("2026-09-03T11:30:00+00:00")
    user, gate2 = resolve_identity("amina.elmasri@gmail.com", audit_at, store)
    
    assert gate2.ok is True
    assert "user_01" in user.user_ids
    kinds = {i.kind for i in user.identifiers}
    assert {"user_id", "email", "phone", "email_hash", "name"}.issubset(kinds)

def test_s2_resolve_historical_email_chain_case_10():
    store = IdentityStore(Path("dataset"))
    audit_at = datetime.fromisoformat("2026-09-18T12:25:00+00:00")
    user, gate2 = resolve_identity("nadia.ionescu@yahoo.com", audit_at, store)
    
    assert gate2.ok is True
    assert "user_10" in user.user_ids
    emails = {i.norm for i in user.identifiers if i.kind == "email"}
    assert "nadia.ionescu@yahoo.com" in emails
    assert "nadia.petrescu@yahoo.com" in emails
    assert "n.petrescu@yahoo.com" in emails

def test_s2_unknown_email():
    store = IdentityStore(Path("dataset"))
    audit_at = datetime.now()
    user, gate2 = resolve_identity("unknown.nobody.123456@ghost.example.com", audit_at, store)
    assert gate2.ok is False
    assert len(user.user_ids) == 0

def test_s2_exclude_audit_events_after_audit_at():
    store = IdentityStore(Path("dataset"))
    # In user_audit_log, user_425 changed from abena.a30485@outlook.com to abena.a304@outlook.com on 2025-11-20
    # If audit_at is earlier than 2025-11-20 (e.g. 2025-01-01), the historical event is excluded
    early_audit_at = datetime.fromisoformat("2025-01-01T00:00:00+00:00")
    # Resolve using user_425's current email
    curr_email = store.identities["user_425"]["email"]
    user, gate2 = resolve_identity(curr_email, early_audit_at, store)
    
    assert gate2.ok is True
    emails = {i.norm for i in user.identifiers if i.kind == "email"}
    assert "abena.a30485@outlook.com" not in emails
