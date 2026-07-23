import pyvista as pv
import matplotlib.pyplot as plt

def slice(mesh, z_slice):
    bounds = list(mesh.bounds)
    bounds[4] = (z_slice - 1 / 2)
    bounds[5] = (z_slice + 1 / 2)
    return mesh.clip_box(bounds, invert=False)

def screenshot_slice(mesh, z_slice, output_filepath: str):
    try:
        pl = pv.Plotter(off_screen=True)
        slab = slice(mesh, z_slice)
        pl.add_mesh(slab, color='black')
        pl.camera_position = 'xy'
        pl.camera.zoom('tight')
        pl.show(output_filepath)
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
        pl.show(output_filepath)
        return True
    except Exception as e:
        print(f"Erorr while taking a screenshot: {e}")
        return False

def load(input_filepath: str):
    mesh = pv.read(input_filepath)
    return mesh