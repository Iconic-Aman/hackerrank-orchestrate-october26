from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Ghost Data Audit API",
    description="Operational API for deletion-audit verification.",
    version="1.0.0",
)

# CORS configuration
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Depends
from backend.api.auth import verify_token
from backend.api.routes.analytics import router as analytics_router
from backend.api.routes.audit import router as audit_router
from backend.api.routes.cases import router as cases_router
from backend.api.routes.stats import router as stats_router

app.include_router(cases_router, prefix="/api/v1", dependencies=[Depends(verify_token)])
app.include_router(stats_router, prefix="/api/v1", dependencies=[Depends(verify_token)])
app.include_router(audit_router, prefix="/api/v1", dependencies=[Depends(verify_token)])
app.include_router(analytics_router, prefix="/api/v1", dependencies=[Depends(verify_token)])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="ghost-data-audit",
        version="1.0.0",
    )

@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    return {"message": "Ghost Data Audit API is running. Visit /docs for OpenAPI documentation."}

