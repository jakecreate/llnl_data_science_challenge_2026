import json
import numpy as np
import tifffile

def crop_tif_with_json_bounds(json_path, tif_path, output_tif_path, pixel_size_y, pixel_size_z, origin_y=0.0, origin_z=0.0):
    print(f"1. Loading coordinates from {json_path}...")
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    # Extract all [x, y, z] positions from the junctions
    points = np.array([j["position"] for j in json_data["junctions"]])

    # --- STEP 1: EXTRACT Y AND Z BOUNDS ---
    print("2. Calculating true Y and Z bounds from JSON...")
    # Index 1 is Y, Index 2 is Z
    y_min, y_max = points[:, 1].min(), points[:, 1].max()
    z_min, z_max = points[:, 2].min(), points[:, 2].max()
    
    print(f"   JSON Y Bounds: {y_min:.2f} to {y_max:.2f}")
    print(f"   JSON Z Bounds: {z_min:.2f} to {z_max:.2f}")

    # --- STEP 2: CONVERT TO PIXEL INDICES ---
    print("3. Converting physical coordinates to TIF indices...")
    # np.floor rounds down for the minimum, np.ceil rounds up for the maximum
    # to ensure the entire bounding volume is enclosed without cutting off edges.
    px_y_min = int(np.floor((y_min - origin_y) / pixel_size_y))
    px_y_max = int(np.ceil((y_max - origin_y) / pixel_size_y))
    
    px_z_min = int(np.floor((z_min - origin_z) / pixel_size_z))
    px_z_max = int(np.ceil((z_max - origin_z) / pixel_size_z))

    # --- STEP 3: LOAD AND CROP THE TIF ---
    print("4. Loading and cropping the TIF image...")
    tif_array = tifffile.imread(tif_path)
    
    # Ensure indices don't exceed the actual size of the TIF array
    # Assuming standard 3D TIF shape: (Z, Y, X)
    px_z_min = max(0, px_z_min)
    px_z_max = min(tif_array.shape[0], px_z_max)
    px_y_min = max(0, px_y_min)
    px_y_max = min(tif_array.shape[1], px_y_max)
    
    print(f"   Cropping Z-axis array indices: {px_z_min} to {px_z_max}")
    print(f"   Cropping Y-axis array indices: {px_y_min} to {px_y_max}")

    # Crop the Z and Y dimensions, leaving the X dimension intact
    cropped_tif = tif_array[px_z_min:px_z_max, px_y_min:px_y_max, :]

    # --- STEP 4: EXPORT ---
    print("5. Exporting cropped TIF...")
    tifffile.imwrite(output_tif_path, cropped_tif)
    print(f"Success! Cropped TIF saved to: {output_tif_path}")

if __name__ == "__main__":
    # --- CONFIGURE YOUR METADATA HERE ---
    # The physical size of a single pixel/voxel (e.g., 1.0 units per pixel)
    PIXEL_SIZE_Y = 1.0  
    PIXEL_SIZE_Z = 1.0  
    
    # The physical coordinate mapping to the TIF's [0, 0, 0] index.
    ORIGIN_Y = 0.0      
    ORIGIN_Z = 0.0      

    crop_tif_with_json_bounds(
        json_path="data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json", # Or "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json"
        tif_path="data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif",
        output_tif_path="json_bounded_image.tif",
        pixel_size_y=PIXEL_SIZE_Y,
        pixel_size_z=PIXEL_SIZE_Z,
        origin_y=ORIGIN_Y,
        origin_z=ORIGIN_Z
    )