from __future__ import annotations
from pathlib import Path
import yaml
from pydantic import BaseModel, Field

class OperationDef(BaseModel):
    phase: str
    state: str
    order: int

class TreatmentDef(BaseModel):
    kind: str
    action: str
    target: str
    finding: str | None = None
    fix: str | None = None
    verify: str | None = None

class OperationsConfig(BaseModel):
    phases: list[str]
    operations: dict[str, OperationDef]
    treatments: list[TreatmentDef]
    strength: dict[str, int]
    evidence_id_empty: str = ""

def load_operations_config(config_path: Path | str | None = None) -> OperationsConfig:
    if config_path is None:
        config_path = Path(__file__).resolve().parent / "operations.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return OperationsConfig.model_validate(data)
