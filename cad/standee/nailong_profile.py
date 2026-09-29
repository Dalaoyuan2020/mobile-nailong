"""Photo-informed Nailong cutout, not a dimensional reverse-engineering model.

The silhouette is hand traced from the user's 1.6 m standee photograph.  Drawing
coordinates below belong to the manual vector tracing, not an embedded photo.
The structural part is one 8 mm sheet; artwork is optional zero-thickness faces.
"""
from pathlib import Path
import json
import math

import cadquery as cq

HERE = Path(__file__).resolve().parent
THICKNESS = 8.0
SOURCE = "Manual approximate trace of user-supplied Nailong standee photograph; not manufacturing reverse engineering"

# Each C has two control points and an endpoint.  The notch between the feet is
# part of this outer boundary, not a hidden hole or a second upright board.
OUTLINE = [
    ("M", 352, 345),
    ("C", 305, 342, 261, 365, 236, 411),
    ("C", 224, 427, 225, 456, 238, 472),
    ("C", 235, 482, 232, 492, 240, 501),
    ("C", 248, 516, 266, 527, 275, 548),
    ("C", 289, 575, 292, 601, 283, 632),
    ("C", 271, 676, 247, 721, 224, 767),
    ("C", 197, 788, 180, 815, 176, 846),
    ("C", 172, 874, 181, 903, 202, 927),
    ("C", 213, 946, 218, 978, 229, 1006),
    ("C", 247, 1034, 272, 1063, 304, 1079),
    ("C", 308, 1121, 324, 1169, 352, 1205),
    ("C", 368, 1228, 386, 1249, 404, 1267),
    ("C", 377, 1274, 337, 1280, 307, 1288),
    ("C", 289, 1290, 281, 1298, 285, 1319),
    ("C", 288, 1332, 305, 1334, 327, 1334),
    ("C", 374, 1335, 421, 1334, 458, 1330),
    ("C", 475, 1330, 482, 1324, 477, 1311),
    ("C", 475, 1301, 463, 1296, 455, 1291),
    ("C", 442, 1282, 442, 1266, 444, 1246),
    ("C", 445, 1205, 445, 1161, 454, 1122),
    ("C", 458, 1117, 464, 1120, 468, 1133),
    ("C", 487, 1185, 513, 1234, 545, 1277),
    ("C", 554, 1290, 565, 1304, 565, 1315),
    ("C", 556, 1325, 528, 1333, 505, 1343),
    ("C", 484, 1351, 472, 1363, 477, 1377),
    ("C", 482, 1391, 515, 1398, 542, 1394),
    ("C", 578, 1397, 609, 1388, 631, 1377),
    ("C", 645, 1370, 646, 1358, 639, 1346),
    ("C", 632, 1330, 611, 1324, 608, 1310),
    ("C", 604, 1296, 615, 1256, 618, 1221),
    ("C", 625, 1170, 622, 1127, 625, 1095),
    ("C", 675, 1056, 695, 998, 695, 933),
    ("C", 697, 877, 682, 829, 661, 781),
    ("C", 637, 720, 615, 665, 585, 616),
    ("C", 552, 559, 525, 510, 496, 462),
    ("C", 477, 424, 455, 385, 414, 361),
    ("C", 397, 350, 376, 345, 352, 345),
]


def sample_path(commands, steps=16):
    """Sample cubic vectors identically for CAD, SVG and raster preview."""
    result = []
    current = None
    for command in commands:
        if command[0] == "M":
            current = tuple(command[1:3])
            result.append(current)
        elif command[0] == "L":
            current = tuple(command[1:3])
            result.append(current)
        elif command[0] == "C":
            p0 = current
            p1, p2, p3 = command[1:3], command[3:5], command[5:7]
            for i in range(1, steps + 1):
                t, s = i / steps, 1 - i / steps
                result.append(tuple(s**3 * p0[k] + 3*s*s*t*p1[k] + 3*s*t*t*p2[k] + t**3*p3[k] for k in (0, 1)))
            current = tuple(p3)
        else:
            raise ValueError(command)
    if len(result) > 1 and math.dist(result[0], result[-1]) < 1e-9:
        result.pop()
    return result


RAW = sample_path(OUTLINE)
RAW_MIN_X, RAW_MAX_X = min(x for x, z in RAW), max(x for x, z in RAW)
RAW_MIN_Z, RAW_MAX_Z = min(z for x, z in RAW), max(z for x, z in RAW)
RAW_MID_X = (RAW_MIN_X + RAW_MAX_X) / 2


def check_height(height):
    if not 1600 <= height <= 1800:
        raise ValueError("Standee sheet height must be 1600 to 1800 mm")


def profile_points(height=1600, bottom_z=20):
    """World (Y,Z) boundary; +Y is screen-right when looking from +X."""
    check_height(height)
    factor = height / (RAW_MAX_Z - RAW_MIN_Z)
    return [((u - RAW_MID_X) * factor, bottom_z + (RAW_MAX_Z - v) * factor) for u, v in RAW]


def build_board(height=1600, bottom_z=20, back_x=145):
    """One valid solid; sheet occupies X=[back_x,back_x+8], front is +X."""
    points = profile_points(height, bottom_z)
    board = cq.Workplane("YZ", origin=(back_x, 0, 0)).polyline(points).close().extrude(THICKNESS).val()
    if not board.isValid() or len(board.Solids()) != 1:
        raise ValueError("Invalid cutout sheet")
    return board


def profile_metrics(height=1600, bottom_z=20, back_x=145):
    """Metrics use the exact sampled CAD boundary, in mm / mm2 / mm3.

    Centroid is for a uniform sheet and excludes artwork and mounting hardware.
    foot_gap is a horizontal opening between the two feet at sheet Z=100 mm.
    """
    points = profile_points(height, bottom_z)
    pairs = list(zip(points, points[1:] + points[:1]))
    signed2 = sum(a[0]*b[1] - b[0]*a[1] for a, b in pairs)
    centroid = [sum((a[i]+b[i])*(a[0]*b[1]-b[0]*a[1]) for a, b in pairs) / (3*signed2) for i in (0, 1)]
    sample_z = bottom_z + height * 100 / 1600
    crossings = []
    for a, b in pairs:
        if min(a[1], b[1]) <= sample_z < max(a[1], b[1]):
            crossings.append(a[0] + (sample_z-a[1]) * (b[0]-a[0]) / (b[1]-a[1]))
    crossings.sort()
    foot_gap = crossings[2]-crossings[1] if len(crossings) == 4 else None
    return {"units": "mm", "height": height, "width": max(y for y,z in points)-min(y for y,z in points),
            "thickness": THICKNESS, "area_mm2": abs(signed2)/2,
            "volume_mm3": abs(signed2)/2*THICKNESS, "centroid_yz_mm": centroid,
            "centroid_xyz_mm": [back_x+THICKNESS/2, *centroid], "bottom_z": bottom_z,
            "top_z": bottom_z+height, "foot_gap_mm": foot_gap, "foot_gap_sample_z": sample_z,
            "bounds": [back_x, min(y for y,z in points), bottom_z,
                       back_x+THICKNESS, max(y for y,z in points), bottom_z+height],
            "source": SOURCE, "outline_vertex_count": len(points)}


def ellipse(cx, cy, rx, ry, count=80):
    return [(cx+rx*math.cos(2*math.pi*i/count), cy+ry*math.sin(2*math.pi*i/count)) for i in range(count)]


ARTWORK = [
    ("belly", (255, 226, 136), sample_path([
        ("M", 285, 680), ("C", 244, 733, 205, 825, 207, 920),
        ("C", 214, 1020, 343, 1117, 457, 1119), ("C", 540, 1127, 598, 1067, 590, 988),
        ("C", 585, 913, 540, 851, 480, 807), ("C", 415, 760, 350, 681, 313, 679),
        ("C", 301, 676, 291, 676, 285, 680)])),
    ("far_eye_white", (252, 246, 209), sample_path([
        ("M", 236, 423), ("C", 224, 433, 226, 458, 238, 472),
        ("C", 248, 460, 249, 434, 241, 424), ("C", 239, 422, 237, 422, 236, 423)])),
    ("far_eye_pupil", (42, 47, 37), sample_path([
        ("M", 239, 433), ("C", 230, 438, 231, 458, 238, 466),
        ("C", 244, 457, 244, 439, 239, 433)])),
    ("eye_outer", (160, 194, 111), ellipse(318, 425, 33, 33)),
    ("eye_inner", (107, 163, 95), ellipse(319, 425, 29, 30)),
    ("eye_pupil", (30, 42, 32), ellipse(327, 429, 17, 18)),
    ("eye_glint", (241, 244, 195), ellipse(312, 410, 5, 5)),
    ("mouth", (66, 66, 37), sample_path([
        ("M", 240, 494), ("C", 252, 494, 280, 489, 298, 490),
        ("C", 290, 494, 257, 498, 241, 499), ("C", 238, 498, 238, 496, 240, 494)])),
    ("far_hand", (200, 163, 66), sample_path([
        ("M", 214, 832), ("C", 200, 827, 188, 834, 190, 846),
        ("C", 193, 856, 204, 861, 214, 866), ("C", 198, 866, 186, 872, 191, 883),
        ("C", 197, 890, 207, 893, 217, 897), ("C", 202, 897, 189, 901, 196, 912),
        ("C", 202, 919, 212, 920, 221, 924), ("C", 209, 924, 199, 928, 205, 935),
        ("C", 211, 941, 222, 942, 225, 932), ("C", 229, 912, 220, 888, 218, 873),
        ("C", 215, 857, 207, 845, 216, 838), ("C", 220, 834, 219, 833, 214, 832)])),
    ("near_arm", (237, 194, 86), sample_path([
        ("M", 445, 690), ("C", 452, 726, 452, 766, 431, 790),
        ("C", 402, 817, 345, 833, 306, 841), ("C", 292, 829, 275, 829, 275, 842),
        ("C", 275, 852, 289, 858, 305, 863), ("C", 289, 866, 265, 873, 255, 879),
        ("C", 242, 887, 251, 899, 265, 900), ("C", 278, 901, 292, 897, 306, 894),
        ("C", 288, 907, 258, 913, 255, 922), ("C", 256, 934, 273, 937, 286, 932),
        ("C", 300, 927, 314, 919, 322, 917), ("C", 305, 931, 270, 937, 273, 948),
        ("C", 276, 960, 291, 960, 307, 954), ("C", 343, 944, 365, 930, 391, 924),
        ("C", 444, 916, 494, 902, 535, 880), ("C", 568, 850, 586, 802, 586, 754),
        ("C", 582, 714, 562, 681, 543, 663), ("C", 511, 647, 462, 656, 445, 690)])),
    ("arm_fold", (192, 155, 67), sample_path([
        ("M", 442, 690), ("C", 442, 718, 446, 752, 456, 767),
        ("L", 449, 770), ("C", 440, 748, 438, 713, 442, 690)])),
    ("finger_fold_one", (190, 151, 60), sample_path([
        ("M", 306, 861), ("C", 317, 864, 327, 866, 336, 866),
        ("C", 326, 870, 314, 869, 306, 865), ("L", 306, 861)])),
    ("finger_fold_two", (190, 151, 60), sample_path([
        ("M", 306, 894), ("C", 316, 891, 328, 890, 338, 890),
        ("C", 327, 894, 317, 896, 306, 898), ("L", 306, 894)])),
]


def artwork_shapes(height=1600, bottom_z=20, front_x=153.04):
    """List of name, color (0..1 RGB), zero-thickness cq.Face for preview only.

    Faces have tiny 0.01 mm display offsets to prevent z-fighting.  These are
    printing/visualization layers, excluded from structural STEP and BOM volume.
    """
    check_height(height)
    factor = height / (RAW_MAX_Z - RAW_MIN_Z)
    result = []
    for index, (name, rgb, points) in enumerate(ARTWORK):
        display_x = front_x + index*.01
        coords = [cq.Vector(display_x, (u-RAW_MID_X)*factor,
                            bottom_z+(RAW_MAX_Z-v)*factor) for u,v in points]
        wire = cq.Wire.makePolygon(coords, close=True)
        face = cq.Face.makeFromWires(wire)
        # These two colors run all the way to the cut edge; clip them just as
        # the SVG clipPath does, so the drawing never changes the silhouette.
        if name in {"far_eye_white", "far_hand"}:
            cutline = cq.Face.makeFromWires(cq.Wire.makePolygon(
                [cq.Vector(display_x, y, z) for y,z in profile_points(height, bottom_z)], close=True))
            clipped = face.intersect(cutline)
            face = clipped.Faces()[0] if len(clipped.Faces()) == 1 else clipped
        if not face.isValid():
            raise ValueError(f"Invalid print face: {name}")
        result.append({"name": name, "shape": face, "color": [c/255 for c in rgb],
                       "category": "artwork"})
    return result


def export_artwork(height=1600, path=None):
    """Standalone SVG at real sheet size, with the same cut line as CAD."""
    check_height(height)
    target = Path(path) if path else HERE / "front_artwork.svg"
    metrics = profile_metrics(height)
    width, rh = RAW_MAX_X-RAW_MIN_X, RAW_MAX_Z-RAW_MIN_Z
    def polygon(points, color, **attrs):
        coords = " ".join(f"{u:.3f},{v:.3f}" for u,v in points)
        options = " ".join(f'{k.replace("_", "-")}="{v}"' for k,v in attrs.items())
        return f'<polygon points="{coords}" fill="{color}" {options}/>'
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{metrics["width"]:.4f}mm" height="{height}mm" viewBox="{RAW_MIN_X} {RAW_MIN_Z} {width} {rh}">',
             f'<title>Nailong cutout — {height} mm</title>', f'<desc>{SOURCE}. Not final print artwork.</desc>',
             '<defs><clipPath id="cutline">', polygon(RAW, "white"), '</clipPath></defs>',
             '<g clip-path="url(#cutline)">', polygon(RAW, "#f3cb68")]
    for name, rgb, points in ARTWORK:
        lines.append(polygon(points, "#"+"".join(f"{c:02x}" for c in rgb), id=name))
    lines.extend(['</g>', '</svg>'])
    target.write_text("\n".join(lines)+"\n", encoding="utf-8")
    return target


def export_preview(height=1600, path=None):
    """Front view from the same sampled outline and print vectors; no photo edit."""
    from PIL import Image, ImageDraw, ImageFont
    target = Path(path) if path else HERE / "profile_preview.png"
    canvas = Image.new("RGB", (1380, 2000), "#f8fafb")
    draw = ImageDraw.Draw(canvas)
    def font(size):
        for file in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
            if Path(file).is_file():
                return ImageFont.truetype(file, size)
        return ImageFont.load_default()
    metrics = profile_metrics(height)
    draw.text((70, 40), "NAILONG / SHAPED STANDEE", font=font(44), fill="#202a31")
    draw.text((70, 106), f'{height:.0f} x {metrics["width"]:.0f} x 8 mm | 20 mm foot clearance', font=font(28), fill="#526069")
    scale = 1620 / (RAW_MAX_Z-RAW_MIN_Z)
    def xy(points):
        return [(690+(u-RAW_MID_X)*scale, 218+(v-RAW_MIN_Z)*scale) for u,v in points]
    draw.polygon(xy(RAW), fill="#f3cb68")
    for name,rgb,points in ARTWORK:
        draw.polygon(xy(points), fill=rgb)
    draw.line(xy(RAW+[RAW[0]]), fill="#7c6837", width=2)
    draw.line((100, 1859, 1280, 1859), fill="#9eabb4", width=2)
    draw.text((70, 1890), "Manual photo approximation; one flat sheet, two separate feet.", font=font(27), fill="#38464f")
    draw.text((70, 1931), "Illustrative print layers are excluded from the structural STEP model.", font=font(24), fill="#64717b")
    canvas.save(target)
    return target


if __name__ == "__main__":
    board = build_board()
    artwork_shapes()
    export_artwork()
    export_preview()
    metrics = profile_metrics()
    (HERE / "profile_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
