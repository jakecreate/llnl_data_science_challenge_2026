import pyvista as pv
import matplotlib.pyplot as plt

def slice(mesh, slice, side: str = 'z'):
    bounds = list(mesh.bounds)
    if (side == 'x'):
        bounds[0] = (slice - 1 / 2)
        bounds[1] = (slice + 1 / 2)
        pass
    elif (side == 'y'):
        bounds[2] = (slice - 1 / 2)
        bounds[3] = (slice + 1 / 2)
    else:
        bounds[4] = (slice - 1 / 2)
        bounds[5] = (slice + 1 / 2)
    return mesh.clip_box(bounds, invert=False)

def screenshot_slice(mesh, z_slice, output_filepath: str, normal=(0, 0, 1), facing: str = 'xy', slice_side: str = 'z'):
    try:
        pl = pv.Plotter(off_screen=True)
        origin = (mesh.center[0], mesh.center[1], z_slice) if normal == (0, 0, 1) else mesh.center
        sliced = mesh.slice(normal=list(normal), origin=origin)

        print('n points in slice:', sliced.n_points)  # sanity check it's not empty
        print('slice bounds:', sliced.bounds)

        pl.add_mesh(sliced, color='black', line_width=2)
        pl.camera_position = facing
        pl.camera.zoom('tight')
        pl.show(screenshot=output_filepath)
        return True
    except Exception as e:
        print(f"Error while taking a screenshot slice: {e}")
        return False

def load(input_filepath: str):
    mesh = pv.read(input_filepath)
    return mesh

mesh = load('cropped_0.5.stl')
screenshot_slice(mesh, 0, 'slices/z_0_test.png', (0, 0, 1), 'yz', 'x')    