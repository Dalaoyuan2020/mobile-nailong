"""Upright suitcase, trolley handle and photo-proportioned Nailong cutout; mm."""

from pathlib import Path
import argparse
import hashlib
import json
import sys

import cadquery as cq
import trimesh

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "handle"))
from handle import build_handle, seat_cutters, validate as validate_handle
from case_pose import load_upright_case, build_wheels
from nailong_profile import build_board, profile_metrics, export_artwork, export_preview

HEIGHT, THICKNESS = 1600.0, 8.0
BOARD_BACK_X, BOARD_BOTTOM_Z = 145.0, 20.0
MOUNT_HEIGHTS = (920.0, 1080.0)


def shape(value):
    return value.val() if isinstance(value, cq.Workplane) else value


def box(l, w, h, x, y, z):
    return cq.Workplane("XY").box(l, w, h, centered=(True, True, False)).translate((x, y, z))


def build_standee(height=HEIGHT):
    if not 1600 <= height <= 1800:
        raise ValueError("Board height must be between 1600 and 1800 mm")
    return build_board(height=height, bottom_z=BOARD_BOTTOM_Z, back_x=BOARD_BACK_X)


def mount_bar(center_z):
    """Concept back spreader with tube channels; clamp/bolt detail is deferred."""
    bar = box(16, 250, 30, 137, 0, center_z - 15)
    for y in (-90, 90):
        channel = (cq.Workplane("XY").center(139, y).circle(6.2)
                   .extrude(32).translate((0, 0, center_z - 16)))
        bar = bar.cut(channel)
    return bar.clean()


def build_assembly(height=HEIGHT):
    case = load_upright_case()
    handles = build_handle()
    validate_handle(handles)
    # Only cut two embedded guide pockets in the posed copy, never the case source.
    for name, part in case.items():
        mounted = shape(part)
        for cutter in seat_cutters().values():
            mounted = mounted.cut(shape(cutter))
        case[name] = mounted.clean()
    components = []

    def add(parts, category, color):
        for name, part in parts.items():
            components.append({"name": name, "shape": shape(part),
                               "category": category, "color": color})

    add(case, "case", [0.23, 0.25, 0.27])
    for name, part in build_wheels().items():
        add({name: part}, "wheel", [0.085, 0.095, 0.105] if "wheel" in name else [0.30, 0.32, 0.34])
    for name, part in handles.items():
        add({name: part}, "handle", [0.66, 0.69, 0.72] if "frame" in name else [0.16, 0.18, 0.20])
    add({"standee": build_standee(height)}, "board", [243/255, 203/255, 104/255])
    add({"mount_lower": mount_bar(MOUNT_HEIGHTS[0]),
         "mount_upper": mount_bar(MOUNT_HEIGHTS[1])}, "mount", [0.36, 0.39, 0.42])
    return components


def bounds(part):
    b = shape(part).BoundingBox()
    return [round(v, 6) for v in (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax)]


def expect_bounds(part, expected, name):
    if any(abs(a - b) > 1e-5 for a, b in zip(bounds(part), expected)):
        raise ValueError(f"{name}: wrong bounds {bounds(part)}")


def verify(components, height=HEIGHT):
    by_name = {p["name"]: p["shape"] for p in components}
    for part in components:
        solid = part["shape"]
        if not solid.isValid() or len(solid.Solids()) != 1:
            raise ValueError(f"{part['name']}: expected one valid solid")
    case = cq.Compound.makeCompound([p["shape"] for p in components if p["category"] == "case"])
    expect_bounds(case, [-145, -235, 70, 145, 235, 790], "upright case")
    board = by_name["standee"]
    bb = bounds(board)
    expect_bounds(board, [145, bb[1], BOARD_BOTTOM_Z, 153, bb[4], BOARD_BOTTOM_Z + height], "board")
    if not 0.46 * height < bb[4] - bb[1] < 0.53 * height:
        raise ValueError("Cutout must retain the reference silhouette proportions")
    complete = cq.Compound.makeCompound([p["shape"] for p in components])
    expect_bounds(complete, [-145, bb[1], 0, 153, bb[4], BOARD_BOTTOM_Z + height], "assembly")
    expect_bounds(by_name["handle_frame"], [125, -96, 710, 145, 96, 1140], "stowed handle")

    # Check the complete assembly, rather than declaring separated items attached.
    max_overlap = 0.0
    for i, a in enumerate(components):
        for b in components[i + 1:]:
            volume = a["shape"].intersect(b["shape"]).Volume()
            max_overlap = max(max_overlap, volume)
            if volume > 1e-4:
                raise ValueError(f"Interference {a['name']} / {b['name']}: {volume:.6f} mm3")
    for name in ("handle_frame", "mount_lower", "mount_upper"):
        if board.distance(by_name[name]) > 1e-5:
            raise ValueError(f"{name} does not contact board")
    if board.distance(case) > 1e-5:
        raise ValueError("Board does not touch the upright case")
    for name in ("mount_lower", "mount_upper"):
        if by_name[name].distance(by_name["handle_frame"]) > .201:
            raise ValueError(f"{name} exceeds the concept tube clearance")
    return {"units": "mm", "case_pose": "upright", "case_bounds": bounds(case),
            "case_height": 720, "case_width": 470, "case_depth": 290,
            "board_bounds": bounds(board), "board_height": height, "board_back_x": BOARD_BACK_X,
            "board_contacts_case_and_handle": True, "handle_projection": 350,
            "tube_spacing": 180, "concept_mount_center_z": MOUNT_HEIGHTS,
            "mount_status": "layout only; clamp, fasteners and load rating not designed",
            "mount_channel_radial_clearance": .2,
            "profile": profile_metrics(height=height, bottom_z=BOARD_BOTTOM_Z, back_x=BOARD_BACK_X),
            "ground_to_board_top": BOARD_BOTTOM_Z + height, "ordinary_caster_centers_x": [-105, 105],
            "ordinary_caster_centers_y": [-200, 200],
            "max_pairwise_interference_mm3": max_overlap, "part_count": len(components)}


def export_all(height=HEIGHT):
    source_files = list((ROOT.parent / "case26").glob("case26*"))
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files if p.is_file()}
    print("Build upright case, handle, Nailong cutout and concept back mounts", flush=True)
    components = build_assembly(height)
    report = verify(components, height)
    out = ROOT / "parts"
    out.mkdir(exist_ok=True)
    assembly = cq.Assembly(name="upright_suitcase_standee")
    meshes, manifest, mesh_report = [], [], {}
    for part in components:
        name, solid = part["name"], part["shape"]
        assembly.add(solid, name=name, color=cq.Color(*part["color"]))
        path = out / f"{name}.stl"
        cq.exporters.export(solid, str(path), tolerance=0.08, angularTolerance=0.1)
        mesh = trimesh.load_mesh(path)
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        if not mesh.is_watertight or not mesh.is_winding_consistent or len(mesh.split()) != 1:
            raise ValueError(f"{name}: invalid exported STL")
        mesh.export(path)
        meshes.append(mesh)
        mesh_report[name] = {"watertight": True, "triangles": len(mesh.faces)}
        manifest.append({"name": name, "category": part["category"], "color": part["color"],
                         "path": path.relative_to(ROOT).as_posix(), "bounds": bounds(solid)})
    assembly.export(str(ROOT / "standee_assembly.step"))
    trimesh.util.concatenate(meshes).export(ROOT / "standee_assembly.stl")
    imported = cq.importers.importStep(str(ROOT / "standee_assembly.step")).val()
    if not imported.isValid() or len(imported.Solids()) != len(components):
        raise ValueError("Assembly STEP round trip lost a valid component")
    board = next(p["shape"] for p in components if p["name"] == "standee")
    board_assembly = cq.Assembly(name="yellow_KT_standee")
    board_assembly.add(board, name="standee", color=cq.Color(243/255, 203/255, 104/255))
    board_assembly.export(str(ROOT / "standee.step"))
    (ROOT / "standee.stl").write_bytes((out / "standee.stl").read_bytes())
    for name, before in source_hashes.items():
        if hashlib.sha256((ROOT.parent / "case26" / name).read_bytes()).hexdigest() != before:
            raise ValueError(f"Original case file changed: {name}")
    report.update({"case_source_files_unchanged": True,
                   "step_round_trip": f"valid, {len(components)} solids", "stl_checks": mesh_report})
    export_artwork(height)
    export_preview(height)
    (ROOT / "profile_metrics.json").write_text(json.dumps(report["profile"], indent=2) + "\n", encoding="utf-8")
    (ROOT / "assembly_manifest.json").write_text(json.dumps({"parts": manifest}, indent=2) + "\n", encoding="utf-8")
    (ROOT / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "stl_checks"}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--height", type=float, default=HEIGHT, help="KT board height, 1600 to 1800 mm")
    export_all(parser.parse_args().height)
