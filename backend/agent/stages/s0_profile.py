from __future__ import annotations
import csv
import hashlib
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field

class Gate0Result(BaseModel):
    ok: bool
    manifest_files_count: int
    hash_algorithm: str
    errors: list[str] = Field(default_factory=list)

class SchemaMap(BaseModel):
    formats: dict[str, str]
    csv_roles: dict[str, dict[str, str]]
    identifier_kinds: dict[str, dict[str, Any]]
    email_hash: dict[str, Any]
    state_vocab: dict[str, str]
    resource_system_map: dict[str, str]
    category_kinds: dict[str, str]

def detect_email_hash(identities_csv: Path) -> dict[str, Any]:
    with open(identities_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))[:50]
    for algo in ["sha256", "sha512", "md5", "sha1"]:
        matches = sum(
            getattr(hashlib, algo)(r["email"].strip().lower().encode("utf-8")).hexdigest() == r["email_hash"]
            for r in rows
        )
        if matches == len(rows) and len(rows) > 0:
            return {"algorithm": algo, "input_normalize": ["strip", "lower"]}
    raise ValueError("Could not determine email hash algorithm from identities")

def profile_dataset(dataset_dir: Path | str) -> tuple[SchemaMap, Gate0Result]:
    dataset_path = Path(dataset_dir)
    errors: list[str] = []
    
    # 1. Email hash
    hash_info = detect_email_hash(dataset_path / "user_identities.csv")
    
    # 2. Evidence manifest check
    manifest_file = dataset_path / "evidence_files.csv"
    manifest_count = 0
    with open(manifest_file, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            manifest_count += 1
            if not (dataset_path / row["file_path"]).exists():
                errors.append(f"Missing evidence file: {row['file_path']}")

    formats = {
        ".sql": "sql",
        ".json": "json_snapshots",
        ".txt": "pipe_table",
        ".log": "log_lines",
        ".pdf": "pdf_text",
        ".png": "image_vision",
    }
    
    # 3. Rules validation
    with open(dataset_path / "deletion_rules.csv", "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["required_action"] not in {"DELETE", "REDACT", "ANONYMIZE", "RETAIN"}:
                errors.append(f"Invalid rule action: {r['required_action']} for {r['rule_id']}")

    resource_system_map = {
        "account": "account_service",
        "analytics": "analytics_platform",
        "audit_record": "security_service",
        "backup": "backup_service",
        "cache": "cache_service",
        "data_flow": "integration_service",
        "email_delivery": "email_delivery_service",
        "export": "export_service",
        "legal_hold": "legal_service",
        "marketing": "marketing_platform",
        "object": "object_storage",
        "search": "search_service",
        "support": "support_platform",
        "tombstone": "identity_service",
    }

    category_kinds = {
        "USER_PROFILE": "record",
        "SECONDARY_IDENTIFIER": "record",
        "SEARCH_INDEX_ENTRY": "record",
        "CACHE_ENTRY": "record",
        "SUPPORT_MESSAGE": "record",
        "SUPPORT_ATTACHMENT": "record",
        "ANALYTICS_PROFILE": "record",
        "PRODUCT_TELEMETRY": "record",
        "USER_EXPORT": "record",
        "MARKETING_PROFILE": "record",
        "EMAIL_DELIVERY_LOG": "record",
        "SECURITY_AUDIT_LOG": "record",
        "LEGAL_HOLD_RECORD": "record",
        "BACKUP_ARCHIVE": "restore_path",
        "ACCOUNT_TOMBSTONE": "record",
        "DATA_FLOW": "flow",
    }

    schema_map = SchemaMap(
        formats=formats,
        csv_roles={
            "identities": {"user_id": "user_id", "email": "email", "phone": "phone", "name": "name", "email_hash": "email_hash"},
            "audit_log": {"field_name": "field_name", "old_value": "old_value", "new_value": "new_value", "event_time": "event_time"},
            "activity": {"activity_id": "activity_id", "event_time": "event_time", "event_type": "event_type", "target_system": "target_system", "resource_id": "resource_id"},
        },
        identifier_kinds={
            "email": {"normalize": ["strip", "lower"], "strength": "strong"},
            "phone": {"normalize": ["digits_only"], "strength": "strong"},
            "email_hash": {"normalize": ["strip", "lower"], "strength": "strong"},
            "user_id": {"normalize": ["strip"], "strength": "strong"},
            "name": {"normalize": ["casefold", "collapse_ws"], "strength": "weak"},
        },
        email_hash=hash_info,
        state_vocab={
            "NOT_FOUND": "ABSENT",
            "FOUND": "PRESENT",
            "IDENTIFIABLE": "IDENTIFIABLE",
            "ACTIVE": "ACTIVE",
            "ANONYMIZED": "ANONYMIZED",
            "REDACTED": "REDACTED",
            "BLOCKED": "BLOCKED",
            "DISABLED": "DISABLED",
        },
        resource_system_map=resource_system_map,
        category_kinds=category_kinds,
    )
    
    gate0 = Gate0Result(
        ok=(len(errors) == 0),
        manifest_files_count=manifest_count,
        hash_algorithm=hash_info["algorithm"],
        errors=errors,
    )
    return schema_map, gate0

def save_schema_map(schema_map: SchemaMap, out_path: Path | str) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(schema_map.model_dump(), f, sort_keys=False)
