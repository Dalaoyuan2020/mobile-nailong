"""Independent dimensional checks on delivered STEP faces and line sections."""

from pathlib import Path
import json
import math

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface


ROOT = Path(__file__).resolve().parent
TOL = 1e-5


def close(actual, expected):
    assert len(actual) == len(expected), (actual, expected)
    assert all(abs(a - b) < TOL for a, b in zip(actual, expected)), (actual, expected)


def section(shape, start, end, axis):
    line = cq.Edge.makeLine(cq.Vector(*start), cq.Vector(*end))
    spans = []
    for edge in shape.intersect(line).Edges():
        b = edge.BoundingBox()
        spans.append((getattr(b, axis + "min"), getattr(b, axis + "max")))
    return sorted(spans)


def spans_equal(actual, expected):
    close([v for pair in actual for v in pair], [v for pair in expected for v in pair])


def plane_faces(shape, axis, position):
    return [f for f in shape.Faces() if f.geomType() == "PLANE"
            and abs(getattr(f.BoundingBox(), axis + "len")) < TOL
            and abs(getattr(f.Center(), axis) - position) < TOL]


def verify():
    base = cq.importers.importStep(str(ROOT / "case26_base.step")).val()
    lid = cq.importers.importStep(str(ROOT / "case26_lid.step")).val()

    # An outer-edge slice sees only the pads, beyond the rounded shell floor.
    for y in (-229.9, 229.9):
        spans_equal(section(base, (-361, y, 0.1), (361, y, 0.1), "x"),
                    [(-300, -240), (240, 300)])

    # Actual cylindrical STEP surfaces establish hole size, count and position.
    for radius, axis, expected in [
        (3.3, "z", [(-270, -200), (-270, 200), (270, -200), (270, 200)]),
        (9.0, "x", [(-120, 40), (0, 40), (120, 40)]),
    ]:
        centers = []
        for face in base.Faces():
            if face.geomType() != "CYLINDER":
                continue
            cylinder = BRepAdaptor_Surface(face.wrapped).Cylinder()
            if abs(cylinder.Radius() - radius) >= TOL:
                continue
            direction = cylinder.Axis().Direction()
            assert abs(abs(getattr(direction, axis.upper())()) - 1) < TOL
            c = face.Center()
            centers.append((c.x, c.y) if axis == "z" else (c.y, c.z))
        spans_equal(sorted(centers), expected)

    for x in (-270, 270):
        for y in (-200, 200):
            spans_equal(section(base, (x, y, -1), (x, y, 25), "z"), [])
    for y in (-120, 0, 120):
        spans_equal(section(base, (350, y, 40), (361, y, 40), "x"), [])

    floors = sorted(plane_faces(lid, "z", 288), key=lambda f: f.Center().x)
    assert len(floors) == 3
    for x, floor in zip((-80, 0, 80), floors):
        b = floor.BoundingBox()
        close([floor.Center().x, b.xlen, b.ylen], [x, 40, 400])
        # Center and corner-adjacent sections retain 3 mm beneath each recess.
        for dx, y in ((0, 0), (-19, 190), (19, -190)):
            spans_equal(section(lid, (x + dx, y, 280), (x + dx, y, 291), "z"), [(285, 288)])

    handle = plane_faces(base, "x", -356)
    assert len(handle) == 1
    b = handle[0].BoundingBox()
    close([b.ylen, b.zlen], [160, 50])
    for y, z in ((0, 120), (-79, 103), (79, 137)):
        spans_equal(section(base, (-361, y, z), (-350, y, z), "x"), [(-356, -353)])

    # Matching annular faces at Z=170: a full cap would have a much larger area.
    seam_area = 720 * 470 - 714 * 464 - (4 - math.pi) * (20 ** 2 - 17 ** 2)
    for shape in (base, lid):
        faces = plane_faces(shape, "z", 170)
        assert len(faces) == 1
        close([faces[0].Area()], [seam_area])
        spans_equal(section(shape, (0, 0, 169), (0, 0, 171), "z"), [])

    print(json.dumps({"source": "exported STEP solids", "result": "PASS",
                      "checks": ["outer pad sections", "4 circular 6.6 mm through holes",
                                 "3 circular 18 mm through holes", "3 grooves 40 x 400 x 2 mm",
                                 "groove and handle floors retain 3 mm", "matching open seam at Z=170"]},
                     indent=2))


if __name__ == "__main__":
    verify()
