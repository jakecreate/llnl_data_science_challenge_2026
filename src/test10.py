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
    
    points = np.array([j["position"] for j in json_data["junctions"]])

    x_min, x_max = points[:, 0].min(), points[:, 0].max()
    y_min, y_max = points[:, 1].min(), points[:, 1].max()
    z_min, z_max = points[:, 2].min(), points[:, 2].max()
    
    print("\nMaster JSON Bounds:")
    print(f"   X: {x_min:.2f} to {x_max:.2f}")
    print(f"   Y: {y_min:.2f} to {y_max:.2f}")
    print(f"   Z: {z_min:.2f} to {z_max:.2f}")

    # ==========================================
    # STEP 2: LOAD, ROTATE, AND SLICE THE STL
    # ==========================================
    print("\n2. Loading and slicing the STL...")
    mesh = trimesh.load(stl_path)
    print(f"   Loaded STL bounds: {mesh.bounds}")

    print("   Applying 90-degree Z-axis rotation...")
    angle_z = np.pi / 2
    rot_matrix_z = trimesh.transformations.rotation_matrix(angle_z, [0, 0, 1])
    mesh.apply_transform(rot_matrix_z)
    print(f"   STL bounds after Z rotation: {mesh.bounds}")

    print("   Applying 90-degree Y-axis rotation...")
    angle_y = np.pi / 2
    rot_matrix_y = trimesh.transformations.rotation_matrix(angle_y, [0, 1, 0])
    mesh.apply_transform(rot_matrix_y)
    print(f"   STL bounds after Y rotation: {mesh.bounds}")

    # Combined transform, applied in the SAME order as the mesh (Z then Y)
    combined_rot = rot_matrix_y @ rot_matrix_z

    # Rotate the JSON-derived bounding box corners the SAME way, so the
    # slicing planes stay consistent with the mesh's new orientation
    corners = np.array([
        [x_min, y_min, z_min], [x_max, y_min, z_min],
        [x_min, y_max, z_min], [x_min, y_min, z_max],
        [x_max, y_max, z_min], [x_max, y_min, z_max],
        [x_min, y_max, z_max], [x_max, y_max, z_max],
    ])
    rotated_corners = trimesh.transform_points(corners, combined_rot)
    rx_min, ry_min, rz_min = rotated_corners.min(axis=0)
    rx_max, ry_max, rz_max = rotated_corners.max(axis=0)

    print("   Rotated JSON bounds (used for slicing):")
    print(f"   X: {rx_min:.2f} to {rx_max:.2f}")
    print(f"   Y: {ry_min:.2f} to {ry_max:.2f}")
    print(f"   Z: {rz_min:.2f} to {rz_max:.2f}")

    # Slice X axis
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[rx_min, 0, 0], plane_normal=[1, 0, 0])
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[rx_max, 0, 0], plane_normal=[-1, 0, 0])

    # Slice Y axis
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, ry_min, 0], plane_normal=[0, 1, 0])
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, ry_max, 0], plane_normal=[0, -1, 0])

    # Slice Z axis
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, 0, rz_min], plane_normal=[0, 0, 1])
    mesh = trimesh.intersections.slice_mesh_plane(mesh, plane_origin=[0, 0, rz_max], plane_normal=[0, 0, -1])

    print(f"   Sliced STL vertex count: {len(mesh.vertices)}")
    if len(mesh.vertices) == 0:
        raise ValueError("Slicing produced an empty mesh — check that rotated STL and JSON bounds overlap!")

    mesh.export(output_stl_path)
    print(f"   Cropped STL saved to: {output_stl_path}")

    # ==========================================
    # STEP 3: CROP THE TIF (uses ORIGINAL, unrotated JSON bounds — TIF was never rotated)
    # ==========================================
    print("\n3. Converting physical coordinates to TIF indices...")
    px_x_min = int(np.floor((x_min - origin_x) / pixel_size_x))
    px_x_max = int(np.ceil((x_max - origin_x) / pixel_size_x))

    px_y_min = int(np.floor((y_min - origin_y) / pixel_size_y))
    px_y_max = int(np.ceil((y_max - origin_y) / pixel_size_y))

    px_z_min = int(np.floor((z_min - origin_z) / pixel_size_z))
    px_z_max = int(np.ceil((z_max - origin_z) / pixel_size_z))

    print("4. Loading and cropping the TIF image...")
    tif_array = tifffile.imread(tif_path)

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

    cropped_tif = tif_array[px_z_min:px_z_max, px_y_min:px_y_max, px_x_min:px_x_max]

    tifffile.imwrite(output_tif_path, cropped_tif)
    print(f"   Cropped TIF saved to: {output_tif_path}")
    print("\nSuccess! Both files are now bound to the exact JSON coordinates.")


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