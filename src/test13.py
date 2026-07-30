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
    # STEP 1: EXTRACT & SWAP BOUNDS FROM JSON
    # ==========================================
    print(f"1. Loading coordinates from {json_path}...")
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    # Extract positions as (X, Y, Z)
    points = np.array([j["position"] for j in json_data["junctions"]])

    # SWAP AXES: (X, Y, Z) -> (Z, Y, X)
    points = points[:, [2, 1, 0]]

    # Calculate bounds based on the newly swapped axes
    x_min, x_max = points[:, 0].min(), points[:, 0].max()
    y_min, y_max = points[:, 1].min(), points[:, 1].max()
    z_min, z_max = points[:, 2].min(), points[:, 2].max()

    print("\n   Swapped JSON Bounds:")
    print(f"   X (Old Z): {x_min:.2f} to {x_max:.2f}")
    print(f"   Y (Old Y): {y_min:.2f} to {y_max:.2f}")
    print(f"   Z (Old X): {z_min:.2f} to {z_max:.2f}")

    # ==========================================
    # STEP 2: CROP THE TIF (Using swapped bounds)
    # ==========================================
    print("\n2. Converting swapped coordinates to TIF indices...")
    px_x_min = int(np.floor((x_min - origin_x) / pixel_size_x))
    px_x_max = int(np.ceil((x_max - origin_x) / pixel_size_x))

    px_y_min = int(np.floor((y_min - origin_y) / pixel_size_y))
    px_y_max = int(np.ceil((y_max - origin_y) / pixel_size_y))

    px_z_min = int(np.floor((z_min - origin_z) / pixel_size_z))
    px_z_max = int(np.ceil((z_max - origin_z) / pixel_size_z))

    print("3. Loading and cropping the TIF image...")
    tif_array = tifffile.imread(tif_path)

    # Clamp indices to TIF shape (Z, Y, X)
    px_z_min = max(0, px_z_min)
    px_z_max = min(tif_array.shape[0], px_z_max)

    px_y_min = max(0, px_y_min)
    px_y_max = min(tif_array.shape[1], px_y_max)

    px_x_min = max(0, px_x_min)
    px_x_max = min(tif_array.shape[2], px_x_max)

    cropped_tif = tif_array[px_z_min:px_z_max, px_y_min:px_y_max, px_x_min:px_x_max]
    tifffile.imwrite(output_tif_path, cropped_tif)
    print(f"   Cropped TIF saved to: {output_tif_path}")

    # ==========================================
    # STEP 3: BACK-CALCULATE GRID SNAP BOUNDS
    # ==========================================
    grid_x_min = (px_x_min * pixel_size_x) + origin_x
    grid_x_max = (px_x_max * pixel_size_x) + origin_x
    
    grid_y_min = (px_y_min * pixel_size_y) + origin_y
    grid_y_max = (px_y_max * pixel_size_y) + origin_y
    
    grid_z_min = (px_z_min * pixel_size_z) + origin_z
    grid_z_max = (px_z_max * pixel_size_z) + origin_z

    print("\n   GRID-SNAPPED BOUNDS (Perfect Alignment):")
    print(f"   X: {grid_x_min:.2f} to {grid_x_max:.2f}")
    print(f"   Y: {grid_y_min:.2f} to {grid_y_max:.2f}")
    print(f"   Z: {grid_z_min:.2f} to {grid_z_max:.2f}")

    # ==========================================
    # STEP 4: LOAD, SWAP AXES, AND SLICE THE STL
    # ==========================================
    print("\n4. Loading, swapping axes, and slicing the STL...")
    mesh = trimesh.load(stl_path)
    
    # SWAP AXES: Reorder the vertices from (X, Y, Z) to (Z, Y, X)
    mesh.vertices = mesh.vertices[:, [2, 1, 0]]
    
    # IMPORTANT: Swapping two axes mirrors the geometry. 
    # We must invert the mesh to restore outward-facing normals.
    mesh.invert()

    # Slice X axis using the grid-snapped boundaries
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[grid_x_min, 0, 0], plane_normal=[1, 0, 0])
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[grid_x_max, 0, 0], plane_normal=[-1, 0, 0])

    # Slice Y axis
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, grid_y_min, 0], plane_normal=[0, 1, 0])
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, grid_y_max, 0], plane_normal=[0, -1, 0])

    # Slice Z axis
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, 0, grid_z_min], plane_normal=[0, 0, 1])
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, 0, grid_z_max], plane_normal=[0, 0, -1])

    if len(mesh.vertices) == 0:
        raise ValueError("Slicing produced an empty mesh — check coordinate alignment!")

    mesh.export(output_stl_path)
    print(f"   Cropped STL saved to: {output_stl_path}")
    print("\nSuccess! Both files are now bound to the exact same grid-snapped coordinates.")


if __name__ == "__main__":
    PIXEL_SIZE_X = 1.0
    PIXEL_SIZE_Y = 1.0
    PIXEL_SIZE_Z = 1.0

    ORIGIN_X = 0.0
    ORIGIN_Y = 0.0
    ORIGIN_Z = 0.0

    crop_stl_and_tif_to_json_bounds(
        json_path="data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json",
        stl_path="test/registered_model_0.5.stl",
        tif_path="data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif",
        output_stl_path="test/final_cropped_model_0.5.stl",
        output_tif_path="test/final_cropped_image_0.5.tif",
        pixel_size_x=PIXEL_SIZE_X,
        pixel_size_y=PIXEL_SIZE_Y,
        pixel_size_z=PIXEL_SIZE_Z,
        origin_x=ORIGIN_X,
        origin_y=ORIGIN_Y,
        origin_z=ORIGIN_Z
    )