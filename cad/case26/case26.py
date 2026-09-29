"""26-inch case only. Units: mm. Run: python cad/case26/case26.py"""

from pathlib import Path
import argparse
import json

import cadquery as cq

L, W, H = 720.0, 470.0, 290.0
WALL, RADIUS, SPLIT = 3.0, 20.0, 170.0
WHEEL_XY = [(x, y) for x in (-270.0, 270.0) for y in (-200.0, 200.0)]
WHEEL_HOLE_D = 6.6  # M6 clearance hole, not an internal thread.
WHEEL_PAD = 60.0
SENSOR_Y = (-120.0, 0.0, 120.0)
SENSOR_D, SENSOR_Z = 18.0, 40.0
STRAP_X = (-80.0, 0.0, 80.0)
STRAP_WIDTH, STRAP_LENGTH, STRAP_DEPTH, STRAP_R = 40.0, 400.0, 2.0, 8.0
BALLAST_XY = [(x, y) for x in (-210.0, -70.0, 70.0, 210.0) for y in (-85.0, 85.0)]
BALLAST_L, BALLAST_W, BALLAST_H = 100.0, 50.0, 40.0
LOCATOR_WALL, LOCATOR_HEIGHT = 2.0, 2.0
HANDLE_W, HANDLE_H, HANDLE_DEPTH, HANDLE_R, HANDLE_Z = 160.0, 50.0, 4.0, 8.0, 120.0
REAR_PAD_W, REAR_PAD_H, REAR_PAD_DEPTH, REAR_PAD_Z = 80.0, 50.0, 3.0, 55.0


def box(l, w, h, x=0, y=0, z=0):
    return cq.Workplane("XY").box(l, w, h, centered=(True, True, False)).translate((x, y, z))


def rounded_box(l, w, h, r, z):
    return box(l, w, h, z=z).edges().fillet(r)


def pad_xy(l, w, h, r, x, y, z):
    return box(l, w, h, x, y, z).edges("|Z").fillet(r)


def pad_yz(w, h, depth, r, x, z):
    return (cq.Workplane("YZ").box(w, h, depth, centered=(True, True, False))
            .edges("|X").fillet(r).translate((x, 0, z)))


def top_pocket(lid, l, w, depth, r, x, y):
    # Back the pressed recess inward before cutting; retain a 3 mm pocket floor.
    backing = pad_xy(l + 2 * WALL, w + 2 * WALL, depth + 0.2,
                     r + WALL, x, y, H - WALL - depth)
    cutter = pad_xy(l, w, depth + 1, r, x, y, H - depth)
    return lid.union(backing).cut(cutter)


def build():
    outer = rounded_box(L, W, H, RADIUS, 0)
    inner = rounded_box(L - 2 * WALL, W - 2 * WALL, H - 2 * WALL,
                        RADIUS - WALL, WALL)
    print("1/3 Bottom shell", flush=True)
    lower_outer = outer.intersect(box(L + 10, W + 10, SPLIT))
    # Flatten all four 60 x 60 undersides at Z=0, including the rounded edge.
    # Recut the original cavity to preserve the flat interior floor at Z=3.
    for x, y in WHEEL_XY:
        lower_outer = lower_outer.union(box(WHEEL_PAD, WHEEL_PAD, RADIUS, x, y))
    base = lower_outer.cut(inner)
    for x, y in WHEEL_XY:
        hole = cq.Workplane("XY").center(x, y).circle(WHEEL_HOLE_D / 2).extrude(25).translate((0, 0, -1))
        base = base.cut(hole)

    # Eight low locator frames: a clear 100 x 50 footprint and 40 mm above it.
    for x, y in BALLAST_XY:
        frame = box(BALLAST_L + 2 * LOCATOR_WALL, BALLAST_W + 2 * LOCATOR_WALL,
                    LOCATOR_HEIGHT, x, y, WALL).cut(
                        box(BALLAST_L, BALLAST_W, LOCATOR_HEIGHT + 2, x, y, WALL - 1))
        base = base.union(frame)

    for y in SENSOR_Y:
        hole = (cq.Workplane("YZ").center(y, SENSOR_Z).circle(SENSOR_D / 2)
                .extrude(12).translate((L / 2 - 8, 0, 0)))
        base = base.cut(hole)

    # Rear (-X) stowed-handle recess, 160 x 50 x 4. No handle body.
    base = base.union(pad_yz(HANDLE_W + 2 * WALL, HANDLE_H + 2 * WALL,
                             HANDLE_DEPTH + 0.2, HANDLE_R + WALL,
                             -L / 2 + WALL - 0.2, HANDLE_Z))
    base = base.cut(pad_yz(HANDLE_W, HANDLE_H, HANDLE_DEPTH + 1, HANDLE_R,
                           -L / 2 - 1, HANDLE_Z))
    # Rear inner-wall mounting face: 80 along Y, 50 along Z, face at X=-354.
    base = base.union(box(REAR_PAD_DEPTH + 0.2, REAR_PAD_W, REAR_PAD_H,
                         -L / 2 + WALL + (REAR_PAD_DEPTH - 0.2) / 2, 0,
                         REAR_PAD_Z - REAR_PAD_H / 2)).clean()

    print("2/3 Lid", flush=True)
    lid = outer.cut(inner).intersect(box(L + 10, W + 10, H - SPLIT, z=SPLIT))
    for x in STRAP_X:
        lid = top_pocket(lid, STRAP_WIDTH, STRAP_LENGTH, STRAP_DEPTH, STRAP_R, x, 0)
    # Shallow moulded flutes stay outside the strap channels and the envelope.
    for x in (-217.5, 217.5):
        for y in (-150, -90, 90, 150):
            lid = top_pocket(lid, 175, 10, 1, 4, x, y)
    lid = lid.clean()

    print("3/3 Closed assembly", flush=True)
    assembly = cq.Assembly(name="case26_ABS")
    assembly.add(base, name="case26_base", color=cq.Color(0.22, 0.24, 0.26))
    assembly.add(lid, name="case26_lid", color=cq.Color(0.27, 0.29, 0.31))
    return base, lid, assembly


def bounds(shape):
    b = shape.BoundingBox()
    return [b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax]


def check_close(actual, expected, label, tol=1e-5):
    if any(abs(a - e) > tol for a, e in zip(actual, expected)):
        raise ValueError(f"{label}: {actual} != {expected}")


def validate(base, lid):
    b, t = base.val(), lid.val()
    for name, shape in (("base", b), ("lid", t)):
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError(f"{name}: expected one valid solid")
    check_close(bounds(b), [-360, -235, 0, 360, 235, 170], "base bounds")
    check_close(bounds(t), [-360, -235, 170, 360, 235, 290], "lid bounds")
    if base.intersect(lid).val().Volume() > 1e-5:
        raise ValueError("Shells overlap")

    for x, y in BALLAST_XY:
        clearance = box(BALLAST_L, BALLAST_W, BALLAST_H, x, y, WALL)
        if base.intersect(clearance).val().Volume() > 1e-5:
            raise ValueError(f"Ballast space blocked at {x}, {y}")
        if not b.isInside((x, y, 1.5)) or b.isInside((x, y, 3.01)):
            raise ValueError("Interior floor must be flat at Z=3")

    for x, y in WHEEL_XY:
        if b.isInside((x, y, 1.5)) or not b.isInside((x + 4, y, 1.5)):
            raise ValueError("M6 clearance hole missing")
        for dx in (-29, 29):
            for dy in (-29, 29):
                if not b.isInside((x + dx, y + dy, 0.1)):
                    raise ValueError("Wheel platform not flat at Z=0")

    for y in SENSOR_Y:
        if b.isInside((359, y, 40)) or not b.isInside((359, y + 10, 40)):
            raise ValueError("Front sensor hole missing")
    for x in STRAP_X:
        if t.isInside((x, 0, 289)) or not t.isInside((x, 0, 286)):
            raise ValueError("Top channel or backing missing")
        if t.isInside((x, 0, 284.9)) or not t.isInside((x, 0, 285.1)):
            raise ValueError("Channel floor must retain 3 mm")

    if b.isInside((-358, 0, 120)) or not b.isInside((-354, 0, 120)):
        raise ValueError("Rear recess missing")
    if not b.isInside((-355, 0, 55)):
        raise ValueError("Rear electronics mounting face missing")

    return {
        "units": "mm", "material": "ABS", "color": "dark grey",
        "envelope": [L, W, H], "split_z": SPLIT, "wall": WALL,
        "base_bounds": bounds(b), "lid_bounds": bounds(t),
        "base_volume_mm3": b.Volume(), "lid_volume_mm3": t.Volume(),
        "wheel_xy": WHEEL_XY, "wheel_hole_d": WHEEL_HOLE_D,
        "strap_x": STRAP_X, "ballast_clearance_count": len(BALLAST_XY),
        "valid_single_solids": True, "interference_volume_mm3": 0,
    }


def export_all(out):
    out.mkdir(parents=True, exist_ok=True)
    base, lid, assembly = build()
    report = validate(base, lid)
    for name, part in (("case26_base", base), ("case26_lid", lid)):
        cq.exporters.export(part, str(out / f"{name}.step"))
        cq.exporters.export(part, str(out / f"{name}.stl"), tolerance=0.08, angularTolerance=0.1)
    assembly.export(str(out / "case26.step"))
    # Lid exterior down; assembly-coordinate sources above remain unchanged.
    print_lid = lid.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, H))
    cq.exporters.export(print_lid, str(out / "case26_lid_print.stl"), tolerance=0.08, angularTolerance=0.1)

    import trimesh
    mesh_report = {}
    meshes = {}
    for name in ("case26_base", "case26_lid", "case26_lid_print"):
        mesh = trimesh.load_mesh(out / f"{name}.stl")
        before = len(mesh.faces)
        # OCCT's spherical poles can tessellate to zero-area triangles in STL.
        # Drop only degenerate faces; do not fill holes or change the surface.
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        if not mesh.is_watertight or not mesh.is_winding_consistent or len(mesh.split()) != 1:
            raise ValueError(f"{name}: STL must be one watertight, consistently oriented mesh")
        mesh.export(out / f"{name}.stl")
        meshes[name] = mesh
        mesh_report[name] = {"watertight": True, "triangles": len(mesh.faces),
                             "degenerate_triangles_removed": before - len(mesh.faces)}
    # Two individually closed shells touch at the parting plane. This combined
    # mesh is for inspection; the separate STLs are the slicing deliverables.
    trimesh.util.concatenate([meshes["case26_base"], meshes["case26_lid"]]).export(out / "case26.stl")
    # Validate the files actually delivered, including a STEP round trip.
    imported = cq.importers.importStep(str(out / "case26.step")).val()
    if not imported.isValid() or len(imported.Solids()) != 2:
        raise ValueError("STEP assembly must contain two valid shell solids")
    check_close(bounds(imported), [-360, -235, 0, 360, 235, 290], "STEP envelope")
    report["stl_checks"] = mesh_report
    report["step_round_trip"] = "valid, 2 solids, envelope verified"
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    export_all(parser.parse_args().out)
