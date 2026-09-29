"""Render the exported, unmodified STL shells. Requires vtk and Pillow."""

from pathlib import Path
import argparse

import vtk
from vtk.util.numpy_support import vtk_to_numpy
from PIL import Image, ImageDraw, ImageFont


BG = (246, 247, 245)
INK = (32, 39, 45)
MUTED = (101, 111, 119)


def font(size, bold=False):
    candidates = [
        Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def read_stl(path):
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(path))
    reader.Update()
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputConnection(reader.GetOutputPort())
    normals.SetFeatureAngle(35)
    normals.ConsistencyOn()
    normals.AutoOrientNormalsOn()
    normals.SplittingOn()
    normals.Update()
    result = vtk.vtkPolyData()
    result.DeepCopy(normals.GetOutput())
    return result


def add_shell(renderer, mesh, color):
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(mesh)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetColor(*color)
    prop.SetAmbient(0.20)
    prop.SetDiffuse(0.78)
    prop.SetSpecular(0.25)
    prop.SetSpecularPower(35)
    prop.SetInterpolationToPhong()
    renderer.AddActor(actor)

    # Genuine mesh crease edges, not a wireframe of every triangle.
    edges = vtk.vtkFeatureEdges()
    edges.SetInputData(mesh)
    edges.BoundaryEdgesOn()
    edges.FeatureEdgesOn()
    edges.NonManifoldEdgesOff()
    edges.ManifoldEdgesOff()
    edges.SetFeatureAngle(40)
    edge_mapper = vtk.vtkPolyDataMapper()
    edge_mapper.SetInputConnection(edges.GetOutputPort())
    edge_mapper.ScalarVisibilityOff()
    edge_mapper.SetResolveCoincidentTopologyToPolygonOffset()
    edge_actor = vtk.vtkActor()
    edge_actor.SetMapper(edge_mapper)
    edge_actor.GetProperty().SetColor(0.08, 0.10, 0.12)
    edge_actor.GetProperty().SetOpacity(0.36)
    edge_actor.GetProperty().SetLineWidth(1)
    renderer.AddActor(edge_actor)


def render(shells, size, direction, focus, scale, headlight=False, ao=False):
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(*(c / 255 for c in BG))
    for mesh, color in shells:
        add_shell(renderer, mesh, color)

    camera = renderer.GetActiveCamera()
    camera.SetFocalPoint(*focus)
    camera.SetPosition(*(focus[i] + direction[i] for i in range(3)))
    camera.SetViewUp(0, 0, 1)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(scale)

    renderer.RemoveAllLights()
    for position, intensity in [((500, -900, 1600), 0.95),
                                ((-900, -200, 650), 0.50),
                                ((400, 1000, 1000), 0.65)]:
        light = vtk.vtkLight()
        light.SetLightTypeToSceneLight()
        light.SetPosition(*position)
        light.SetFocalPoint(*focus)
        light.SetIntensity(intensity)
        renderer.AddLight(light)
    if headlight:
        light = vtk.vtkLight()
        light.SetLightTypeToHeadlight()
        light.SetIntensity(1.05)
        renderer.AddLight(light)

    # SSAO is optional: leave it off to avoid driver-dependent depth banding.
    steps = vtk.vtkRenderStepsPass()
    occlusion = vtk.vtkSSAOPass()
    occlusion.SetDelegatePass(steps)
    occlusion.SetRadius(22)
    occlusion.SetBias(0.2)
    occlusion.SetKernelSize(128)
    occlusion.BlurOn()
    renderer.SetPass(occlusion if ao else steps)
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
    image = Image.fromarray(pixels.reshape(size[1], size[0], 3)[::-1].copy())
    window.Finalize()
    return image


def main(directory):
    base = read_stl(directory / "case26_base.stl")
    lid = read_stl(directory / "case26_lid.stl")
    base_color = (0.24, 0.265, 0.285)
    lid_color = (0.275, 0.295, 0.315)
    canvas = Image.new("RGB", (2000, 1590), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((70, 42), "CASE / 26", font=font(58, True), fill=INK)
    draw.text((73, 120), "720 x 470 x 290 mm  /  R20  /  3 mm ABS shell", font=font(27), fill=MUTED)
    draw.text((1605, 61), "SHELL STUDY", font=font(24, True), fill=INK)
    draw.text((1605, 98), "Actual STL geometry", font=font(22), fill=MUTED)

    hero = render([(base, base_color), (lid, lid_color)], (1860, 690),
                  (1100, -1350, 1150), (0, 0, 145), 425)
    canvas.paste(hero, (70, 188))
    draw.text((99, 208), "01 / CLOSED CASE", font=font(27, True), fill=INK)
    draw.text((99, 819), "Horizontal pose  /  split plane Z = 170 mm", font=font(25), fill=MUTED)
    draw.text((1290, 819), "+X front: three 18 mm openings", font=font(25), fill=MUTED)

    interior = render([(base, base_color)], (905, 482),
                      (650, -850, 1900), (0, 0, 83), 475)
    top = render([(lid, lid_color)], (905, 482),
                 (650, -850, 1900), (0, 0, 240), 475)
    canvas.paste(interior, (70, 913))
    canvas.paste(top, (1025, 913))
    draw.text((99, 932), "02 / BOTTOM SHELL", font=font(26, True), fill=INK)
    draw.text((1054, 932), "03 / LID EXTERIOR", font=font(26, True), fill=INK)
    draw.text((73, 1423), "8 locator frames  /  100 x 50 x 40 mm clear space", font=font(25), fill=INK)
    draw.text((1028, 1423), "3 strap channels  /  40 mm wide, 2 mm deep", font=font(25), fill=INK)
    draw.line((70, 1500, 1930, 1500), fill=(221, 226, 226), width=2)
    draw.text((73, 1521), "Base and lid shown in assembly coordinates. No wheels, drive plate or accessories.", font=font(23), fill=MUTED)
    output = directory / "case26_preview.png"
    canvas.save(output)
    print(output)
    render_details(directory, base, base_color)


def render_details(directory, base, color):
    canvas = Image.new("RGB", (2000, 1340), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((70, 42), "CASE / 26  -  DETAILS", font=font(53, True), fill=INK)
    draw.text((73, 119), "Actual STL geometry  /  bottom shell only", font=font(26), fill=MUTED)

    underside = render([(base, color)], (905, 938),
                       (500, -700, -2400), (0, 0, 35), 510, headlight=True, ao=False)
    rear = render([(base, color)], (905, 418),
                  (-1700, -160, 180), (-320, 0, 100), 200, headlight=True, ao=False)
    inside = render([(base, color)], (905, 418),
                    (850, -280, 850), (-312, 0, 77), 155, headlight=True, ao=False)
    canvas.paste(underside, (70, 189))
    canvas.paste(rear, (1025, 189))
    canvas.paste(inside, (1025, 709))
    draw.text((99, 211), "04 / UNDERSIDE", font=font(26, True), fill=INK)
    draw.text((1054, 211), "05 / REAR EXTERIOR", font=font(26, True), fill=INK)
    draw.text((1054, 731), "06 / REAR INNER WALL", font=font(26, True), fill=INK)
    draw.text((73, 1150), "4 flat 60 x 60 mm platforms  /  M6 clearance holes", font=font(25), fill=INK)
    draw.text((73, 1191), "Centers: X = +/-270 mm, Y = +/-200 mm", font=font(24), fill=MUTED)
    draw.text((1028, 632), "Recessed handle pocket  /  nothing protrudes", font=font(25), fill=INK)
    draw.text((1028, 1150), "80 x 50 mm mounting face  /  no electronics fitted", font=font(25), fill=INK)
    draw.line((70, 1250, 1930, 1250), fill=(221, 226, 226), width=2)
    draw.text((73, 1272), "Underside is viewed from below. Rear = -X. Interior detail is cropped for inspection.", font=font(23), fill=MUTED)
    output = directory / "case26_details.png"
    canvas.save(output)
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=Path(__file__).resolve().parent)
    main(parser.parse_args().dir)
