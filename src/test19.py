import trimesh
import tifffile
import numpy as np

def crop_tif_to_stl_bounds(stl_path, tif_path, output_tif_path, pixel_size_x, pixel_size_z, origin_x=0.0, origin_z=0.0):
    print("1. Loading STL and extracting physical bounds...")
    mesh = trimesh.load(stl_path)
    
    # mesh.bounds returns [[x_min, y_min, z_min], [x_max, y_max, z_max]]
    physical_bounds = mesh.bounds
    stl_x_min, stl_x_max = physical_bounds[0][0], physical_bounds[1][0]
    stl_z_min, stl_z_max = physical_bounds[0][2], physical_bounds[1][2]
    
    print(f"   STL X Bounds: {stl_x_min:.2f} to {stl_x_max:.2f}")
    print(f"   STL Z Bounds: {stl_z_min:.2f} to {stl_z_max:.2f}")

    print("2. Converting physical bounds to TIF pixel indices...")
    # Formula: index = (physical_position - origin) / pixel_size
    # np.floor and np.ceil ensure we capture the full bounding volume
    px_x_min = int(np.floor((stl_x_min - origin_x) / pixel_size_x))
    px_x_max = int(np.ceil((stl_x_max - origin_x) / pixel_size_x))
    
    px_z_min = int(np.floor((stl_z_min - origin_z) / pixel_size_z))
    px_z_max = int(np.ceil((stl_z_max - origin_z) / pixel_size_z))

    print("3. Loading the TIF image...")
    tif_array = tifffile.imread(tif_path)
    
    # Check if the TIF is 2D or 3D to handle array shapes correctly
    is_3d = len(tif_array.shape) == 3
    
    print("4. Cropping the TIF array...")
    if is_3d:
        # Assuming standard 3D medical/scientific TIF order: (Z, Y, X)
        # Clamp indices to ensure we don't try to crop outside the array limits
        px_z_min = max(0, px_z_min)
        px_z_max = min(tif_array.shape[0], px_z_max)
        px_x_min = max(0, px_x_min)
        px_x_max = min(tif_array.shape[2], px_x_max)
        
        print(f"   Cropping Z-axis indices: {px_z_min} to {px_z_max}")
        print(f"   Cropping X-axis indices: {px_x_min} to {px_x_max}")
        
        # Crop Z and X, leaving Y untouched
        cropped_tif = tif_array[px_z_min:px_z_max, :, px_x_min:px_x_max]
    else:
        # Assuming 2D TIF order: (Z/Y, X) - adjust based on your specific 2D plane
        px_z_min = max(0, px_z_min)
        px_z_max = min(tif_array.shape[0], px_z_max)
        px_x_min = max(0, px_x_min)
        px_x_max = min(tif_array.shape[1], px_x_max)
        
        cropped_tif = tif_array[px_z_min:px_z_max, px_x_min:px_x_max]

    print("5. Exporting cropped TIF...")
    tifffile.imwrite(output_tif_path, cropped_tif)
    print(f"Success! Cropped TIF saved to: {output_tif_path}")


if __name__ == "__main__":
    # --- CONFIGURE YOUR TIF METADATA HERE ---
    # The physical size of a single pixel/voxel (e.g., 0.1 mm per pixel)
    PIXEL_SIZE_X = 1.0  
    PIXEL_SIZE_Z = 1.0  
    
    # The physical coordinate where the TIF's [0, 0, 0] pixel is located in space.
    # If the TIF and STL share an exact origin (0,0,0), leave these as 0.0.
    ORIGIN_X = 0.0      
    ORIGIN_Z = 0.0      

    crop_tif_to_stl_bounds(
        stl_path="perfectly_aligned_cropped_model.stl",
        tif_path="data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif",
        output_tif_path="cropped_image.tif",
        pixel_size_x=PIXEL_SIZE_X,
        pixel_size_z=PIXEL_SIZE_Z,
        origin_x=ORIGIN_X,
        origin_z=ORIGIN_Z
    )