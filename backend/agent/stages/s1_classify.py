from __future__ import annotations
import re
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------
class Gate1Result(BaseModel):
    ok: bool
    is_deletion: bool
    confidence: float = 1.0
    reason: str = ""
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Regex tiers
# ---------------------------------------------------------------------------
# Clear non-deletion patterns → immediately return False
NON_DELETION_PATTERNS = [
    r"leave (the|my) account",
    r"leave my profile",
    r"keep (the|my) account",
    r"\bdo not (close|delete|erase|remove)\b",
    r"\bdon['']?t (close|delete|erase|remove)\b",
    r"please don['']?t",
    r"without removing",
    r"marketing (lists|emails|communications) only",
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
    r"how (do|can|to) (i|you) delete",    # rhetorical how-to question
    r"how (do|can|to) (i|you) close",
    r"how (do|can|to) (i|you) erase",
    r"can you (tell|explain|show) me how",
    r"(access|download|export|copy of) (my )?(personal )?(data|information|account)",
    r"right of access",
    r"data portability",
    r"opt.?out of (marketing|emails|communications)",
]

# Clear deletion patterns → immediately return True (unless negation already fired)
DELETION_PATTERNS = [
    r"\bdelete\b",
    r"\bdeletion\b",
    r"\berase\b",
    r"\berasure\b",
    r"\berased\b",
    r"remove (my|the|all) (account|data|profile|information|records?)",
    r"close (my|the|this) account",
    r"eliminaci[oó]n",
    r"eliminar",
    r"borrar",
    r"\bsuppression\b",
    r"\bsupprimer\b",
    r"exclus[aã]o",
    r"excluir",
    r"l[oö]sch",
    r"right (to be|of) (forgotten|erasure)",
    r"forget me",
    r"wipe (my|all|the) (data|records?|account)",
    r"stop being in your system",
    r"remove me from (your|all) (system|database|records?)",
    r"purge (my|the|all) (data|records?|account)",
]

# ---------------------------------------------------------------------------
# LLM classification prompt
# ---------------------------------------------------------------------------
_SYSTEM = (
    "You are a data-deletion request classifier for a privacy compliance system. "
    "Your sole job is to determine whether the user's message is an authoritative "
    "request to delete/erase their personal data under GDPR / CCPA or equivalent law."
)

_USER_TMPL = """Classify the following request. Answer with exactly one JSON object and nothing else.

Rules:
- "is_deletion": true only when the person clearly and directly asks to have their personal data
  permanently deleted or their account removed.
- "is_deletion": false for: requests to access/export/download data, opt-out of marketing only,
  corrections, rhetorical questions ("how do I delete?"), negations ("please don't delete"),
  questions about deletion policy, or ambiguous/polite complaints that don't explicitly ask for erasure.
- Mixed requests ("send me my data, then delete it") → true if deletion is explicitly requested in addition to another action.
- Respond in the request language — but always output JSON in English keys.

Required JSON format:
{{"is_deletion": <true|false>, "confidence": <0.0-1.0>, "reason": "<one short English sentence>"}}

Request:
\"\"\"
{text}
\"\"\"
"""


def _llm_classify(text: str) -> Gate1Result | None:
    """Call OpenRouter to classify. Returns None if LLM unavailable or response invalid."""
    try:
        from backend.agent.llm.openrouter_client import chat_completion  # late import
    except Exception:
        return None

    import json

    raw = chat_completion(
        prompt=_USER_TMPL.format(text=text[:2000]),
        system=_SYSTEM,
        temperature=0.0,
        max_tokens=128,
    )
    if raw is None:
        return None

    # Extract JSON from response (model may wrap in markdown fences)
    json_match = re.search(r"\{.*?\}", raw, re.S)
    if not json_match:
        return None

    try:
        obj = json.loads(json_match.group(0))
        is_del = bool(obj.get("is_deletion", False))
        confidence = float(obj.get("confidence", 0.8))
        reason = str(obj.get("reason", "LLM classified"))
        return Gate1Result(ok=True, is_deletion=is_del, confidence=confidence, reason=reason)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def classify_request(
    request_text: str,
    reported_status: str | None = None,
) -> tuple[bool, str, Gate1Result]:
    """
    Two-tier classification:
      Tier 1 — fast regex for high-confidence clear cases.
      Tier 2 — LLM via OpenRouter for ambiguous / multilingual / edge cases.
      Fallback — conservative regex result if LLM unavailable.
    """
    text = (request_text or "").strip()
    if not text:
        return (
            False,
            "Empty request text",
            Gate1Result(ok=False, is_deletion=False, confidence=0.0, errors=["Empty request text"]),
        )

    # ── Tier 1a: regex non-deletion (fast exit) ──────────────────────────
    for pattern in NON_DELETION_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            # Still validate with LLM if the match was a negation-type pattern
            # (the regex might fire on "don't delete" inside a real deletion request)
            is_negation_pattern = any(
                kw in pattern for kw in ["don", "do not", "how do", "can you tell", "access", "portab", "opt"]
            )
            if not is_negation_pattern:
                # High-confidence structural negative — skip LLM
                reason = f"Request does not authorize deletion: matched '{m.group(0)}'"
                return False, reason, Gate1Result(ok=True, is_deletion=False, confidence=0.99, reason=reason)
            # For negation-type patterns: let LLM confirm, but set a hint
            llm_result = _llm_classify(text)
            if llm_result is not None:
                return llm_result.is_deletion, llm_result.reason, llm_result
            # LLM unavailable → trust regex
            reason = f"Request does not authorize deletion: matched '{m.group(0)}'"
            return False, reason, Gate1Result(ok=True, is_deletion=False, confidence=0.90, reason=reason)

    # ── Tier 1b: regex deletion (fast exit for unambiguous cases) ────────
    deletion_match: re.Match | None = None
    for pattern in DELETION_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            deletion_match = m
            break

    # Decide if we need LLM:
    # • Has deletion match AND no non-ASCII → high confidence, skip LLM
    # • No match OR non-ASCII present → use LLM
    has_non_ascii = any(ord(c) > 127 for c in text)
    needs_llm = deletion_match is None or has_non_ascii

    if needs_llm:
        llm_result = _llm_classify(text)
        if llm_result is not None:
            return llm_result.is_deletion, llm_result.reason, llm_result
        # LLM unavailable → conservative fallback
        if deletion_match:
            reason = f"Request authorizes deletion: matched '{deletion_match.group(0)}'"
            return True, reason, Gate1Result(ok=True, is_deletion=True, confidence=0.75, reason=reason)
        # Non-ASCII, no match, no LLM → conservative: treat as NOT deletion (avoid false positives)
        reason = "Could not determine deletion intent; LLM unavailable and no pattern matched"
        return False, reason, Gate1Result(ok=True, is_deletion=False, confidence=0.50, reason=reason)

    # ── Fast path: clear deletion match, ASCII-only ───────────────────────
    reason = f"Request authorizes deletion: matched '{deletion_match.group(0)}'"  # type: ignore[union-attr]
    return True, reason, Gate1Result(ok=True, is_deletion=True, confidence=0.99, reason=reason)
