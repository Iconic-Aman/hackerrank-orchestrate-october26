from __future__ import annotations
from datetime import datetime
from pathlib import Path
from backend.agent.models import Fact, Coverage
from backend.agent.parsers.pipe_table import parse_pipe_table
from backend.agent.parsers.json_bundle import parse_json_bundle
from backend.agent.parsers.sql_parser import parse_sql_snapshot
from backend.agent.parsers.log_parser import parse_log_lines

def parse_evidence_file(
    file_path: Path | str,
    file_id: str,
    captured_at: datetime | None = None,
    resource_system_map: dict[str, str] | None = None,
) -> tuple[list[Fact], list[Coverage]]:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".txt":
        return parse_pipe_table(path, file_id, default_time=captured_at)
    elif ext == ".json":
        return parse_json_bundle(path, file_id, default_time=captured_at)
    elif ext == ".sql":
        return parse_sql_snapshot(path, file_id, default_time=captured_at, resource_system_map=resource_system_map)
    elif ext == ".log":
        return parse_log_lines(path, file_id, default_time=captured_at, resource_system_map=resource_system_map)
    else:
        # Fallback empty for binary/unsupported
        coverage = [
            Coverage(
                file_id=file_id,
                system_id="unsupported_format",
                collection=ext.lstrip("."),
                captured_at=captured_at or datetime.now(),
                row_count=0,
            )
        ]
        return [], coverage
