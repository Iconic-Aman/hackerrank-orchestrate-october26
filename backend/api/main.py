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
