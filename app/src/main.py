"""
MedVault Public Health Reporting API - minimal demonstration application.

Security-relevant features wired in:
  - Structured JSON logging (AU-3 content of audit records)
  - Request ID propagation (AU-2 event logging)
  - Health and readiness endpoints (CP-2, SI-4)
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": int(time.time()),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        return json.dumps(payload)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
log = logging.getLogger("medvault")

app = FastAPI(title="MedVault Public Health Reporting API", version="0.1.0")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_ctx.set(rid)
    try:
        log.info(f"request.start method={request.method} path={request.url.path}")
        response = await call_next(request)
        log.info(f"request.end status={response.status_code}")
        response.headers["x-request-id"] = rid
        return response
    finally:
        request_id_ctx.reset(token)


class Report(BaseModel):
    jurisdiction: str = Field(..., min_length=2, max_length=64)
    indicator: str = Field(..., min_length=2, max_length=128)
    count: int = Field(..., ge=0)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.post("/v1/reports", status_code=202)
def submit_report(report: Report):
    log.info(f"report.received jurisdiction={report.jurisdiction} indicator={report.indicator}")
    return {"status": "accepted", "request_id": request_id_ctx.get()}