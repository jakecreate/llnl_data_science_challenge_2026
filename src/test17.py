import trimesh
import numpy as np

def crop_stl_to_tif_bounds(input_stl, output_stl, tif_y_min, tif_y_max):
    print("1. Loading the aligned STL...")
    mesh = trimesh.load(input_stl)

    print(f"2. Slicing bottom at Y = {tif_y_min}...")
    # The normal vector [0, 1, 0] points UP. 
    # The function keeps everything in the direction of the normal.
    mesh = trimesh.intersections.slice_mesh_plane(
        mesh,
        plane_origin=[0, tif_y_min, 0],
        plane_normal=[0, 1, 0]
    )

    print(f"3. Slicing top at Y = {tif_y_max}...")
    # The normal vector [0, -1, 0] points DOWN.
    # We keep everything below the maximum boundary.
    mesh = trimesh.intersections.slice_mesh_plane(
        mesh,
        plane_origin=[0, tif_y_max, 0],
        plane_normal=[0, -1, 0]
    )

    print("4. Exporting perfectly bounded mesh...")
    mesh.export(output_stl)
    print(f"Success! Cropped mesh saved to: {output_stl}")

if __name__ == "__main__":
    # --- STEP 1: DEFINE YOUR BOUNDS ---
    # You will need to extract or calculate these physical coordinates from your TIF
    Y_MIN_FROM_TIF = 0.0   # Replace with actual lower physical bound
    Y_MAX_FROM_TIF = 720.0 # Replace with actual upper physical bound
    
    crop_stl_to_tif_bounds(
        input_stl="registered_model.stl",
        output_stl="test/perfectly_aligned_cropped_model_0_test.stl",
        tif_y_min=Y_MIN_FROM_TIF,
        tif_y_max=Y_MAX_FROM_TIF
    )