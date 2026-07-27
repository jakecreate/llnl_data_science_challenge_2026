import pyvista as pv
import matplotlib.pyplot as plt

def slice(mesh, z_slice):
    bounds = list(mesh.bounds)
    bounds[4] = (z_slice - 1 / 2)
    bounds[5] = (z_slice + 1 / 2)
    return mesh.clip_box(bounds, invert=False)

def screenshot_slice(mesh, z_slice, output_filepath: str, facing: str = 'xy'):
    try:
        pl = pv.Plotter(off_screen=True)
        # slab = slice(mesh, z_slice)
        # pl.add_mesh(slab, color='black')
        origin = (mesh.center[0], mesh.center[1], z_slice)
        slice = mesh.slice(normal=[0, 0, 1], origin=origin)
        pl.add_mesh(slice, color='black')
        pl.camera_position = facing
        pl.camera.zoom('tight')
        pl.show(screenshot=output_filepath)
        return True
    except Exception as e:
        print(f"Erorr while taking a screenshot slice: {e}")
        return False

def screenshot(mesh, output_filepath: str):
    try:
        pl = pv.Plotter(off_screen=True)
        pl.add_mesh(mesh, color='black')
        pl.camera_position = 'xy'
        pl.camera.zoom('tight')
        pl.show(screenshot=output_filepath)
        return True
    except Exception as e:
        print(f"Erorr while taking a screenshot: {e}")
        return False

def load(input_filepath: str):
    mesh = pv.read(input_filepath)
    return mesh

# mesh = load('data/missing_struts/stls/0.stl')
mesh = load('cropped_0.5.stl')
print(screenshot_slice(mesh, 0, 'slices/z0_0.5_v2_test_skew.png', 'zy'))