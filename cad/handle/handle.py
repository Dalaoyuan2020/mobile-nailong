"""Stowed handle for the upright 720 x 470 x 290 case; units mm."""

from pathlib import Path
import argparse
import json

import cadquery as cq

CASE_BOTTOM, CASE_TOP, CASE_FRONT = 70.0, 790.0, 145.0
PROJECTION = 350.0
TUBE_X, TUBE_SPACING = 139.0, 180.0
TUBE_OD, TUBE_WALL, TUBE_BOTTOM = 12.0, 1.2, 710.0
BAR_X, BAR_DEPTH, BAR_WIDTH, BAR_HEIGHT = 135.0, 20.0, 180.0, 15.0
SOCKET_X_MIN, SOCKET_X_MAX = 123.0, 145.0
SOCKET_WIDTH, SOCKET_BOTTOM, SOCKET_TOP = 26.0, 700.0, 790.0
SOCKET_RADIUS, BORE_D, BORE_BOTTOM = 2.0, 12.4, 706.0
SEAT_CLEARANCE = 0.2


def box(xsize, ysize, height, x, y, z):
    return (cq.Workplane("XY").box(xsize, ysize, height, centered=(True, True, False))
            .translate((x, y, z)))


def build_handle():
    """Three disjoint components: fused tube/grip frame and two embedded guide seats."""
    top = CASE_TOP + PROJECTION
    tube_top = top - BAR_HEIGHT / 2
    frame = box(BAR_DEPTH, BAR_WIDTH, BAR_HEIGHT, BAR_X, 0, top - BAR_HEIGHT)
    parts = {}
    for side, y in (("left", -TUBE_SPACING / 2), ("right", TUBE_SPACING / 2)):
        tube = (cq.Workplane("XY").center(TUBE_X, y)
                .circle(TUBE_OD / 2).circle(TUBE_OD / 2 - TUBE_WALL)
                .extrude(tube_top - TUBE_BOTTOM).translate((0, 0, TUBE_BOTTOM)))
        # Tube ends fuse into the grip; the frame is one simplified rigid part.
        frame = frame.union(tube)
        seat = box(SOCKET_X_MAX - SOCKET_X_MIN, SOCKET_WIDTH,
                   SOCKET_TOP - SOCKET_BOTTOM, (SOCKET_X_MIN + SOCKET_X_MAX) / 2,
                   y, SOCKET_BOTTOM).edges("|Z").fillet(SOCKET_RADIUS)
        bore = (cq.Workplane("XY").center(TUBE_X, y).circle(BORE_D / 2)
                .extrude(SOCKET_TOP - BORE_BOTTOM + 1).translate((0, 0, BORE_BOTTOM)))
        # Bore opens at X=145 as a C guide; 0.2 radial clearance and a bottom shoulder.
        parts[f"socket_{side}"] = seat.cut(bore).clean()
    return {"handle_frame": frame.clean(), **parts}


def seat_cutters():
    """Seat envelopes with 0.2 assembly clearance, for a copy of the upright shell."""
    return {
        f"socket_{side}": box(SOCKET_X_MAX - SOCKET_X_MIN + 2 * SEAT_CLEARANCE,
                              SOCKET_WIDTH + 2 * SEAT_CLEARANCE,
                              SOCKET_TOP - SOCKET_BOTTOM + 2 * SEAT_CLEARANCE,
                              (SOCKET_X_MIN + SOCKET_X_MAX) / 2, y,
                              SOCKET_BOTTOM - SEAT_CLEARANCE)
        for side, y in (("left", -TUBE_SPACING / 2), ("right", TUBE_SPACING / 2))
    }


def bounds(shape):
    b = shape.BoundingBox()
    return [b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax]


def check_bounds(shape, expected, label):
    if any(abs(a - b) > 1e-5 for a, b in zip(bounds(shape), expected)):
        raise ValueError(f"{label}: unexpected envelope {bounds(shape)}")


def validate(parts):
    for name, part in parts.items():
        if not part.val().isValid() or len(part.val().Solids()) != 1:
            raise ValueError(f"{name}: expected one valid solid")
    check_bounds(parts["handle_frame"].val(), [125, -96, 710, 145, 96, 1140], "frame")
    cutters = seat_cutters()
    for side, y in (("left", -90), ("right", 90)):
        seat = parts[f"socket_{side}"]
        check_bounds(seat.val(), [123, y - 13, 700, 145, y + 13, 790], side)
        if seat.intersect(parts["handle_frame"]).val().Volume() > 1e-5:
            raise ValueError("Seat and frame overlap")
        if seat.cut(cutters[f"socket_{side}"]).val().Volume() > 1e-5:
            raise ValueError("Seat cutter does not contain the complete seat")
        if seat.val().isInside((TUBE_X, y + 6.1, 750)):
            raise ValueError("Missing tube clearance")
        if not seat.val().isInside((TUBE_X, y + 6.3, 750)):
            raise ValueError("Guide wall missing")
        if not seat.val().isInside((TUBE_X, y, 703)):
            raise ValueError("Bottom shoulder missing")
    combined = cq.Compound.makeCompound([p.val() for p in parts.values()])
    check_bounds(combined, [123, -103, 700, 145, 103, 1140], "assembly")
    return {"units": "mm", "case_orientation": "upright",
            "case_z": [CASE_BOTTOM, CASE_TOP], "projection_above_case": PROJECTION,
            "tube_spacing": TUBE_SPACING, "tube_od": TUBE_OD, "tube_wall": TUBE_WALL,
            "tube_axes_xy": [[TUBE_X, -90], [TUBE_X, 90]],
            "tube_bottom_z": TUBE_BOTTOM, "tube_insertion_below_case_top": CASE_TOP - TUBE_BOTTOM,
            "guide_radial_clearance": (BORE_D - TUBE_OD) / 2,
            "seat_cut_clearance": SEAT_CLEARANCE, "frame_and_seat_overlap_mm3": 0,
            "bounds": bounds(combined), "named_parts": list(parts),
            "valid_solids": 3}


def export_all(out):
    out.mkdir(parents=True, exist_ok=True)
    parts = build_handle()
    report = validate(parts)
    assembly = cq.Assembly(name="upright_stowed_handle")
    for name, part in parts.items():
        color = cq.Color(0.62, 0.64, 0.66) if name == "handle_frame" else cq.Color(0.14, 0.15, 0.16)
        assembly.add(part, name=name, color=color)
        cq.exporters.export(part, str(out / f"{name}.step"))
        cq.exporters.export(part, str(out / f"{name}.stl"), tolerance=0.06, angularTolerance=0.1)
    assembly.export(str(out / "handle.step"))
    imported = cq.importers.importStep(str(out / "handle.step")).val()
    if not imported.isValid() or len(imported.Solids()) != 3:
        raise ValueError("Handle STEP round trip must contain three valid solids")
    check_bounds(imported, [123, -103, 700, 145, 103, 1140], "STEP assembly")
    import trimesh
    meshes, mesh_report = [], {}
    for name in parts:
        mesh = trimesh.load_mesh(out / f"{name}.stl")
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        if not mesh.is_watertight or not mesh.is_winding_consistent or len(mesh.split()) != 1:
            raise ValueError(f"{name}: STL must be a single watertight, consistently oriented mesh")
        mesh.export(out / f"{name}.stl")
        meshes.append(mesh)
        mesh_report[name] = {"watertight": True, "triangles": len(mesh.faces)}
    trimesh.util.concatenate(meshes).export(out / "handle.stl")
    report.update({"step_round_trip": "valid, 3 solids", "stl_checks": mesh_report})
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    export_all(parser.parse_args().out)
