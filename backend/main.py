"""
main.py

FastAPI backend for the CS2 stats site.

POST /api/parse  -> accepts a .dem file upload, parses it with awpy,
                     returns the full stats payload as JSON.
GET  /api/health -> simple liveness check.

Run locally:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CS2 Stats Parser API")

WORKER_SCRIPT = Path(__file__).parent / "parse_worker.py"
PARSE_TIMEOUT_SECONDS = 120

# CS2 demo headers alone are a few hundred bytes; real matches are MBs.
# Anything under this is almost certainly empty/truncated/garbage and will
# crash the native parser (it has been observed to panic on a 0-byte file),
# so we reject it up front rather than letting it reach the parser at all.
MIN_DEMO_BYTES = 1024

# Allowed frontend origins. Local dev ports are always allowed; the deployed
# frontend's origin is added via the FRONTEND_ORIGIN env var (set this in
# Railway's dashboard once you know your Vercel URL).
_default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
_extra_origin = os.environ.get("FRONTEND_ORIGIN")
allow_origins = _default_origins + ([_extra_origin] if _extra_origin else [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 512MB RAM is the ceiling on Render's free web service tier, and the parser
# (a Rust library wrapped via PyO3, plus polars DataFrames built from the
# parsed events) needs headroom several times larger than the raw file size
# to do its work. 80MB keeps a typical ~20-30 round competitive demo
# comfortably inside that budget; raise this if you upgrade to a paid tier
# with more RAM.
MAX_UPLOAD_BYTES = 80 * 1024 * 1024


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/parse")
async def parse_demo(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".dem"):
        raise HTTPException(status_code=400, detail="Please upload a .dem file.")

    # Stream to a temp file rather than loading the whole upload into memory,
    # since demos can be 100MB+.
    tmp_dir = tempfile.mkdtemp(prefix="cs2demo_")
    tmp_path = Path(tmp_dir) / "match.dem"

    size = 0
    try:
        with open(tmp_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Demo file is too large (limit 300MB).",
                    )
                f.write(chunk)

        if size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        if size < MIN_DEMO_BYTES:
            raise HTTPException(
                status_code=400,
                detail="This file is too small to be a valid CS2 demo.",
            )

        try:
            result = subprocess.run(
                [sys.executable, str(WORKER_SCRIPT), str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=PARSE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=504,
                detail="Parsing this demo took too long and was cancelled.",
            ) from exc

        if result.returncode != 0:
            # The worker process either raised a clean Python exception or
            # the native parser crashed/panicked. Either way, the API
            # process itself is unaffected, and we surface a clean error.
            stderr_tail = (result.stderr or "").strip().splitlines()
            detail_line = stderr_tail[-1] if stderr_tail else "Unknown parse failure."
            raise HTTPException(
                status_code=422,
                detail=(
                    "Couldn't parse this demo. It may be corrupted, from an "
                    f"unsupported game mode, or an unexpected format. ({detail_line})"
                ),
            )

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=500,
                detail="Parser produced an unexpected response.",
            ) from exc

        return payload

    finally:
        # Clean up the temp file/dir regardless of outcome.
        try:
            if tmp_path.exists():
                tmp_path.unlink()
            Path(tmp_dir).rmdir()
        except OSError:
            pass
