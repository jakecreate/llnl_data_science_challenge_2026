import numpy as np
import pyvista as pv
import tifffile


def align_stl(input_filepath: str) -> pv.PolyData:
    """Rotate and translate the STL into the TIF's frame (already registered, no scaling needed)."""
    mesh = pv.read(input_filepath)

    mesh.rotate_z(90, inplace=True)  # metal axis -> matches TIF's stacking axis

    stl_min = np.array(mesh.bounds[::2])
    mesh.translate(-stl_min, inplace=True)

    print("Aligned STL bounds:", mesh.bounds)
    return mesh


def crop_stl_y(mesh: pv.PolyData, y_min: float, y_max: float) -> pv.PolyData:
    """Crop the STL to a Y range using a box clip."""
    bounds = list(mesh.bounds)
    bounds[2] = y_min  # ymin
    bounds[3] = y_max  # ymax
    cropped = mesh.clip_box(bounds, invert=False)
    print("Cropped STL bounds:", cropped.bounds)
    return cropped


def crop_tif_y(volume: np.ndarray, y_min: int, y_max: int, y_axis: int = 1) -> np.ndarray:
    """
    Crop the TIF volume to a Y index range.
    y_axis: which array axis corresponds to Y (confirm against your data's shape ordering).
    """
    y_min_idx = max(0, int(np.floor(y_min)))
    y_max_idx = min(volume.shape[y_axis], int(np.ceil(y_max)))

    slicer = [slice(None)] * volume.ndim
    slicer[y_axis] = slice(y_min_idx, y_max_idx)
    cropped = volume[tuple(slicer)]

    print("Cropped TIF shape:", cropped.shape)
    return cropped


# ---------- Usage ----------

stl_mesh = align_stl('test/perfectly_aligned_cropped_model_0.5.stl')
volume = tifffile.imread('data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif')  # shape: (pages, H, W)

print("TIF volume shape:", volume.shape)

# Pick a shared Y range — adjust to your actual target region
y_min = stl_mesh.bounds[2] + (stl_mesh.bounds[3] - stl_mesh.bounds[2]) * 0.33
y_max = stl_mesh.bounds[2] + (stl_mesh.bounds[3] - stl_mesh.bounds[2]) * 0.66

cropped_stl = crop_stl_y(stl_mesh, y_min, y_max)
cropped_volume = crop_tif_y(volume, y_min, y_max, y_axis=1)  # confirm y_axis matches your data

surface = cropped_stl.extract_surface() 
surface.save('test/cropped_shared_region_0.5.stl')
# tifffile.imwrite('test/cropped_shared_region.tif', cropped_volume)

# ---------- Quick visual check ----------
pl = pv.Plotter()
pl.add_mesh(cropped_stl, color='silver', opacity=0.6)
pl.add_mesh(cropped_volume, color='red', opacity=0.6)
pl.add_axes()
pl.show()