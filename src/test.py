import json
import numpy as np
import pyvista as pv

# Load data
with open('data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json') as f:
    data = json.load(f)

junctions = data['junctions']
struts = data['struts']

# Build points array, indexed by junction id
max_id = max(j['id'] for j in junctions)
points = np.zeros((max_id + 1, 3))
for j in junctions:
    points[j['id']] = j['position']

# Build line connectivity: PyVista wants [n_points_in_line, p0, p1, n_points_in_line, p0, p1, ...]
lines = []
for s in struts:
    lines.extend([2, s['junction0'], s['junction1']])
lines = np.array(lines)

# Create PolyData of line segments
lattice = pv.PolyData(points, lines=lines)

# Convert lines -> tubes (cylinders) using the strut thickness
# thickness = 0.1 for all struts, so radius = thickness / 2
lattice_tubes = lattice.tube(radius=1.5)

# Plot
plotter = pv.Plotter()
plotter.add_mesh(lattice_tubes, color='silver', smooth_shading=True)
plotter.show_grid()
plotter.camera_position = 'xy'
plotter.show()