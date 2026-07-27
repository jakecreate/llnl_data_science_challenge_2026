import json
import numpy as np
import pyvista as pv
import tifffile

# ---------- Load TIF volume ----------
volume = tifffile.imread('data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif')  # shape: (pages, H, W) e.g. (761, 815, 837)
print("TIF volume shape:", volume.shape)

# Wrap as a PyVista ImageData grid so it can be rendered/contoured
grid = pv.ImageData()
grid.dimensions = np.array(volume.shape) + 1  # cell data needs dims+1
grid.spacing = (1, 1, 1)  # set real voxel spacing here if known
grid.origin = (0, 0, 0)
grid.cell_data['density'] = volume.flatten(order='F')

# Extract an isosurface (the actual solid shape) at some threshold
threshold = volume.max() * 0.5  # adjust based on your data's actual value range
tif_surface = grid.threshold(threshold)  # or use .contour([threshold]) for a surface mesh

# ---------- Load JSON lattice ----------
with open('data/missing_struts/octet_truss_9x9x9.json') as f:
    data = json.load(f)

junctions = data['junctions']
struts = data['struts']

max_id = max(j['id'] for j in junctions)
points = np.zeros((max_id + 1, 3))
for j in junctions:
    points[j['id']] = j['position']

# Apply your established scale factor + any needed axis flip/translation
scale_factor = 79.4 / 4.617  # from your earlier cell-size comparison
points_scaled = points / scale_factor
points_scaled -= points_scaled.min(axis=0)  # start at (0,0,0), matching TIF origin

lines = []
for s in struts:
    lines.extend([2, s['junction0'], s['junction1']])
lines = np.array(lines)

lattice = pv.PolyData(points_scaled, lines=lines)
lattice_tubes = lattice.tube(radius=0.1 / 2 / scale_factor)

# ---------- Plot both together ----------
pl = pv.Plotter()
pl.add_mesh(tif_surface, color='red', opacity=0.4, label='TIF scan')
pl.add_mesh(lattice_tubes, color='steelblue', label='JSON lattice')
pl.add_legend()
pl.add_axes()
pl.show()