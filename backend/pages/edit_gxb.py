from __future__ import annotations

import hashlib
import logging
import re
import uuid
from pathlib import Path
from typing import Dict, Any, List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from utils.stl import demo_cube_stl_ascii

logger = logging.getLogger("parametereyes.pages.edit_gxb")

router = APIRouter(prefix="/edit-gxb", tags=["edit-gxb"])

WORK_DIR = Path(__file__).resolve().parents[1] / "_work" / "edit_gxb"
WORK_DIR.mkdir(parents=True, exist_ok=True)
logger.debug("WORK_DIR resolved to %s", WORK_DIR)

def extract_gxb_info(filename: str, data: bytes) -> Dict[str, Any]:
    logger.debug("extract_gxb_info(filename=%s, data_len=%d)", filename, len(data))

    size = len(data)
    logger.debug("size=%d", size)

    sha = hashlib.sha256(data).hexdigest()
    logger.debug("sha256=%s", sha)

    header_hex = data[:64].hex(" ")
    logger.debug("header_hex_64b=%s", header_hex)

    ascii_runs = re.findall(rb"[ -~]{6,}", data)
    logger.debug("ascii_runs_found=%d", len(ascii_runs))

    snippets: List[str] = []
    for idx, b in enumerate(ascii_runs[:10]):
        s = b.decode("utf-8", errors="ignore").strip()
        logger.debug("ascii_run[%d]=%r", idx, s[:160])
        if s:
            snippets.append(s[:120])

    info = {
        "filename": filename,
        "size_bytes": size,
        "sha256": sha,
        "header_hex_64b": header_hex,
        "ascii_snippets": snippets,
    }
    logger.debug("extract_gxb_info -> %s", {**info, "ascii_snippets": f"{len(snippets)} snippets"})
    return info

def decode_gxb_to_stl_bytes(data: bytes) -> bytes:
    """TODO: Replace with real `.gxb` -> `.stl` conversion."""
    logger.debug("decode_gxb_to_stl_bytes(data_len=%d) [DEMO]", len(data))
    stl = demo_cube_stl_ascii(size=20.0)
    logger.debug("decode_gxb_to_stl_bytes -> stl_len=%d", len(stl))
    return stl

@router.post("/handle")
async def handle_gxb(file: UploadFile = File(...)) -> Dict[str, Any]:
    logger.debug("handle_gxb() called")
    logger.debug("upload filename=%r content_type=%r", file.filename, file.content_type)

    if not file.filename or not file.filename.lower().endswith(".gxb"):
        logger.warning("Rejected upload: filename=%r", file.filename)
        raise HTTPException(status_code=400, detail="Please upload a .gxb file")

    logger.debug("Reading uploaded file bytes...")
    data = await file.read()
    logger.debug("Read complete: data_len=%d", len(data))

    if not data:
        logger.warning("Rejected upload: empty file")
        raise HTTPException(status_code=400, detail="Empty file")

    job_id = uuid.uuid4().hex[:12]
    logger.debug("Generated job_id=%s", job_id)

    job_dir = WORK_DIR / job_id
    logger.debug("Creating job_dir=%s", job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)

    logger.debug("Extracting info JSON...")
    info = extract_gxb_info(file.filename, data)

    logger.debug("Decoding GXB -> STL bytes...")
    stl_bytes = decode_gxb_to_stl_bytes(data)

    stl_path = job_dir / "model.stl"
    logger.debug("Writing STL to %s (len=%d)", stl_path, len(stl_bytes))
    stl_path.write_bytes(stl_bytes)

    resp = {
        "job_id": job_id,
        "info": info,
        "stl_url": f"/edit-gxb/stl/{job_id}",
        "note": "STL is currently a demo cube. Replace decode_gxb_to_stl_bytes() with real conversion.",
    }
    logger.info("handle_gxb OK job=%s file=%s bytes=%d", job_id, file.filename, len(data))
    logger.debug("handle_gxb response=%s", resp)
    return resp

@router.get("/stl/{job_id}")
def get_stl(job_id: str):
    logger.debug("get_stl(job_id=%s) called", job_id)
    stl_path = WORK_DIR / job_id / "model.stl"
    logger.debug("Resolved stl_path=%s", stl_path)

    if not stl_path.exists():
        logger.warning("STL not found: %s", stl_path)
        raise HTTPException(status_code=404, detail="STL not found for job_id")

    logger.info("Serving STL for job_id=%s (%d bytes)", job_id, stl_path.stat().st_size)
    return FileResponse(
        str(stl_path),
        media_type="model/stl",
        filename=f"{job_id}.stl",
    )
