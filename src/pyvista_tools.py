import pyvista as pv
import matplotlib.pyplot as plt
import numpy as np

def get_bounds(mesh):
    xmin, xmax, ymin, ymax, zmin, zmax = mesh.bounds
    x_bound = xmax - xmin
    y_bound = ymax - ymin
    z_bound = zmax - zmin
    return x_bound, y_bound, z_bound

def load_stl(input_filepath: str, output_filepath: str):
    mesh = pv.read(input_filepath)
    print(get_bounds(mesh))
    pl = pv.Plotter()
    pl.add_mesh(mesh)
    # pl.camera_position = 'xz'
    # pl.reset_camera()
    # pl.camera.zoom('tight')
    pl.enable_parallel_projection()
    pl.view_xz()   
    # pl.camera.tight(view='xz')
    pl.add_axes()
    pl.show(screenshot=output_filepath)

def thick_slice_z(mesh, z_center, thickness):
    bounds = list(mesh.bounds)
    bounds[4] = (z_center - thickness / 2)
    bounds[5] = (z_center + thickness / 2)
    return mesh.clip_box(bounds, invert=False)

def screenshot_slice(input_filepath):
    try:
        pl = pv.Plotter()
        mesh = pv.read(input_filepath)
        print("first load:", mesh.bounds)
        stl_center = np.array(mesh.center)
        mesh.translate(-stl_center, inplace=True)
        print("pre rotate:", mesh.bounds)
        mesh.rotate_z(90, inplace=True)
        print("post rotate:", mesh.bounds)
        origin = (mesh.center[0], 0, mesh.center[2])
        slice = mesh.slice(normal=[0, 1, 0], origin=origin)
        pl.add_mesh(slice, color='black')
        pl.enable_parallel_projection()
        pl.camera_position = 'xz'
        pl.camera.tight(view='xz')
        pl.show(screenshot='stl_potential_center.png')
        return True
    except Exception as e:
        print(f"Erorr while taking a screenshot slice: {e}")
        return False

screenshot_slice('perfectly_aligned_cropped_model.stl')
