import tifffile
import pyvista as pv
import numpy as np

# volume = tifffile.imread('data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif')
volume = tifffile.imread('data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif')

print("Original TIF volume shape:", volume.shape)
# volume[volume < 40000] = 0

# --- Crop to first half along the y-axis ---
# Assuming volume.shape order matches (x, y, z) as used in grid.dimensions below.
# If your array is (Z, Y, X) instead, change axis=1 to whichever axis is Y.
# y_axis = 1
# half = volume.shape[y_axis] // 2
# volume = np.take(volume, indices=range(0, half), axis=y_axis)

# print("Cropped TIF volume shape:", volume.shape)

# volume[volume < 47000] = 0
volume[volume < 43400] = 0

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

origin = (tif_surface.center[0], 0, tif_surface.center[2])
sliced = tif_surface.slice(normal=[0, 1, 0], origin=origin)

# Plot
plotter = pv.Plotter()
plotter.enable_parallel_projection()
plotter.view_xz() 
plotter.camera.tight(view='xz')
plotter.add_mesh(sliced, color='black')
# plotter.add_mesh(tif_surface, color='red')
# print(grid.bounds)
plotter.show(screenshot='tif_potential_center.png')