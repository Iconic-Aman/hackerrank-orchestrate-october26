from datetime import datetime
from pathlib import Path
from backend.agent.models import Fact, Identifier, ResolvedUser
from backend.agent.parsers.dispatcher import parse_evidence_file
from backend.agent.stages.s2_identity import IdentityStore, resolve_identity
from backend.agent.stages.s4_match import match_observations

def test_s4_match_case_11():
    store = IdentityStore(Path("dataset"))
    audit_at = datetime.fromisoformat("2026-10-01T12:00:00+00:00")
    user, gate2 = resolve_identity("novak.tomasz@icloud.com", audit_at, store)
    assert gate2.ok is True

    # Parse evidence_03 handover log
    facts, _ = parse_evidence_file("dataset/evidence/records/customer_account_handover_20261001.txt", "evidence_03")
    
    cap_times = {"evidence_03": audit_at}
    obs, res_set, gate4 = match_observations(user, facts, audit_at, cap_times)
    
    assert gate4.ok is True
    assert gate4.observations_count >= 5
    res_ids = {r[1] for r in res_set}
    # Check expected resources for case_11
    assert "search_052" in res_ids
    assert "analytics_2034" in res_ids
    assert "support_864" in res_ids
    assert "data_flow_9522" in res_ids
    assert "account_4248" in res_ids

def test_s4_drop_weak_name_only():
    user = ResolvedUser(
        user_ids=["user_999"],
        identifiers=[
            Identifier(kind="name", raw="John Smith", norm="john smith", strength="weak", source_ref="test")
        ],
    )
    fact = Fact(
        file_id="ev_1",
        system_id="test_sys",
        collection="test_coll",
        resource_id="res_1",
        fields={"comment": "Customer John Smith called support"},
    )
    obs, res_set, gate4 = match_observations(user, [fact], datetime.now())
    # Should be dropped because name is weak only
    assert len(obs) == 0
    assert len(res_set) == 0

def test_s4_temporal_cutoff():
    user = ResolvedUser(
        user_ids=["user_100"],
        identifiers=[
            Identifier(kind="email", raw="test@example.com", norm="test@example.com", strength="strong", source_ref="test")
        ],
    )
    fact = Fact(
        file_id="ev_future",
        system_id="sys",
        collection="coll",
        resource_id="res_future",
        fields={"email": "test@example.com"},
    )
    audit_at = datetime.fromisoformat("2026-05-01T00:00:00+00:00")
    cap_times = {"ev_future": datetime.fromisoformat("2026-06-01T00:00:00+00:00")}
    obs, _, _ = match_observations(user, [fact], audit_at, cap_times)
    assert len(obs) == 0
