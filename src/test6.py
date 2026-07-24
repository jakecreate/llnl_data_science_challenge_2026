import os
import numpy as np
import tifffile
from PIL import Image


def load_volume(input_filepath: str) -> np.ndarray:
    ext = os.path.splitext(input_filepath)[1].lower()
    if ext == '.npy':
        voxels = np.load(input_filepath, allow_pickle=True)
        if voxels.dtype == object and voxels.shape == ():
            voxels = voxels.item()
            if isinstance(voxels, dict):
                voxels = voxels.get('voxels', voxels.get('data'))
        voxels = np.asarray(voxels)
    elif ext in ('.tif', '.tiff'):
        voxels = tifffile.imread(input_filepath)
    else:
        raise ValueError(f'Unsupported file extension: {ext}')
    return voxels


def visualize_slice(input_filepath: str, output_filepath: str, slice_index: int, axis: int = 0) -> str:
    try:
        voxels = load_volume(input_filepath)
        slice_ = np.take(voxels, slice_index, axis=axis)

        slice_min, slice_max = slice_.min(), slice_.max()
        if slice_max > slice_min:
            normalized = ((slice_ - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(slice_, dtype=np.uint8)

        Image.fromarray(normalized).save(output_filepath)
    except Exception as e:
        return f"Error while running visualize_slice: {e}"
    return f"Dataset has been sliced and saved to {output_filepath}"

print(visualize_slice('data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif',
                'slices/z100_tan.png', 100, 0))