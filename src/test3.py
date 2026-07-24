

import json
import numpy as np
import pyvista as pv
import trimesh

# --- Load STL ---
mesh = trimesh.load('data/missing_struts/stls/0.stl')
pv_mesh = pv.read('data/missing_struts/stls/0.stl')

# Translate STL so its min bound sits at (0,0,0)
stl_min = np.array(mesh.bounds[0])
pv_mesh.translate(-stl_min, inplace=True)

# --- Load JSON ---
with open('data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json') as f:
    data = json.load(f)

junctions = data['junctions']
struts = data['struts']

max_id = max(j['id'] for j in junctions)
points = np.zeros((max_id + 1, 3))
for j in junctions:
    points[j['id']] = j['position']

scale_factor = 17.21  # from earlier X/Z agreement
points_scaled = points / scale_factor

# Translate JSON points so its min bound sits at (0,0,0)
json_min = points_scaled.min(axis=0)
points_scaled = points_scaled - json_min

# Build lattice tubes
lines = []
for s in struts:
    lines.extend([2, s['junction0'], s['junction1']])
lines = np.array(lines)

lattice = pv.PolyData(points_scaled, lines=lines)
lattice_tubes = lattice.tube(radius=0.1)

# --- Overlay ---
pl = pv.Plotter()
pl.add_mesh(pv_mesh, color='silver', opacity=0.4)
pl.add_mesh(lattice_tubes, color='black')
pl.add_axes()
pl.show()