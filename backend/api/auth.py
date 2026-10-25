from __future__ import annotations
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)

def verify_token(creds: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    secret = os.getenv("SECRET_KEY", "dev-secret-key")
    if not creds or creds.credentials != secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return creds.credentials
