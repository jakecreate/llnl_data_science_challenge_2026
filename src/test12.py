import numpy as np
import pyvista as pv
import tifffile

# ---------- Load TIF volume ----------
volume = tifffile.imread('data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif')
volume[volume < 47000] = 0
print("TIF volume shape:", volume.shape)

grid = pv.ImageData()
grid.dimensions = np.array(volume.shape) + 1
grid.spacing = (1, 1, 1)
grid.origin = (0, 0, 0)
grid.cell_data['density'] = volume.flatten(order='F')

threshold = volume.max() * 0.5
tif_surface = grid.threshold(threshold)

# Center the TIF surface at (0,0,0)
tif_center = np.array(tif_surface.center)
tif_surface.translate(-tif_center, inplace=True)
print("TIF surface bounds after centering:", tif_surface.bounds)

# ---------- Load STL mesh ----------
stl_mesh = pv.read('registered_model.stl')

stl_mesh.rotate_z(90, inplace=True)  # check sign — use -90 if metal ends up flipped/wrong direction
print("After rotation, STL bounds:", stl_mesh.bounds)

# Center the STL at (0,0,0)
stl_center = np.array(stl_mesh.center)
stl_mesh.translate(-stl_center, inplace=True)
print("After centering, STL bounds:", stl_mesh.bounds)

# ---------- Plot both together ----------
pl = pv.Plotter()
pl.add_mesh(tif_surface, color='red', opacity=0.5, label='TIF scan')
pl.add_mesh(stl_mesh, color='silver', opacity=0.5, label='STL')
pl.add_legend()
pl.add_axes()
pl.show()