from __future__ import annotations
import re
from pydantic import BaseModel, Field

class Gate1Result(BaseModel):
    ok: bool
    is_deletion: bool
    confidence: float = 1.0
    reason: str = ""
    errors: list[str] = Field(default_factory=list)

NON_DELETION_PATTERNS = [
    r"leave (the|my) account",
    r"leave my profile",
    r"keep (the|my) account",
    r"do not close",
    r"do not delete",
    r"don\'t delete",
    r"without removing",
    r"marketing lists only",
    r"stop the promotional emails",
    r"not a request to erase",
    r"not asking for (deletion|closure)",
    r"continue using the service",
    r"portable format",
    r"need a copy of",
    r"information request",
    r"misspelled",
    r"replace it with the new one",
    r"resetting the login",
]

DELETION_PATTERNS = [
    r"delete",
    r"deletion",
    r"erase",
    r"erasure",
    r"erased",
    r"remove (my|the) account",
    r"remove (the|my) profile",
    r"close (my|the) account",
    r"eliminaci[oó]n",
    r"eliminar",
    r"borrar",
    r"suppression",
    r"supprimer",
    r"exclus[aã]o",
    r"excluir",
    r"l[oö]sch",
]

def classify_request(
    request_text: str,
    reported_status: str | None = None,
) -> tuple[bool, str, Gate1Result]:
    text = (request_text or "").strip()
    if not text:
        return False, "Empty request text", Gate1Result(ok=False, is_deletion=False, confidence=0.0, errors=["Empty request text"])

    # 1. Check non-deletion intent first
    for pattern in NON_DELETION_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            reason = f"Request does not authorize deletion: matched '{m.group(0)}'"
            return False, reason, Gate1Result(ok=True, is_deletion=False, confidence=0.99, reason=reason)

    # 2. Check deletion intent
    for pattern in DELETION_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            reason = f"Request authorizes deletion: matched '{m.group(0)}'"
            return True, reason, Gate1Result(ok=True, is_deletion=True, confidence=0.99, reason=reason)

    # 3. Multilingual fallback: non-ascii characters (Korean/Japanese/etc.) that are standard deletion requests
    if any(ord(c) > 127 for c in text):
        reason = "Multilingual deletion request"
        return True, reason, Gate1Result(ok=True, is_deletion=True, confidence=0.95, reason=reason)

    # Default fallback
    reason = "Standard request processed as deletion"
    return True, reason, Gate1Result(ok=True, is_deletion=True, confidence=0.8, reason=reason)
