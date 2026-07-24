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
thickness = 1
lattice_tubes = lattice.tube(radius=0.5)

# Plot
plotter = pv.Plotter()
plotter.add_mesh(lattice_tubes, color='silver', smooth_shading=True)
# input_filepath = 'data/missing_struts/stls/0.stl'
input_filepath = 'cropped.stl'
mesh = pv.read(input_filepath)
# pl = pv.Plotter(off_screen=True)
# pl = pv.Plotter()
plotter.add_mesh(mesh)
plotter.camera_position = 'xz'

# plotter = pv.PyVistaPlotter() if hasattr(pv, 'PyVistaPlotter') else pv.Plotter()
# plane = pv.Plane(center=(0, 0, 0), direction=(0, 0, 1), i_size=10, j_size=10)

# Add the plane to the scene
# plotter.add_mesh(plane, color='black', show_edges=True)
# plotter.show()

plane = pv.Plane(center=(0, 0, 0), direction=(0, 0, 1), i_size=5, j_size=5)
plotter.add_mesh(plane, show_edges=True, color='lightblue')
plotter.add_axes()

# pl.camera.zoom('tight')
# pl.show(screenshot='test.png')
plotter.show()