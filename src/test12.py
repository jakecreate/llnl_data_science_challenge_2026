import numpy as np
import pyvista as pv
import tifffile

# ---------- Load TIF volume ----------
volume = tifffile.imread('data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif')  # shape: (pages, H, W)
print("TIF volume shape:", volume.shape)

grid = pv.ImageData()
grid.dimensions = np.array(volume.shape) + 1
grid.spacing = (1, 1, 1)          # set real voxel spacing here if known
grid.origin = (0, 0, 0)
grid.cell_data['density'] = volume.flatten(order='F')

threshold = volume.max() * 0.5    # adjust based on your actual segmentation threshold
tif_surface = grid.threshold(threshold)

# ---------- Load STL mesh ----------
stl_mesh = pv.read('data/missing_struts/stls/0.stl')

stl_mesh.rotate_z(90, inplace=True)  # check sign — use -90 if metal ends up flipped/wrong direction
print("After rotation, STL bounds:", stl_mesh.bounds)

stl_min = np.array(stl_mesh.bounds[::2])  # [xmin, ymin, zmin]
stl_mesh.translate(-stl_min, inplace=True)
print("After translation, STL bounds:", stl_mesh.bounds)

# ---------- Plot both together ----------
pl = pv.Plotter()
pl.add_mesh(tif_surface, color='red', opacity=0.2, label='TIF scan')
pl.add_mesh(stl_mesh, color='silver', opacity=0.8, label='STL')
pl.add_legend()
pl.add_axes()
pl.show()