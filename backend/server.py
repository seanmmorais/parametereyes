from __future__ import annotations

import os
import sys
import time
import logging
import traceback
from pathlib import Path
from typing import Callable, Any, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from pages.home import router as home_router
from pages.edit_gxb import router as edit_gxb_router

LOG_DIR = Path(__file__).resolve().parent / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")

LOG_LEVEL = os.environ.get("PARAMEYES_LOG_LEVEL", "DEBUG").upper()
TRACE_LINES = _env_bool("PARAMEYES_TRACE_LINES", False)  # EXTREMELY VERBOSE

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_DIR / "backend.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("parametereyes.backend")

def _install_line_tracer(mod_prefixes: Optional[list[str]] = None) -> None:
    """Log executed lines for selected modules. Turn on with PARAMEYES_TRACE_LINES=1."""
    if not TRACE_LINES:
        return

    trace_log = logging.getLogger("parametereyes.trace")
    trace_fh = logging.FileHandler(LOG_DIR / "trace.log", encoding="utf-8")
    trace_fh.setLevel(logging.DEBUG)
    trace_fh.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d %(message)s", "%Y-%m-%d %H:%M:%S"))
    trace_log.addHandler(trace_fh)
    trace_log.setLevel(logging.DEBUG)

    prefixes = mod_prefixes or ["backend", "pages", "utils"]
    base_dir = str(Path(__file__).resolve().parent)

    def tracer(frame, event, arg):
        try:
            if event != "line":
                return tracer
            filename = frame.f_code.co_filename
            # only trace our project files
            if not filename.startswith(base_dir):
                return tracer
            rel = filename[len(base_dir):].lstrip("/\\")
            if not any(rel.startswith(p) for p in prefixes):
                return tracer
            lineno = frame.f_lineno
            code = frame.f_code
            # read the actual source line (best-effort)
            line = ""
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if 1 <= lineno <= len(lines):
                    line = lines[lineno-1].rstrip("\n")
            except Exception:
                pass
            trace_log.debug(f"{rel}:{lineno} | {code.co_name} | {line}")
        except Exception:
            # never crash the app due to tracing
            pass
        return tracer

    sys.settrace(tracer)
    threading = __import__("threading")
    threading.settrace(tracer)
    logger.warning("PARAMEYES_TRACE_LINES=1 enabled. This is VERY VERBOSE and can slow the backend.")

_install_line_tracer()

app = FastAPI(title="Parametereyes Backend", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Desktop UI file:// often yields origin "null"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next: Callable[[Request], Any]) -> Response:
    start = time.perf_counter()
    rid = os.urandom(4).hex()
    logger.debug("REQ %s -> %s %s", rid, request.method, request.url.path)
    try:
        response: Response = await call_next(request)
        dur_ms = (time.perf_counter() - start) * 1000
        logger.debug("RES %s <- %s %s (%s) %.2fms", rid, request.method, request.url.path, response.status_code, dur_ms)
        return response
    except Exception as e:
        dur_ms = (time.perf_counter() - start) * 1000
        logger.error("ERR %s !! %s %s %.2fms: %s", rid, request.method, request.url.path, dur_ms, e)
        logger.error("TRACEBACK %s\n%s", rid, traceback.format_exc())
        raise

@app.on_event("startup")
async def on_startup():
    logger.info("Backend starting up (LOG_LEVEL=%s TRACE_LINES=%s)", LOG_LEVEL, TRACE_LINES)

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Backend shutting down")

app.include_router(home_router)
app.include_router(edit_gxb_router)

def main() -> None:
    import uvicorn
    port = int(os.environ.get("PARAMEYES_BACKEND_PORT", "5123"))
    logger.info("Launching uvicorn on http://127.0.0.1:%d", port)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    main()
