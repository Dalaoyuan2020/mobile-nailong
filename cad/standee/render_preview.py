"""Render only exported assembly STL parts; no pose or geometry changes."""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from nailong_profile import artwork_shapes

from PIL import Image, ImageDraw


HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("case_preview", HERE.parent / "case26" / "render_preview.py")
_case_preview = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_case_preview)
read_stl = _case_preview.read_stl
render = _case_preview.render
font = _case_preview.font
BG = _case_preview.BG
INK = _case_preview.INK
MUTED = _case_preview.MUTED
ACCENT = (176, 124, 14)


def category(part):
    """Prefer the manifest category; support descriptive part names as fallback."""
    cat = str(part.get("category", part.get("kind", ""))).lower()
    name = str(part.get("name", part.get("path", ""))).lower()
    if cat in {"case", "handle", "wheel", "board", "mount", "artwork"}:
        return cat
    text = f"{cat} {name}"
    for result, tokens in (
        ("strap", ("strap", "belt")),
        ("board", ("board", "panel", "standee", "kt")),
        ("wheel", ("wheel", "caster", "castor")),
        ("handle", ("handle", "tube", "grip", "socket", "rod")),
        ("case", ("case", "shell", "lid", "base")),
    ):
        if any(token in text for token in tokens):
            return result
    raise ValueError(f"Unrecognised part category: {part!r}")


def load_parts(directory):
    data = json.loads((directory / "assembly_manifest.json").read_text(encoding="utf-8-sig"))
    parts = []
    for raw in data["parts"]:
        path = (directory / raw["path"]).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        mesh = read_stl(path)
        if not mesh.GetNumberOfPoints():
            raise ValueError(f"Empty STL: {path}")
        color = raw.get("color", [.45, .48, .50])
        if max(color) > 1:
            color = [float(c) / 255 for c in color]
        parts.append({**raw, "mesh": mesh, "color": tuple(color), "category": category(raw)})
    return parts


def bounds(parts):
    found = [part["mesh"].GetBounds() for part in parts]
    if not found:
        raise ValueError("Missing required assembly category")
    return tuple((min if i % 2 == 0 else max)(b[i] for b in found) for i in range(6))


def draw_title(canvas, title, subtitle):
    draw = ImageDraw.Draw(canvas)
    draw.text((75, 48), title, font=font(61, True), fill=INK)
    draw.text((79, 130), subtitle, font=font(29), fill=MUTED)
    return draw


def scene(parts, size, direction, focus, scale):
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(*(v/255 for v in BG))
    for part in parts:
        if part["category"] != "artwork":
            _case_preview.add_shell(renderer, part["mesh"], part["color"])
        else:
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(part["mesh"])
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(*part["color"])
            actor.GetProperty().LightingOff()
            renderer.AddActor(actor)
    camera = renderer.GetActiveCamera()
    camera.SetFocalPoint(*focus)
    camera.SetPosition(*(focus[i]+direction[i] for i in range(3)))
    camera.SetViewUp(0, 0, 1)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(scale)
    renderer.UseFXAAOn()
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetMultiSamples(0)
    window.SetSize(*size)
    window.AddRenderer(renderer)
    renderer.ResetCameraClippingRange()
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.SetInputBufferTypeToRGB()
    capture.ReadFrontBufferOff()
    capture.Update()
    pixels = vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars())
    result = Image.fromarray(pixels.reshape(size[1], size[0], 3)[::-1].copy())
    window.Finalize()
    return result


def print_layers(parts):
    board = bounds([p for p in parts if p["category"] == "board"])
    layers = []
    for part in artwork_shapes(height=board[5]-board[4], bottom_z=board[4], front_x=board[1]+.04):
        vertices, triangles = part["shape"].tessellate(.1)
        points, cells = vtk.vtkPoints(), vtk.vtkCellArray()
        for point in vertices:
            points.InsertNextPoint(*point.toTuple())
        for triangle in triangles:
            cells.InsertNextCell(3, triangle)
        mesh = vtk.vtkPolyData()
        mesh.SetPoints(points)
        mesh.SetPolys(cells)
        layers.append({**part, "mesh": mesh})
    return layers


def preview(directory, parts):
    canvas = Image.new("RGB", (2400, 1860), "white")
    draw = draw_title(canvas, "NAILONG / UPRIGHT SUITCASE",
                      "Photo-proportioned cutout  /  Feet near the wheels  /  Back mounting concept")
    size = (1090, 1410)
    board = bounds([p for p in parts if p["category"] == "board"])
    focus = (0, 0, board[5]/2)
    scale = board[5]*.57
    canvas.paste(scene(parts+print_layers(parts), size, (3000, 0, 0), focus, scale), (75, 223))
    canvas.paste(scene(parts, size, (-2100, 1900, 450), focus, scale), (1235, 223))
    draw.text((103, 248), "01 / FRONT CUTOUT", font=font(31, True), fill=INK)
    draw.text((1263, 248), "02 / REAR ASSEMBLY", font=font(31, True), fill=INK)
    draw.text((105, 1581), "Flat 8 mm panel + illustrative print artwork", font=font(28), fill=MUTED)
    draw.text((1265, 1581), "Upright case and two back spreaders", font=font(28), fill=MUTED)
    draw.line((75, 1694, 2325, 1694), fill=(221, 226, 226), width=2)
    draw.text((79, 1724), "Same scale. Structural parts from exported STL; printed features are preview-only vector layers.",
              font=font(28), fill=MUTED)
    draw.text((79, 1773), f"Case body 720 mm  |  Foot clearance {board[4]:.0f} mm  |  Ground to head {board[5]:.0f} mm",
              font=font(28), fill=INK)
    output = directory / "upright_preview.png"
    canvas.save(output)
    print(output)


def arrow(draw, start, end, fill=INK, width=3, head=12):
    draw.line((*start, *end), fill=fill, width=width)
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    for point, sign in ((start, 1), (end, -1)):
        bx, by = point[0] + sign * ux * head, point[1] + sign * uy * head
        draw.polygon([point, (bx - uy * head * .38, by + ux * head * .38),
                      (bx + uy * head * .38, by - ux * head * .38)], fill=fill)


def vertical_label(canvas, xy, text, size=27, fill=INK):
    face = font(size, True)
    box = face.getbbox(text)
    patch = Image.new("RGBA", (box[2] - box[0] + 16, box[3] - box[1] + 16))
    ImageDraw.Draw(patch).text((8 - box[0], 8 - box[1]), text, font=face, fill=fill)
    patch = patch.rotate(90, expand=True)
    canvas.paste(patch, (int(xy[0] - patch.width / 2), int(xy[1] - patch.height / 2)), patch)


def side_view(directory, parts):
    canvas = Image.new("RGB", (2180, 2230), "white")
    draw = draw_title(canvas, "SIDE VIEW / UPRIGHT ASSEMBLY",
                      "Orthographic X-Z view, looking from -Y  /  Dimensions measured from exported parts")
    ox, oy, width, height = 265, 235, 1140, 1740
    board = bounds([p for p in parts if p["category"] == "board"])
    focus = (0, 0, board[5]/2)
    scale = board[5]*.57
    canvas.paste(scene(parts, (width, height), (0, -3000, 0), focus, scale), (ox, oy))
    s = height / (2 * scale)
    px = lambda x: ox + width / 2 + (x - focus[0]) * s
    pz = lambda z: oy + height / 2 - (z - focus[2]) * s
    case = bounds([p for p in parts if p["category"] == "case"])
    handle = bounds([p for p in parts if p["category"] == "handle"])
    board = bounds([p for p in parts if p["category"] == "board"])
    all_parts = bounds(parts)
    ground = min(0, all_parts[4])
    draw.line((320, pz(ground), 1370, pz(ground)), fill=(128, 137, 145), width=2)
    draw.text((1048, pz(ground) + 18), "Ground Z = 0", font=font(25), fill=MUTED)

    def dimension(x, z0, z1, source_x, label, label_offset=30, color=INK):
        for z in (z0, z1):
            draw.line((x - 8, pz(z), source_x, pz(z)), fill=(153, 162, 168), width=2)
        arrow(draw, (x, pz(z0)), (x, pz(z1)), fill=color)
        vertical_label(canvas, (x - label_offset, (pz(z0) + pz(z1)) / 2), label, fill=color)

    dimension(220, ground, board[5], px(board[0]),
              f"{board[5] - ground:.0f} mm / overall height", 38)
    dimension(475, case[4], case[5], px(case[0]),
              f"{case[5] - case[4]:.0f} mm / case body", 35)
    dimension(593, case[5], handle[5], px(handle[0]),
              f"{handle[5] - case[5]:.0f} mm", 36)
    draw.text((491, pz(handle[5]) - 72), "Handle extension", font=font(25), fill=MUTED)

    # Show the real overlap interval on the front, without drawing new solids.
    overlap_lo = max(case[4], board[4])
    overlap_hi = min(case[5], board[5])
    dimension(1250, overlap_lo, overlap_hi, px(board[1]) + 5,
              f"{overlap_hi - overlap_lo:.0f} mm / board overlaps case", -42, ACCENT)

    text_x = 1490
    draw.text((text_x, 305), "BOARD", font=font(29, True), fill=INK)
    draw.text((text_x, 351), f"{board[5]-board[4]:.0f} x {board[3]-board[2]:.0f} x 8 mm", font=font(31), fill=INK)
    draw.text((text_x, 400), "Nailong silhouette / flat KT sheet", font=font(26), fill=MUTED)
    draw.text((text_x, 533), "CONTACT PLANE", font=font(29, True), fill=INK)
    draw.text((text_x, 579), f"Board back: X = {board[0]:.0f} mm", font=font(27), fill=INK)
    draw.text((text_x, 625), f"Case front: X = {case[1]:.0f} mm", font=font(27), fill=INK)
    draw.text((text_x, 671), f"Lowest foot: Z = {board[4]:.0f} mm", font=font(27), fill=INK)
    draw.text((text_x, 721), "The board runs down the case face.", font=font(25), fill=MUTED)

    strap_parts = [p for p in parts if p["category"] == "mount"]
    heights = sorted({round((p["mesh"].GetBounds()[4] + p["mesh"].GetBounds()[5]) / 2, 3)
                      for p in strap_parts})
    draw.text((text_x, 875), "BACK MOUNTS / CONCEPT", font=font(29, True), fill=INK)
    for index, (z, descr) in enumerate(zip(heights, ("Lower spreader", "Upper spreader"))):
        yy = 927 + index * 60
        draw.text((text_x, yy), f"Z {z:.0f}  /  {descr}", font=font(27), fill=INK)
        # Label the high pair separately to preserve exact centre lines.
        target_y = pz(z)
        label_y = target_y if z < 700 else (pz(z) + (27 if index == 1 else -30))
        draw.line((px(board[1]) + 9, target_y, 1095, target_y, 1130, label_y),
                  fill=(96, 105, 113), width=2)
        draw.text((1145, label_y - 17), f"Z {z:.0f}", font=font(24, True), fill=INK)

    draw.text((text_x, 1221), "+X FRONT", font=font(29, True), fill=INK)
    draw.text((text_x, 1267), "Board faces right in this view.", font=font(26), fill=MUTED)
    draw.text((text_x, 1316), "Case is behind it, on the left.", font=font(26), fill=MUTED)
    arrow(draw, (text_x, 1415), (text_x + 300, 1415), fill=INK)
    # Remove the left arrowhead for a direction arrow.
    draw.rectangle((text_x - 1, 1407, text_x + 15, 1423), fill="white")
    draw.line((text_x, 1415, text_x + 30, 1415), fill=INK, width=3)

    draw.line((75, 2060, 2105, 2060), fill=(221, 226, 226), width=2)
    draw.text((79, 2090), "Exact STL side projection. Thin panel thickness is preserved; no exploded offsets or illustrative contact fills.",
              font=font(25), fill=MUTED)
    draw.text((79, 2140), "Passive wheel placeholders. Clamp fasteners, drive hardware and load capacity are not yet engineered.",
              font=font(25), fill=MUTED)
    output = directory / "upright_side.png"
    canvas.save(output)
    print(output)


def main(directory):
    parts = load_parts(directory)
    preview(directory, parts)
    side_view(directory, parts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=HERE)
    main(parser.parse_args().dir)
