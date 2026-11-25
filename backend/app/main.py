import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from . import analytics, demo, experiments, images, security, workspace
from .db import engine

app = FastAPI(title="DemandTwin", version="0.1.0", description="Provenance-aware consumer experiments and conditional market simulation.")
origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-Participant-Key"])


@app.middleware("http")
async def security_headers(request, call_next):
    if request.headers.get("sec-fetch-site") == "cross-site" and request.method not in {"GET", "HEAD", "OPTIONS"}:
        return JSONResponse({"detail": "Cross-site writes are blocked"}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api/v1"):
        response.headers.setdefault("Cache-Control", "private, no-store")
    return response


@app.get("/api/v1/health", tags=["system"])
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ok", "database": engine.dialect.name}


for router in (security.router, workspace.router, experiments.router, analytics.router, images.router, demo.router):
    app.include_router(router, prefix="/api/v1")
