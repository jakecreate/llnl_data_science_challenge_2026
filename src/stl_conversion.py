import trimesh
import numpy as np
import tifffile



def stl_to_tif(input_filepath: str, output_filepath: str):
    # Load mesh
    mesh = trimesh.load(input_filepath)


    # Voxelize (pitch = voxel size, in mesh units)
    voxel_grid = mesh.voxelized(pitch=0.01).fill()  # fill() makes it solid, not just surface

    # Get as a boolean/uint8 numpy array (Z, Y, X)
    volume = voxel_grid.matrix.astype(np.uint8) * 255

    print(mesh.bounds)  # bounding box of STL, in STL units (mm? inches?)
    print(voxel_grid.shape)  # (Z, Y, X) — how many voxels per axis
    print(volume.shape, volume.dtype)
    print(np.count_nonzero(volume), volume.size)  # how much is actually "filled"
    print(mesh.is_watertight)

    # Save as a multi-page TIFF stack
    tifffile.imwrite(output_filepath, volume)

    
    with tifffile.TiffFile(output_filepath) as tif:
        print(tif.pages[0].tags)

stl_to_tif('data/missing_struts/stls/0.stl', 'output.tif')
