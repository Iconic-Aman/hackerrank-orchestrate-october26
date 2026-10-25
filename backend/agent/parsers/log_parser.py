from __future__ import annotations
import re
import json
from datetime import datetime
from pathlib import Path
from backend.agent.models import Fact, Coverage

def _parse_line(s: str) -> tuple[str | None, dict[str, str]]:
    s = s.strip()
    if not s:
        return None, {}
    
    parts = s.split(maxsplit=1)
    ts_str = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    # 1. Try JSON in rest part
    rest_clean = rest.strip()
    if rest_clean.startswith("{") and rest_clean.endswith("}"):
        try:
            obj = json.loads(rest_clean)
            if isinstance(obj, dict):
                fields = {str(k): (str(v) if v is not None else "") for k, v in obj.items()}
                return ts_str, fields
        except Exception:
            pass

    # 2. Try whole line as JSON
    if s.startswith("{") and s.endswith("}"):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                line_ts = obj.get("timestamp") or obj.get("time") or ts_str
                fields = {str(k): (str(v) if v is not None else "") for k, v in obj.items()}
                return str(line_ts), fields
        except Exception:
            pass

    # 3. Fallback to key=value regex
    kv_matches = re.findall(r'(\w+)=(?:"([^"]*)"|(\S+))', s)
    fields = {k: (v1 if v1 != "" else v2) for k, v1, v2 in kv_matches}
    return ts_str, fields

def _extract_subject_identifier(fields: dict[str, str]) -> str | None:
    for key in [
        "subject_ref", "customer_reference", "subject_reference", "user_id",
        "lookup_key", "subject_key", "correlation_key", "match_key",
        "customer_email", "requester_email", "email"
    ]:
        val = fields.get(key)
        if val and val.strip() and val.strip().lower() not in ("null", "none"):
            return val.strip()
    return None

def parse_log_lines(
    file_path: Path | str,
    file_id: str,
    default_time: datetime | None = None,
    resource_system_map: dict[str, str] | None = None,
) -> tuple[list[Fact], list[Coverage]]:
    path = Path(file_path)
    facts: list[Fact] = []
    systems_seen: set[str] = set()
    sys_map = resource_system_map or {}
    latest_time = default_time or datetime.now()

    trace_to_subjects: dict[str, set[str]] = {}
    trace_to_ident: dict[str, str] = {}
    unparsed_count = 0

    # First pass: collect trace_id -> identifier mappings (per-file)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            ts_str, fields = _parse_line(line)
            if not fields:
                if line.strip():
                    unparsed_count += 1
                continue
            t_id = fields.get("trace_id")
            ident = _extract_subject_identifier(fields)
            if t_id and ident:
                trace_to_subjects.setdefault(t_id, set()).add(ident)

    # Only link if unambiguous (exactly 1 subject associated with trace)
    for t_id, subjects in trace_to_subjects.items():
        if len(subjects) == 1:
            trace_to_ident[t_id] = next(iter(subjects))

    # Second pass: construct facts
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f, start=1):
            ts_str, fields = _parse_line(line)
            if not fields:
                continue

            if ts_str:
                try:
                    line_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if default_time is None or line_time > latest_time:
                        latest_time = line_time
                except Exception:
                    pass

            fields["raw_line"] = line.strip()
            if ts_str:
                fields["event_time"] = ts_str

            t_id = fields.get("trace_id")
            if t_id and t_id in trace_to_ident:
                resolved_subject = trace_to_ident[t_id]
                fields["linked_via_trace"] = t_id
                if not fields.get("lookup_key"):
                    fields["lookup_key"] = resolved_subject
                if not fields.get("subject_ref"):
                    fields["subject_ref"] = resolved_subject
                if not fields.get("customer_reference"):
                    fields["customer_reference"] = resolved_subject

            res_id = fields.get("resource_id")
            service = fields.get("service") or fields.get("logger") or "unknown_service"

            if res_id:
                prefix = res_id.rsplit("_", 1)[0] if "_" in res_id else res_id
                system_id = sys_map.get(prefix, service)
            else:
                system_id = service
            systems_seen.add(system_id)

            ev = fields.get("event", "")
            # Transient query start lines do not create facts; they only supply links
            if ev.endswith("_started"):
                continue

            rows_val = fields.get("rows")
            http_val = fields.get("http_status")
            enabled_val = fields.get("enabled")
            marker_found = fields.get("marker_found")

            if rows_val == "0" or http_val == "404":
                raw_state = "ABSENT"
            elif rows_val == "1" or marker_found == "false" or fields.get("integrity_check") == "passed":
                raw_state = "PRESENT"
            elif enabled_val == "false" or fields.get("last_delivery_status") == "stopped":
                raw_state = "DISABLED"
            elif enabled_val == "true":
                raw_state = "ACTIVE"
            elif fields.get("blocked") == "true":
                raw_state = "BLOCKED"
            elif fields.get("anonymized") == "true":
                raw_state = "ANONYMIZED"
            else:
                raw_state = "PRESENT" if res_id else ev

            if res_id:
                category = "DATA_FLOW" if "data_flow" in res_id else ("SUPPORT_MESSAGE" if "support" in system_id else None)
                facts.append(
                    Fact(
                        file_id=file_id,
                        system_id=system_id,
                        collection="log_stream",
                        resource_id=res_id,
                        category=category,
                        raw_state=raw_state,
                        fields=fields,
                        locator=f"line:{idx}",
                        confidence=1.0,
                    )
                )

    coverage = [
        Coverage(
            file_id=file_id,
            system_id=sys,
            collection="log_stream",
            captured_at=latest_time,
            row_count=sum(1 for f in facts if f.system_id == sys),
        )
        for sys in sorted(systems_seen)
    ]
    return facts, coverage
