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
stl_mesh = pv.read('model_scaled_translated_full.stl')

# Apply scale factor to bring STL into the same units as the TIF

# Axis correspondence: TIF stacking axis matches STL's Y, but flipped
# PyVista axis order in points is [x, y, z] -> swap/flip as needed
pts = stl_mesh.points.copy()
pts[:, 1] = -pts[:, 1]   # flip Y
stl_mesh.points = pts

# Translate STL so its min bound sits at (0,0,0), matching the TIF's origin
stl_min = np.array(stl_mesh.bounds[::2])  # [xmin, ymin, zmin]
stl_mesh.translate(-stl_min, inplace=True)

# ---------- Plot both together ----------
pl = pv.Plotter()
pl.add_mesh(tif_surface, color='red', opacity=0.2, label='TIF scan')
pl.add_mesh(stl_mesh, color='silver', opacity=0.8, label='STL')
pl.add_legend()
pl.add_axes()
pl.show()