import numpy as np
import pyvista as pv
import tifffile

def scale_stl_to_tif_bounds(stl_mesh, tif_bounds):
    """
    Scales and translates an STL mesh so its bounding box matches
    the given TIF bounding box exactly, per axis.

    Parameters
    ----------
    stl_mesh : pv.PolyData
        The STL mesh to transform (modified in place).
    tif_bounds : tuple or array-like
        (xmin, xmax, ymin, ymax, zmin, zmax) — e.g. grid.bounds

    Returns
    -------
    pv.PolyData
        The same mesh, scaled and translated to match tif_bounds.
    """
    tif_bounds = np.array(tif_bounds)
    tif_min = tif_bounds[::2]   # [xmin, ymin, zmin]
    tif_max = tif_bounds[1::2]  # [xmax, ymax, zmax]
    tif_extents = tif_max - tif_min

    stl_bounds = np.array(stl_mesh.bounds)
    stl_min = stl_bounds[::2]
    stl_max = stl_bounds[1::2]
    stl_extents = stl_max - stl_min

    # Move STL's min corner to origin first
    stl_mesh.translate(-stl_min, inplace=True)

    # Per-axis scale factor to stretch STL extents to match TIF extents
    per_axis_scale = tif_extents / stl_extents
    print("Per-axis scale factors (x, y, z):", per_axis_scale)

    # Non-uniform scale: pv.PolyData.scale accepts a 3-element list for per-axis scaling
    stl_mesh.scale(per_axis_scale, inplace=True)

    # Move to TIF's actual origin (in case it's not (0,0,0))
    stl_mesh.translate(tif_min, inplace=True)

    print("Final STL bounds:", stl_mesh.bounds)
    print("Target TIF bounds:", tif_bounds)

    return stl_mesh

volume = tifffile.imread('data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif')  # shape: (pages, H, W)

grid = pv.ImageData()
grid.dimensions = np.array(volume.shape) + 1
grid.spacing = (1, 1, 1)          # set real voxel spacing here if known
grid.origin = (0, 0, 0)
grid.cell_data['density'] = volume.flatten(order='F')

stl_mesh = pv.read('cropped_0.stl')
print("stl before: ", stl_mesh.bounds)
stl_mesh.rotate_z(90, inplace=True)  # apply your correct orientation fix first

stl_min = np.array(stl_mesh.bounds[::2])
stl_mesh.translate(-stl_min, inplace=True)  # normalize before fitting to TIF bounds


uniform_scale_factor = np.mean([(grid.bounds[1]-grid.bounds[0])/(stl_mesh.bounds[1]-stl_mesh.bounds[0]),
                                (grid.bounds[3]-grid.bounds[2])/(stl_mesh.bounds[3]-stl_mesh.bounds[2]),
                                (grid.bounds[5]-grid.bounds[4])/(stl_mesh.bounds[5]-stl_mesh.bounds[4])])
# stl_mesh.scale(uniform_scale_factor, inplace=True)
stl_mesh.scale([(grid.bounds[1]-grid.bounds[0])/(stl_mesh.bounds[1]-stl_mesh.bounds[0]),
                                (grid.bounds[3]-grid.bounds[2])/(stl_mesh.bounds[3]-stl_mesh.bounds[2]),
                                (grid.bounds[5]-grid.bounds[4])/(stl_mesh.bounds[5]-stl_mesh.bounds[4])], inplace=True)


stl_min = np.array(stl_mesh.bounds[::2])
stl_mesh.translate(-stl_min, inplace=True)

print("Final STL bounds:", stl_mesh.bounds)
print("TIF bounds:", grid.bounds)

stl_mesh.save("test_0.stl")

# scale_stl_to_tif_bounds(stl_mesh, grid.bounds)