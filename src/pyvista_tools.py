import pyvista as pv
import matplotlib.pyplot as plt

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
    pl.camera.tight(view='xz')
    pl.add_axes()
    pl.show(screenshot=output_filepath)

def thick_slice_z(mesh, z_center, thickness):
    bounds = list(mesh.bounds)
    bounds[4] = (z_center - thickness / 2)
    bounds[5] = (z_center + thickness / 2)
    return mesh.clip_box(bounds, invert=False)

def slice_stl(input_filepath, height):
    mesh = pv.read(input_filepath)
    # if height is None:
    #     origin = mesh.center  # default: slice through the middle
    # else:
    #     origin = (mesh.center[0], mesh.center[1], height)

    origin = (mesh.center[0], mesh.center[1], 0)
    # slice = mesh.slice(normal=[0, 0, 1], origin=origin)
    # origin = (mesh.center[0], mesh.center[1], 10)
    slice1 = mesh.slice(normal=[0, 0, 1], origin=(mesh.center[0], mesh.center[1], 0))
    # slab = thick_slice_z(mesh, z_center=mesh.center[2], thickness=0.1) ---
    # slice = mesh.slice(normal=[0, 0, 1])
    pl = pv.Plotter()
    # pl.camera_position = 'xy' ----

    sliced = mesh.slice(normal=[0, 0, 1], origin=origin)
    filled = sliced.delaunay_2d(alpha=0.4)   # triangulates the loop into a solid surface
    pl.add_mesh(filled)

    # pl.add_mesh(mesh, color='k')
    # pl.add_mesh(slice)
    pl.add_mesh(slice1, color='q')
    pl.add_legend()
    pl.add_axes()
    # pl.add_mesh(slab)
    pl.show()
    
# def load_stl(input_filepath: str, output_filepath: str, y_position: float = None, thickness: float = None):
#     mesh = pv.read(input_filepath)
#     print(get_bounds(mesh))

#     if y_position is None:
#         y_position = mesh.center[1]

#     if thickness is not None:
#         bounds = list(mesh.bounds)
#         bounds[2] = y_position - thickness / 2
#         bounds[3] = y_position + thickness / 2
#         sliced = mesh.clip_box(bounds, invert=False)
#     else:
#         origin = (mesh.center[0], y_position, mesh.center[2])
#         sliced = mesh.slice(normal=(0, 1, 0), origin=origin)

#     print('n points in slice:', sliced.n_points)
#     print('sliced bounds:', sliced.bounds)

#     if sliced.n_points == 0:
#         print("Warning: empty slice at this position — skipping screenshot.")
#         return sliced

#     pl = pv.Plotter()
#     # pl = pv.Plotter(off_screen=True)
#     pl.add_mesh(sliced)
#     pl.camera_position = 'xz'

#     b = sliced.bounds
#     if (b[1] - b[0]) > 1e-6 and (b[5] - b[4]) > 1e-6:  # nonzero X and Z extent
#         pl.camera.zoom('tight')
#     else:
#         print("Warning: degenerate slice extent — using default zoom instead of 'tight'.")

#     pl.show(screenshot=output_filepath)
#     return sliced

load_stl('data/missing_struts/stls/0.stl', None)
# load_stl('model_scaled_translated_full.stl', None)
# load_stl('data/missing_struts/stls/0.stl')
# load_stl('model_aligned.stl')
