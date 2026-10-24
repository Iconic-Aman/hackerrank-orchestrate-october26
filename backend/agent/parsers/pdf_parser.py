from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
import fitz  # PyMuPDF
from backend.agent.models import Fact, Coverage

def parse_pdf_document(
    file_path: Path | str,
    file_id: str,
    default_time: datetime | None = None,
    resource_system_map: dict[str, str] | None = None,
) -> tuple[list[Fact], list[Coverage]]:
    path = Path(file_path)
    facts: list[Fact] = []
    sys_map = resource_system_map or {}
    cap_time = default_time or datetime.now()

    doc = fitz.open(path)
    all_text = ""
    for page_idx, page in enumerate(doc):
        page_text = page.get_text()
        all_text += f"\n--- Page {page_idx + 1} ---\n" + page_text

    # Extract resource IDs
    res_matches = re.findall(r"\b(support_\w+|legal_hold_\w+|audit_record_\w+|account_\w+)\b", all_text)
    distinct_res = sorted(set(res_matches))

    # Guess system
    if any("support" in r for r in distinct_res) or "delivery" in path.name.lower():
        default_sys = "support_platform"
        category = "SUPPORT_ATTACHMENT"
    elif any("legal" in r for r in distinct_res) or "legal" in path.name.lower():
        default_sys = "legal_service"
        category = "LEGAL_HOLD_RECORD"
    elif any("security" in r for r in distinct_res):
        default_sys = "security_service"
        category = "SECURITY_AUDIT_LOG"
    else:
        default_sys = "document_service"
        category = "USER_PROFILE"

    if not distinct_res:
        distinct_res = [f"doc_{path.stem}"]

    for res_id in distinct_res:
        prefix = res_id.rsplit("_", 1)[0] if "_" in res_id else res_id
        effective_sys = sys_map.get(prefix, default_sys)
        facts.append(
            Fact(
                file_id=file_id,
                system_id=effective_sys,
                collection="documents",
                resource_id=res_id,
                category=category,
                raw_state="PRESENT",
                fields={"content": all_text, "filename": path.name},
                locator=f"file:{path.name}",
                confidence=1.0,
            )
        )

    coverage = [
        Coverage(
            file_id=file_id,
            system_id=default_sys,
            collection="documents",
            captured_at=cap_time,
            row_count=len(facts),
        )
    ]
    return facts, coverage
