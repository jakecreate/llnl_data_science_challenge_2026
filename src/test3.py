

import json
import numpy as np
import pyvista as pv
import trimesh

# --- Load STL ---
# mesh = trimesh.load('data/missing_struts/stls/0.stl')
# pv_mesh = pv.read('data/missing_struts/stls/0.stl')
mesh = trimesh.load('model_lattice_only.stl')
pv_mesh = pv.read('model_lattice_only.stl')

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

# junction_pts = np.array([j['position'] for j in junctions])
# json_min = junction_pts.min(axis=0)
# json_max = junction_pts.max(axis=0)
# json_extents = json_max - json_min   # this is it — shape (3,), one value per X/Y/Z

# # JSON: 9 unit cells across each axis
# json_cell_size = json_extents / 9
# print("JSON cell size (design units):", json_cell_size)

# stl_extents = mesh.bounds[1] - mesh.bounds[0]

# # STL: 9 cells in X/Z, but 11 "cells" in Y (9 real + 2 metal, per your observation)
# stl_cell_size_xz = np.array([stl_extents[0] / 9, stl_extents[2] / 9])
# stl_cell_size_y = stl_extents[1] / 11
# print("STL cell size X/Z:", stl_cell_size_xz)
# print("STL cell size Y:", stl_cell_size_y)

# stl_cell_size = np.mean([4.61030854, 4.61062431, 4.640000430020419])
# print("STL cell size (avg):", stl_cell_size)

# json_cell_size_scalar = json_cell_size.mean()  # from earlier, ~79.4-ish per axis
# print("JSON cell size (avg):", json_cell_size_scalar)

# scale_factor = json_cell_size_scalar / stl_cell_size
# print("Corrected scale factor:", scale_factor)

# --- Overlay ---
pl = pv.Plotter()
pl.add_mesh(pv_mesh, color='silver', opacity=0.4)
pl.add_mesh(lattice_tubes, color='black')
pl.add_axes()
pl.show()

# cell_len_y = 4.640000430020419  # one Y-cell length in STL units

# y_min, y_max = mesh.bounds[0][1], mesh.bounds[1][1]
# new_y_min = y_min + cell_len_y   # remove 1 cell from the bottom
# new_y_max = y_max - cell_len_y   # remove 1 cell from the top

# cropped = mesh.slice_plane(plane_origin=[0, new_y_min, 0], plane_normal=[0, 1, 0])
# cropped = cropped.slice_plane(plane_origin=[0, new_y_max, 0], plane_normal=[0, -1, 0])
# cropped.export('model_lattice_only.stl')

# print("Cropped extents:", cropped.bounds[1] - cropped.bounds[0])