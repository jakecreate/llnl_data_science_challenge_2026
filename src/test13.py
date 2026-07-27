import numpy as np
import pyvista as pv
import tifffile

volume = tifffile.imread('data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif')  # shape: (pages, H, W)

grid = pv.ImageData()
grid.dimensions = np.array(volume.shape) + 1
grid.spacing = (1, 1, 1)          # set real voxel spacing here if known
grid.origin = (0, 0, 0)
grid.cell_data['density'] = volume.flatten(order='F')

stl_mesh = pv.read('registered_0.stl')

# ---------- Load TIF volume ----------
print("TIF volume shape:", volume.shape)

print("TIF grid bounds:", grid.bounds)
print("STL bounds (after rotation, before scaling):", stl_mesh.bounds)

tif_bounds = np.array(grid.bounds)   # [xmin,xmax,ymin,ymax,zmin,zmax]
stl_bounds = np.array(stl_mesh.bounds)

tif_extents = np.array([tif_bounds[1]-tif_bounds[0], tif_bounds[3]-tif_bounds[2], tif_bounds[5]-tif_bounds[4]])
stl_extents = np.array([stl_bounds[1]-stl_bounds[0], stl_bounds[3]-stl_bounds[2], stl_bounds[5]-stl_bounds[4]])

print("TIF extents:", tif_extents)
print("STL extents:", stl_extents)
print("Ratio (TIF/STL) per axis:", tif_extents / stl_extents)

correct_scale_factor = (tif_extents / stl_extents).mean()
print("Corrected STL->TIF scale factor:", correct_scale_factor)

stl_mesh = pv.read('model_scaled_translated_full.stl')
stl_mesh.rotate_z(90, inplace=True)  # or whatever rotation you confirmed correct

stl_mesh.scale(correct_scale_factor, inplace=True)

stl_min = np.array(stl_mesh.bounds[::2])
stl_mesh.translate(-stl_min, inplace=True)

print("Final STL bounds:", stl_mesh.bounds)
print("TIF bounds:       ", grid.bounds)