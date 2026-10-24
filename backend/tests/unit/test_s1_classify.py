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
