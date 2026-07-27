import json
import numpy as np
import pyvista as pv


def load(input_filepath: str):
    """Load an STL (or any format PyVista supports) as a mesh."""
    mesh = pv.read(input_filepath)
    return mesh


def load_json(input_filepath: str, radius: float = 1.5) -> pv.PolyData:
    """Load a strut-lattice JSON (junctions + struts) and convert it into a tube mesh."""
    with open(input_filepath) as f:
        data = json.load(f)

    junctions = data['junctions']
    struts = data['struts']

    max_id = max(j['id'] for j in junctions)
    points = np.zeros((max_id + 1, 3))
    for j in junctions:
        points[j['id']] = j['position']

    lines = []
    for s in struts:
        lines.extend([2, s['junction0'], s['junction1']])
    lines = np.array(lines)

    lattice = pv.PolyData(points, lines=lines)
    return lattice.tube(radius=radius)


def screenshot_slice(mesh, slice, output_filepath: str, facing: str = 'xz'):
    try:
        pl = pv.Plotter(off_screen=True)
        origin = (mesh.center[0], slice, mesh.center[2])
        # origin = (mesh.center[0], mesh.center[1], z_slice)
        slice_ = mesh.slice(normal=[0, 1, 0], origin=origin)
        pl.add_mesh(slice_, color='black')
        pl.enable_parallel_projection()
        pl.camera_position = facing
        pl.view_xz()   
        pl.camera.tight(view=facing)
        # pl.camera.zoom('tight')
        pl.show(screenshot=output_filepath)
        return True
    except Exception as e:
        print(f"Error while taking a screenshot slice: {e}")
        return False

json_mesh = load_json('210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices_full.json')
print("Mesh bounds:", json_mesh.bounds)
screenshot_slice(json_mesh, slice=((200)), output_filepath='slices/json_z0_slice.png')
json_mesh_1 = load_json('data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json')
screenshot_slice(json_mesh_1, slice=((200)), output_filepath='slices/json_z0_slice_missing.png')