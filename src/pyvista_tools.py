import pyvista as pv
import matplotlib.pyplot as plt

def get_bounds(mesh):
    xmin, xmax, ymin, ymax, zmin, zmax = mesh.bounds
    x_bound = xmax - xmin
    y_bound = ymax - ymin
    z_bound = zmax - zmin
    return x_bound, y_bound, z_bound

def load_stl(input_filepath: str):
    mesh = pv.read(input_filepath)
    print(get_bounds(mesh))
    # pl = pv.Plotter(off_screen=True)
    pl = pv.Plotter()
    pl.add_mesh(mesh, color='black')
    pl.camera_position = 'xy'
    # pl.camera.zoom('tight')
    # pl.show(screenshot='test.png')
    pl.show()

    # cpos = mesh.plot(cpos='xy')

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
    pl.add_mesh(slice1, color='black')
    # pl.add_mesh(slab)
    pl.show()
    


slice_stl('data/missing_struts/stls/0.stl', 0)
# load_stl('data/missing_struts/stls/0.stl')
# load_stl('model_aligned.stl')
