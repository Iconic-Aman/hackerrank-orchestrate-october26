from __future__ import annotations
import os
import re
from pathlib import Path
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def _find_env_secrets() -> set[str]:
    """Load SECRET_KEY and VITE_SECRET_KEY from environment and .env files."""
    secrets = set()

    # 1. Process environment
    for key in ("SECRET_KEY", "VITE_SECRET_KEY"):
        val = os.getenv(key)
        if val:
            clean = val.strip().strip("'\"")
            if clean:
                secrets.add(clean)

    # 2. Check candidate .env locations (root, backend, etc.)
    base_dir = Path(__file__).resolve().parent.parent.parent
    candidates = [
        base_dir / ".env",
        base_dir / "backend" / ".env",
        base_dir / "frontend" / ".env",
        Path(".env"),
        Path("backend/.env"),
    ]

    for p in candidates:
        if p.is_file():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    m = re.match(r"^(?:SECRET_KEY|VITE_SECRET_KEY)\s*=\s*(.*)$", line)
                    if m:
                        val = m.group(1).strip().strip("'\"")
                        if val:
                            secrets.add(val)
                            # Export to os.environ so other modules can use it
                            if "SECRET_KEY" not in os.environ:
                                os.environ["SECRET_KEY"] = val
            except Exception:
                pass

    secrets.add("dev-secret-key")
    return secrets


def verify_token(creds: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    allowed_secrets = _find_env_secrets()

    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token in Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    incoming = creds.credentials.strip().strip("'\"")

    if incoming not in allowed_secrets:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return incoming
