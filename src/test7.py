import numpy as np
import pyvista as pv
import tifffile

DENSITY_THRESHOLD = 43400
# DENSITY_THRESHOLD = 0

def thick_slice_y(mesh, y_center, thickness):
    bounds = list(mesh.bounds)
    bounds[2] = y_center - thickness / 2
    bounds[3] = y_center + thickness / 2
    return mesh.clip_box(bounds, invert=False)

def thick_slice_z(mesh, z_center, thickness):
    bounds = list(mesh.bounds)
    bounds[4] = z_center - thickness / 2
    bounds[5] = z_center + thickness / 2
    return mesh.clip_box(bounds, invert=False)

# def thick_slice_y(mesh, z_center, thickness):
#     bounds = list(mesh.bounds)
#     bounds[5] = z_center + thickness / 2
#     return mesh.clip_box(bounds, invert=False)

# ---------- TIF ----------
volume = tifffile.imread('test/final_cropped_image.tif')
print("TIF volume shape:", volume.shape)

volume = volume.copy()
volume[volume < DENSITY_THRESHOLD] = 0

grid = pv.ImageData()
grid.dimensions = np.array(volume.shape) + 1
grid.spacing = (1, 1, 1)
grid.origin = (0, 0, 0)
grid.cell_data['density'] = volume.flatten(order='F')

tif_surface = grid.threshold(volume.max() * 0.5)

tif_center = np.array(tif_surface.center)
tif_surface.translate(-tif_center, inplace=True)
print("TIF surface bounds after centering:", tif_surface.bounds)

tif_slice = tif_surface.slice(normal=[0, 1, 0], origin=(0, 0, 0))
print("TIF slice n_points:", tif_slice.n_points, "bounds:", tif_slice.bounds)

# tif_slice = thick_slice_y(tif_surface, 0, 1)

# ---------- STL ----------
stl_mesh = pv.read('test/final_cropped_model_0.5.stl')
print("STL bounds (raw):", stl_mesh.bounds)

# stl_mesh.rotate_z(-90, inplace=True)
# print("STL bounds (after rotation):", stl_mesh.bounds)

# stl_mesh.rotate_y(90, inplace=True)

stl_center = np.array(stl_mesh.center)
stl_mesh.translate(-stl_center, inplace=True)
print("STL bounds (after centering):", stl_mesh.bounds)

stl_slice = stl_mesh.slice(normal=[0, 1, 0], origin=(0, 0, 0))
print("STL slice n_points:", stl_slice.n_points, "bounds:", stl_slice.bounds)

# stl_slice = thick_slice_z(stl_mesh, 0, 2)

# ---------- Compare side by side ----------
pl = pv.Plotter(shape=(1, 2))
pl.subplot(0, 0)
# pl.add_mesh(tif_slice, color='black')
pl.add_mesh(tif_surface, color='black')
# tif_box = tif_surface.bounding_box()
# pl.add_mesh(tif_box, color='red', opacity=0.1)
pl.enable_parallel_projection()
pl.view_xz()
pl.add_axes()
pl.show_grid()
pl.add_text("TIF center slice", font_size=10)

pl.subplot(0, 1)
# pl.add_mesh(stl_slice, color='black')
pl.add_mesh(stl_mesh, color='black')
# stl_box = stl_mesh.bounding_box()
# pl.add_mesh(stl_box, color='red', opacity=0.1)
pl.enable_parallel_projection()
pl.view_xz()
pl.add_text("STL center slice", font_size=10)

pl.link_views()
pl.add_axes()
pl.show_grid()
pl.show(screenshot='center_slice_comparison.png')