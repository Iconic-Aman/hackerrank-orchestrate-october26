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
    detected_language: str = "English"
    english_translation: str = ""
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
    r"delet",
    r"eras",
    r"remov",
    r"clos",
    r"purg",
    r"wip",
    r"elimin",
    r"borr",
    r"supprim",
    r"suppress",
    r"exclu",
    r"l[oö]sch",
    r"削除",
    r"消去",
    r"消して",
    r"解約",
    r"right (to be|of) (forgotten|erasure)",
    r"forget me",
    r"wipe (my|all|the) (data|records?|account)",
    r"stop being in your system",
    r"remove me from (your|all) (system|database|records?)",
    r"purge (my|the|all) (data|records?|account)",
    r"account.*gone",
    r"terminate (my|the) account",
    r"cancel (my|the) account",
]

# ---------------------------------------------------------------------------
# LLM classification prompt
# ---------------------------------------------------------------------------
_SYSTEM = (
    "You are an expert multilingual privacy compliance auditor for GDPR, CCPA, and global data protection regulations. "
    "Your task is to analyze user requests submitted in any language, detect the language, translate the request into English, "
    "and determine if the user is authoritatively demanding permanent deletion/erasure of their personal data or account."
)

_USER_TMPL = """Analyze the following user request using a 3-step chain-of-thought:
1. DETECT LANGUAGE: Identify the language of the request (e.g. Japanese, French, Spanish, German, Portuguese, English).
2. TRANSLATE TO ENGLISH: Provide an accurate, faithful English translation (preserving any negations like "don't delete" or mixed requests).
3. PREDICT DELETION INTENT: Based on the English translation, determine if the user is authoritatively requesting data deletion/erasure.

Classification Rules:
- "is_deletion": true ONLY when the person explicitly requests to delete, erase, close, or wipe their account or personal data.
- "is_deletion": false for:
  * Negations: "please do not delete my account", "keep my data"
  * Data access or export: "send me my data", "download my past invoices"
  * Marketing opt-outs: "stop promotional emails"
  * Profile corrections: "correct my misspelled name"
  * Rhetorical / how-to questions: "how do I delete my account?", "explain your deletion policy"
- Mixed requests: "send me my data, then delete my account" -> true (since deletion is explicitly requested).

Output strictly valid JSON with this exact structure:
{{
  "detected_language": "<Language name>",
  "english_translation": "<Faithful English translation>",
  "is_deletion": <true|false>,
  "confidence": <0.0-1.0>,
  "reason": "<One sentence explanation based on the translated text>"
}}

User Request:
\"\"\"
{text}
\"\"\"
"""


def _llm_classify(text: str) -> Gate1Result | None:
    """Call OpenRouter to detect language, translate to English, and classify deletion intent."""
    try:
        from backend.agent.llm.openrouter_client import chat_completion  # late import
    except Exception:
        return None

    import json

    raw = chat_completion(
        prompt=_USER_TMPL.format(text=text[:2000]),
        system=_SYSTEM,
        temperature=0.0,
        max_tokens=256,
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
        confidence = float(obj.get("confidence", 0.95))
        reason = str(obj.get("reason", "LLM classified"))
        detected_lang = str(obj.get("detected_language", "English"))
        translation = str(obj.get("english_translation", text))
        return Gate1Result(
            ok=True,
            is_deletion=is_del,
            confidence=confidence,
            reason=f"[{detected_lang}] {reason}",
            detected_language=detected_lang,
            english_translation=translation,
        )
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
    raw = (request_text or "").strip()
    if not raw:
        return (
            False,
            "Empty request text",
            Gate1Result(ok=False, is_deletion=False, confidence=0.0, errors=["Empty request text"]),
        )

    # Normalize smart quotes and punctuation
    text = raw.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')

    # ── Tier 1a: regex non-deletion (fast exit) ──────────────────────────
    for pattern in NON_DELETION_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            is_negation_pattern = any(
                kw in pattern for kw in ["don", "do not", "how do", "can you tell", "access", "portab", "opt"]
            )
            if not is_negation_pattern:
                reason = f"Request does not authorize deletion: matched '{m.group(0)}'"
                return False, reason, Gate1Result(ok=True, is_deletion=False, confidence=0.99, reason=reason)
            # Try LLM to check if it's mixed request or negation
            llm_result = _llm_classify(text)
            if llm_result is not None:
                return llm_result.is_deletion, llm_result.reason, llm_result
            reason = f"Request does not authorize deletion: matched '{m.group(0)}'"
            return False, reason, Gate1Result(ok=True, is_deletion=False, confidence=0.90, reason=reason)

    # ── Tier 1b: regex deletion match ────────────────────────────────────
    deletion_match: re.Match | None = None
    for pattern in DELETION_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            deletion_match = m
            break

    if deletion_match:
        reason = f"Request authorizes deletion: matched '{deletion_match.group(0)}'"
        return True, reason, Gate1Result(ok=True, is_deletion=True, confidence=0.99, reason=reason)

    # ── Tier 2: LLM fallback for unrecognized text ───────────────────────
    llm_result = _llm_classify(text)
    if llm_result is not None:
        return llm_result.is_deletion, llm_result.reason, llm_result

    # ── Tier 3: Workflow claim heuristic fallback ────────────────────────
    if reported_status in ("COMPLETE", "PARTIALLY_COMPLETE"):
        reason = f"Deletion inferred from reported status '{reported_status}' without non-deletion patterns"
        return True, reason, Gate1Result(ok=True, is_deletion=True, confidence=0.85, reason=reason)

    reason = "Could not determine deletion intent; no patterns matched"
    return False, reason, Gate1Result(ok=True, is_deletion=False, confidence=0.50, reason=reason)

