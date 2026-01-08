from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

Vec3 = Tuple[float, float, float]

@dataclass(frozen=True)
class Triangle:
    n: Vec3
    a: Vec3
    b: Vec3
    c: Vec3

def _facet(n: Vec3, a: Vec3, b: Vec3, c: Vec3) -> str:
    return (
        f"facet normal {n[0]} {n[1]} {n[2]}\n"
        f"  outer loop\n"
        f"    vertex {a[0]} {a[1]} {a[2]}\n"
        f"    vertex {b[0]} {b[1]} {b[2]}\n"
        f"    vertex {c[0]} {c[1]} {c[2]}\n"
        f"  endloop\n"
        f"endfacet\n"
    )

def triangles_to_ascii_stl(name: str, tris: Iterable[Triangle]) -> bytes:
    body = "".join(_facet(t.n, t.a, t.b, t.c) for t in tris)
    stl = f"solid {name}\n{body}endsolid {name}\n"
    return stl.encode("utf-8")

def demo_cube_stl_ascii(size: float = 10.0) -> bytes:
    """ASCII STL cube centered at origin, edge length = size."""
    s = size / 2.0
    v000 = (-s, -s, -s)
    v001 = (-s, -s,  s)
    v010 = (-s,  s, -s)
    v011 = (-s,  s,  s)
    v100 = ( s, -s, -s)
    v101 = ( s, -s,  s)
    v110 = ( s,  s, -s)
    v111 = ( s,  s,  s)

    tris = [
        Triangle((1,0,0), v100, v110, v111),
        Triangle((1,0,0), v100, v111, v101),
        Triangle((-1,0,0), v000, v011, v010),
        Triangle((-1,0,0), v000, v001, v011),
        Triangle((0,1,0), v010, v011, v111),
        Triangle((0,1,0), v010, v111, v110),
        Triangle((0,-1,0), v000, v101, v001),
        Triangle((0,-1,0), v000, v100, v101),
        Triangle((0,0,1), v001, v101, v111),
        Triangle((0,0,1), v001, v111, v011),
        Triangle((0,0,-1), v000, v110, v100),
        Triangle((0,0,-1), v000, v010, v110),
    ]
    return triangles_to_ascii_stl("parametereyes_demo_cube", tris)
