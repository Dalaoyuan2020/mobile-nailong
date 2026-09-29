"""Rigid upright case pose and four ordinary caster placeholders; units mm."""

from pathlib import Path
import hashlib
import json

import cadquery as cq

CASE_DIR = Path(__file__).resolve().parents[1] / "case26"
CASE_BOTTOM, CASE_TOP = 70.0, 790.0
WHEEL_X, WHEEL_Y, WHEEL_Z = 105.0, 200.0, 25.0
WHEEL_DIAMETER, WHEEL_WIDTH = 50.0, 20.0
AXLE_RADIUS, BORE_RADIUS = 3.0, 3.2
SOURCE_HASHES = {
    "case26_base.step": "68eef816fe622465add3dc82328ac9394234abf953fa2344c19c482c9f9b70fd",
    "case26_lid.step": "ffbce79ccd8657f6c28dd524abcf64589bc1ad8da691c04ed084ee07a46f1f03",
    "case26.py": "d850fb9f8772cf5dddc47dc91d4ae8df0ca85e5131beab11c3302284b5f8d8f8",
}


def load_upright_case():
    """Reuse the original shells, rotating their 720 mm dimension into height."""
    return {
        name: cq.importers.importStep(str(CASE_DIR / filename)).val()
        .rotate((0, 0, 0), (0, 1, 0), -90).translate((145, 0, 430))
        for name, filename in (("case_base", "case26_base.step"),
                               ("case_lid", "case26_lid.step"))
    }


def _box(dx, dy, dz, x, y, z):
    return cq.Workplane("XY").box(dx, dy, dz, centered=(True, True, False)).translate((x, y, z)).val()


def _cylinder_y(radius, length, x, y, z):
    return cq.Solid.makeCylinder(radius, length, cq.Vector(x, y, z), cq.Vector(0, 1, 0))


def build_wheels():
    """Four black wheels plus connected dark fork/axle/post parts, topping at Z=70."""
    parts = {}
    for end, x in (("rear", -WHEEL_X), ("front", WHEEL_X)):
        for side, y in (("left", -WHEEL_Y), ("right", WHEEL_Y)):
            name = f"{end}_{side}"
            blank = _cylinder_y(WHEEL_DIAMETER / 2, WHEEL_WIDTH,
                                x, y - WHEEL_WIDTH / 2, WHEEL_Z)
            wheel = cq.Workplane(obj=blank).edges("%Circle").fillet(1.5).val()
            # Shallow circular recesses distinguish the hub and rubber rim.
            for recess_y in (y - 10.1, y + 8.8):
                ring = _cylinder_y(20, 1.3, x, recess_y, WHEEL_Z).cut(
                    _cylinder_y(8, 1.3, x, recess_y, WHEEL_Z))
                wheel = wheel.cut(ring)
            wheel = wheel.cut(_cylinder_y(BORE_RADIUS, 22, x, y - 11, WHEEL_Z)).clean()

            # Two cheek plates clear the wheel; a through axle joins both plates.
            fork = _box(14, 32, 7, x, y, 57)
            for cheek_y in (y - 14, y + 14):
                fork = fork.fuse(_box(14, 4, 35, x, cheek_y, 25))
            fork = fork.fuse(_cylinder_y(AXLE_RADIUS, 32, x, y - 16, WHEEL_Z))
            post = cq.Solid.makeCylinder(6, 7, cq.Vector(x, y, 63), cq.Vector(0, 0, 1))
            fork = fork.fuse(post).clean()
            parts[f"wheel_{name}"] = wheel
            parts[f"fork_{name}"] = fork
    return parts


def _bounds(shape):
    b = shape.BoundingBox()
    return [b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax]


def validate():
    case, wheels = load_upright_case(), build_wheels()
    for name, shape in {**case, **wheels}.items():
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError(f"{name}: expected one valid solid")
    compound = cq.Compound.makeCompound(list(case.values()))
    if any(abs(a - b) > 1e-5 for a, b in zip(_bounds(compound), [-145, -235, 70, 145, 235, 790])):
        raise ValueError(f"Incorrect upright case envelope: {_bounds(compound)}")
    overlap, support_gaps = {}, {}
    for name, wheel in wheels.items():
        if not name.startswith("wheel_"):
            continue
        fork = wheels[name.replace("wheel_", "fork_")]
        volume = wheel.intersect(fork).Volume()
        if volume > 1e-5:
            raise ValueError(f"{name}: fork interferes with wheel by {volume} mm3")
        overlap[name] = volume
        b = wheel.BoundingBox()
        if max(abs(b.xlen - 50), abs(b.ylen - 20), abs(b.zlen - 50), abs(b.zmin)) > 1e-5:
            raise ValueError(f"{name}: incorrect wheel envelope {_bounds(wheel)}")
        if abs(fork.BoundingBox().zmax - CASE_BOTTOM) > 1e-5:
            raise ValueError(f"{name}: fork does not reach case bottom")
        gap = fork.distance(compound)
        if gap > 1e-5:
            raise ValueError(f"{name}: caster support floats {gap} mm below the case")
        support_gaps[name.replace("wheel_", "fork_")] = gap
    for name, part in wheels.items():
        if part.intersect(compound).Volume() > 1e-5:
            raise ValueError(f"{name}: positive-volume interference with case")
    unchanged = {
        filename: hashlib.sha256((CASE_DIR / filename).read_bytes()).hexdigest() == digest
        for filename, digest in SOURCE_HASHES.items()
    }
    return {"units": "mm", "case_bounds": _bounds(compound),
            "wheel_centers": [[x, y, WHEEL_Z] for x in (-WHEEL_X, WHEEL_X)
                              for y in (-WHEEL_Y, WHEEL_Y)],
            "wheel_diameter": WHEEL_DIAMETER, "wheel_width": WHEEL_WIDTH,
            "ground_z": 0, "fork_top_z": CASE_BOTTOM,
            "track": 2 * WHEEL_Y, "upright_caster_x_spacing": 2 * WHEEL_X,
            "wheel_fork_overlap_mm3": overlap, "case_wheel_overlap_mm3": 0,
            "fork_case_contact_gap_mm": support_gaps,
            "valid_solids": len(case) + len(wheels), "original_case_files_unchanged": unchanged}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
