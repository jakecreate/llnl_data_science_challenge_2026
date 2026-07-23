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
    pl.camera.zoom('tight')
    # pl.show(screenshot='test.png')
    pl.show()

    # cpos = mesh.plot(cpos='xy')


load_stl('data/missing_struts/stls/0.stl')
