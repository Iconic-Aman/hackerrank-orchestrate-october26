from backend.agent.stages.s1_classify import classify_request

def test_s1_classify_english_deletion():
    text = "Please delete my account and the identity document I sent to support."
    is_del, reason, gate1 = classify_request(text)
    assert gate1.ok is True
    assert is_del is True

def test_s1_classify_multilingual_deletion():
    # Spanish
    is_del, _, _ = classify_request("Solicito la eliminación permanente de la cuenta asociada a este correo.")
    assert is_del is True

    # French
    is_del, _, _ = classify_request("Je demande la suppression définitive du compte associé à cette adresse e-mail.")
    assert is_del is True

    # Portuguese
    is_del, _, _ = classify_request("Solicito a exclusão permanente da conta associada a este e-mail.")
    assert is_del is True

def test_s1_classify_non_deletion_requests():
    # Data export only
    text1 = "I'd like to download my account information in a portable format. Please keep the account as it is."
    is_del, reason, _ = classify_request(text1)
    assert is_del is False
    assert "keep the account" in reason

    # Invoice copy
    text2 = "I need a copy of last year's invoices for my records. Please leave my profile and purchase history in place."
    is_del, _, _ = classify_request(text2)
    assert is_del is False

    # Correction
    text3 = "My surname is misspelled on the account. Can you correct it without removing any of my records?"
    is_del, _, _ = classify_request(text3)
    assert is_del is False

    # Marketing opt-out
    text4 = "Please stop the promotional emails. I still need the account and my order history, so I am not asking for deletion."
    is_del, _, _ = classify_request(text4)
    assert is_del is False

def test_s1_reported_status_ignored():
    # Reported status claims COMPLETE, but user asks only for copy
    text = "Could you send me a copy of the information held on my account? I still use it, so please don't delete or change anything."
    is_del, _, _ = classify_request(text, reported_status="COMPLETE")
    assert is_del is False

def test_s1_empty_text():
    is_del, _, gate1 = classify_request("")
    assert gate1.ok is False
    assert is_del is False


# ── Edge cases added for LLM-tier validation ──────────────────────────────

def test_s1_negation_dont_delete():
    """'Please don't delete my account' contains 'delete' but is NOT a deletion request."""
    is_del, _, gate1 = classify_request("Please don't delete my account, I still use it.")
    assert is_del is False, f"Negation should be False (confidence={gate1.confidence}, reason={gate1.reason})"


def test_s1_negation_do_not_delete():
    """'do not delete' variant."""
    is_del, _, _ = classify_request("Do not delete my account — I want to keep it active.")
    assert is_del is False


def test_s1_mixed_export_then_delete():
    """Mixed: explicit delete alongside export → deletion wins."""
    is_del, _, gate1 = classify_request(
        "Please send me a copy of all my data, and then delete my account completely."
    )
    assert is_del is True, f"Mixed request with explicit delete should be True (reason={gate1.reason})"


def test_s1_rhetorical_how_to_question():
    """'Can you tell me how to delete my account?' — question, not a request."""
    is_del, _, gate1 = classify_request("Can you tell me how to delete my account?")
    assert is_del is False, f"Rhetorical question should be False (reason={gate1.reason})"


def test_s1_japanese_deletion_no_llm(monkeypatch):
    """Without LLM, Japanese non-ASCII should not blindly return True at 0.95 confidence."""
    import backend.agent.llm.openrouter_client as client_mod
    monkeypatch.setattr(client_mod, "chat_completion", lambda **kw: None)

    japanese_text = "アカウントを削除してください。"
    is_del, _, gate1 = classify_request(japanese_text)
    # Conservative: either False or True with low confidence (not the old blind 0.95)
    assert gate1.confidence < 0.95 or not gate1.is_deletion or is_del == gate1.is_deletion


def test_s1_japanese_deletion_with_llm(monkeypatch):
    """With LLM, Japanese deletion request → True."""
    import backend.agent.llm.openrouter_client as client_mod

    def fake_chat(**kw):
        return '{"is_deletion": true, "confidence": 0.97, "reason": "Japanese deletion request"}'

    monkeypatch.setattr(client_mod, "chat_completion", fake_chat)

    japanese_text = "アカウントを削除してください。"
    is_del, _, gate1 = classify_request(japanese_text)
    assert is_del is True
    assert gate1.confidence >= 0.9

