import json
import numpy as np
import trimesh
import tifffile

def crop_stl_and_tif_to_json_bounds(
    json_path, stl_path, tif_path, 
    output_stl_path, output_tif_path, 
    pixel_size_x, pixel_size_y, pixel_size_z, 
    origin_x=0.0, origin_y=0.0, origin_z=0.0
):
    # ==========================================
    # STEP 1: EXTRACT BOUNDS FROM JSON
    # ==========================================
    print(f"1. Loading coordinates from {json_path}...")
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    # Extract all [x, y, z] positions from the junctions
    points = np.array([j["position"] for j in json_data["junctions"]])

    x_min, x_max = points[:, 0].min(), points[:, 0].max()
    y_min, y_max = points[:, 1].min(), points[:, 1].max()
    z_min, z_max = points[:, 2].min(), points[:, 2].max()
    
    print("\nMaster JSON Bounds:")
    print(f"   X: {x_min:.2f} to {x_max:.2f}")
    print(f"   Y: {y_min:.2f} to {y_max:.2f}")
    print(f"   Z: {z_min:.2f} to {z_max:.2f}")

    # ==========================================
    # STEP 2: CROP THE STL
    # ==========================================
    print("\n2. Loading and slicing the STL...")
    mesh = trimesh.load(stl_path)

    # Slice X axis
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[x_min, 0, 0], plane_normal=[1, 0, 0])
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[x_max, 0, 0], plane_normal=[-1, 0, 0])
    
    # Slice Y axis
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, y_min, 0], plane_normal=[0, 1, 0])
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, y_max, 0], plane_normal=[0, -1, 0])
    
    # Slice Z axis
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, 0, z_min], plane_normal=[0, 0, 1])
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, 0, z_max], plane_normal=[0, 0, -1])

    mesh.export(output_stl_path)
    print(f"   Cropped STL saved to: {output_stl_path}")

    # ==========================================
    # STEP 3: CROP THE TIF
    # ==========================================
    print("\n3. Converting physical coordinates to TIF indices...")
    # Map the physical space to the pixel space
    px_x_min = int(np.floor((x_min - origin_x) / pixel_size_x))
    px_x_max = int(np.ceil((x_max - origin_x) / pixel_size_x))
    
    px_y_min = int(np.floor((y_min - origin_y) / pixel_size_y))
    px_y_max = int(np.ceil((y_max - origin_y) / pixel_size_y))
    
    px_z_min = int(np.floor((z_min - origin_z) / pixel_size_z))
    px_z_max = int(np.ceil((z_max - origin_z) / pixel_size_z))

    print("4. Loading and cropping the TIF image...")
    tif_array = tifffile.imread(tif_path)
    
    # Clamp indices so they don't exceed the TIF array bounds
    # Assuming standard 3D TIF shape: (Z, Y, X)
    px_z_min = max(0, px_z_min)
    px_z_max = min(tif_array.shape[0], px_z_max)
    
    px_y_min = max(0, px_y_min)
    px_y_max = min(tif_array.shape[1], px_y_max)
    
    px_x_min = max(0, px_x_min)
    px_x_max = min(tif_array.shape[2], px_x_max)

    print("   Cropping Array Indices:")
    print(f"   Z: {px_z_min} to {px_z_max}")
    print(f"   Y: {px_y_min} to {px_y_max}")
    print(f"   X: {px_x_min} to {px_x_max}")

    # Apply the 3D crop
    cropped_tif = tif_array[px_z_min:px_z_max, px_y_min:px_y_max, px_x_min:px_x_max]

    tifffile.imwrite(output_tif_path, cropped_tif)
    print(f"   Cropped TIF saved to: {output_tif_path}")
    print("\nSuccess! Both files are now bound to the exact JSON coordinates.")


if __name__ == "__main__":
    # --- CONFIGURE METADATA HERE ---
    # The physical real-world size of a single voxel for each axis
    PIXEL_SIZE_X = 1.0  
    PIXEL_SIZE_Y = 1.0  
    PIXEL_SIZE_Z = 1.0  
    
    # The physical coordinate that maps to the TIF array's [0, 0, 0] index.
    ORIGIN_X = 0.0      
    ORIGIN_Y = 0.0      
    ORIGIN_Z = 0.0      

    crop_stl_and_tif_to_json_bounds(
        json_path="data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json", 
        stl_path="registered_model.stl",
        tif_path="data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif",
        output_stl_path="test/final_cropped_model_0.stl",
        output_tif_path="test/final_cropped_image_0.tif",
        pixel_size_x=PIXEL_SIZE_X,
        pixel_size_y=PIXEL_SIZE_Y,
        pixel_size_z=PIXEL_SIZE_Z,
        origin_x=ORIGIN_X,
        origin_y=ORIGIN_Y,
        origin_z=ORIGIN_Z
    )