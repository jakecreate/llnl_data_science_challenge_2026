import json
import numpy as np
import pyvista as pv


def load_lattice_tubes(filepath: str, radius: float = 1.5) -> pv.PolyData:
    """Load a strut-lattice JSON and convert it into a tube mesh."""
    with open(filepath) as f:
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


def compute_xor(mesh_a: pv.PolyData, mesh_b: pv.PolyData) -> pv.PolyData:
    """
    Boolean XOR: geometry present in A but not B, combined with geometry
    present in B but not A. Highlights struts that differ between the two lattices.
    """
    a = mesh_a.triangulate().clean()
    b = mesh_b.triangulate().clean()

    a_minus_b = a.boolean_difference(b)
    b_minus_a = b.boolean_difference(a)

    return a_minus_b.merge(b_minus_a)


# ---------- Load both lattices ----------
design_tubes = load_lattice_tubes(
    '210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices_full.json'
)
registered_tubes = load_lattice_tubes(
    'data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json'
)

# ---------- Plot both overlapping ----------
plotter = pv.Plotter()
plotter.add_mesh(design_tubes, color='red', opacity=0.5, smooth_shading=True, label='Design')
plotter.add_mesh(registered_tubes, color='silver', opacity=0.5, smooth_shading=True, label='Registered')
plotter.add_legend()
plotter.show_grid()
plotter.camera_position = 'xy'
plotter.show()

# ---------- Compute and plot the XOR (differences only) ----------
try:
    xor_mesh = compute_xor(design_tubes, registered_tubes)

    plotter_xor = pv.Plotter()
    plotter_xor.add_mesh(xor_mesh, color='yellow', smooth_shading=True, label='XOR (differences)')
    plotter_xor.add_legend()
    plotter_xor.show_grid()
    plotter_xor.camera_position = 'xy'
    plotter_xor.show()
except Exception as e:
    print(f"Boolean XOR failed: {e}")