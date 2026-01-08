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
import mtlsplus
import numpy as np

logger = logging.getLogger("parametereyes.pages.edit_gxb")

router = APIRouter(prefix="/edit-gxb", tags=["edit-gxb"])

WORK_DIR = Path(__file__).resolve().parents[1] / "_work" / "edit_gxb"
WORK_DIR.mkdir(parents=True, exist_ok=True)
logger.debug("WORK_DIR resolved to %s", WORK_DIR)

def extract_gxb_info(glasses, filename) -> Dict[str, Any]:
    curve_sliders_info = {}

    for i in range(glasses.number_of_curved_sliders):
        curved_slider = mtlsplus.eyeweardesign.get_curved_slider(
            glasses=glasses,
            index=i
        )
        curve_sliders_info[i] = curved_slider

    curve_warpers_info = {}
    for i in range(glasses.number_of_curve_warpers):
        curve_warper = mtlsplus.eyeweardesign.get_curve_warper(
            glasses=glasses,
            index=i
        )
        curve_warpers_info[i] = curve_warper

    mirrors_info = {}
    for i in range(glasses.number_of_mirrors):
        mirror = mtlsplus.eyeweardesign.get_mirror(
            glasses=glasses,
            index=i
        )
        mirrors_info[i] = mirror

    scalers_info = {}
    for i in range(glasses.number_of_scalers):
        scaler = mtlsplus.eyeweardesign.get_scaler(
            glasses=glasses,
            index=i
        )
        scalers_info[i] = scaler

    reference_points_info = {}
    for i in range(glasses.number_of_reference_points):
        ref_point = mtlsplus.eyeweardesign.get_reference_point(
            glasses=glasses,
            index=i
        )
        reference_points_info[i] = ref_point

    regions_info = {}
    for i in range(glasses.number_of_regions):
        region = mtlsplus.eyeweardesign.get_region(
            glasses=glasses,
            index=i
        )
        regions_info[i] = region

    parameters_info = {}
    for i in range(glasses.number_of_parameters):
        parameter = mtlsplus.eyeweardesign.get_parameter(
            glasses=glasses,
            index=i
        )
        parameters_info[i] = parameter

    framelist_benders_info = {}
    for i in range(glasses.number_of_framelist_benders):
        bender = mtlsplus.eyeweardesign.get_framelist_bender(
            glasses=glasses,
            index=i
        )
        framelist_benders_info[i] = bender

    triangle_collections_info = {}
    for i in range(glasses.number_of_triangle_collections):
        tri_collection = mtlsplus.eyeweardesign.get_triangle_collection(
            glasses=glasses,
            index=i
        )
        triangle_collections_info[i] = tri_collection

    point_collections_info = {}
    for i in range(glasses.number_of_point_collections):
        point_collection = mtlsplus.eyeweardesign.get_point_collection(
            glasses=glasses,
            index=i
        )
        point_collections_info[i] = point_collection

    csg_operations_info = {}
    for i in range(glasses.number_of_csg_operations):
        csg_op = mtlsplus.eyeweardesign.get_csg_operation(
            glasses=glasses,
            index=i
        )
        csg_operations_info[i] = csg_op        


    info = {
        "filename": filename,
        "curve_sliders_info": curve_sliders_info
    }

    info = {
        "filename": filename,
        "curve_sliders_info": curve_sliders_info,
        "curve_warpers_info": curve_warpers_info,
        "mirrors_info": mirrors_info,
        "scalers_info": scalers_info,
        "reference_points_info": reference_points_info,
        "regions_info": regions_info,
        "parameters_info": parameters_info,
        "framelist_benders_info": framelist_benders_info,
        "triangle_collections_info": triangle_collections_info,
        "point_collections_info": point_collections_info,
        "csg_operations_info": csg_operations_info
    }

    return info

def decode_gxb_to_stl_bytes(glasses, header: bytes = b"numpy-stl") -> bytes:
    """TODO: Replace with real `.gxb` -> `.stl` conversion."""
    v = glasses.vertices.astype(np.float32, copy=False)
    t = glasses.triangles.astype(np.int32, copy=False)

    v1 = v[t[:, 0]]
    v2 = v[t[:, 1]]
    v3 = v[t[:, 2]]

    normals = np.cross(v2 - v1, v3 - v1)
    lens = np.linalg.norm(normals, axis=1)
    normals = np.divide(normals, lens[:, None], out=np.zeros_like(normals), where=lens[:, None] > 0)

    tri_count = t.shape[0]
    dtype = np.dtype([
        ("normal", "<f4", (3,)),
        ("v1", "<f4", (3,)),
        ("v2", "<f4", (3,)),
        ("v3", "<f4", (3,)),
        ("attr", "u2"),
    ])

    data = np.zeros(tri_count, dtype=dtype)
    data["normal"] = normals
    data["v1"] = v1
    data["v2"] = v2
    data["v3"] = v3
    data["attr"] = 0

    header80 = header[:80].ljust(80, b"\0")
    return header80 + np.uint32(tri_count).tobytes() + data.tobytes()


@router.post("/handle")
async def handle_gxb(file: UploadFile = File(...)) -> Dict[str, Any]:
    logger.debug("handle_gxb() called")
    logger.debug(f"file path: {file}")
    logger.debug("upload filename=%r content_type=%r", file.filename, file.content_type)
    extensions = (".gxf", ".gxb")
    if not file.filename or not file.filename.lower().endswith(extensions):
        logger.warning("Rejected upload: filename=%r", file.filename)
        raise HTTPException(status_code=400, detail="Please upload a .gxb file")

    logger.debug("Reading uploaded file bytes...")
    data = await file.read()
    logger.debug("Read complete: data_len=%d", len(data))

    if not data:
        logger.warning("Rejected upload: empty file")
        raise HTTPException(status_code=400, detail="Empty file")
    
    
    glasses = mtlsplus.eyeweardesign.load_from_stream(
        byte_stream=data
    ).glasses
    logger.debug(f"Glasses: {glasses}")

    job_id = uuid.uuid4().hex[:12]
    logger.debug("Generated job_id=%s", job_id)

    job_dir = WORK_DIR / job_id
    logger.debug("Creating job_dir=%s", job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)

    logger.debug("Extracting info JSON...")
    info = extract_gxb_info(glasses, file.filename)

    logger.debug("Decoding GXB -> STL bytes...")
    stl_bytes = decode_gxb_to_stl_bytes(glasses)

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
