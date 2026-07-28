import json
import numpy as np
import trimesh
import open3d as o3d

def register_stl_to_json(stl_path, json_path, output_stl_path):
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    json_points = np.array([j["position"] for j in json_data["junctions"]])

    mesh = trimesh.load(stl_path)
    vertices = mesh.vertices.copy()

    # 3.
    y_coords = vertices[:, 1]
    y_min, y_max = y_coords.min(), y_coords.max()
    y_height = y_max - y_min
    
    unit_cell_y = y_height / 11.0
    
    crop_min_y = y_min + (unit_cell_y * 0.95)
    crop_max_y = y_max - (unit_cell_y * 0.95)
    
    crop_mask = (y_coords >= crop_min_y) & (y_coords <= crop_max_y)
    cropped_vertices = vertices[crop_mask]

    # 4.
    source_pcd = o3d.geometry.PointCloud()
    source_pcd.points = o3d.utility.Vector3dVector(cropped_vertices)

    target_pcd = o3d.geometry.PointCloud()
    target_pcd.points = o3d.utility.Vector3dVector(json_points)

    # 5.
    source_center = source_pcd.get_center()
    target_center = target_pcd.get_center()

    source_extent = source_pcd.get_max_bound() - source_pcd.get_min_bound()
    target_extent = target_pcd.get_max_bound() - target_pcd.get_min_bound()
    
    scale_factor = np.mean(target_extent / source_extent)

    init_transform = np.eye(4)
    init_transform[:3, :3] *= scale_factor
    init_transform[:3, 3] = target_center - (source_center * scale_factor)

    # 6.
    max_correspondence_dist = unit_cell_y * 0.5
    
    icp_result = o3d.pipelines.registration.registration_icp(
        source_pcd, 
        target_pcd, 
        max_correspondence_dist, 
        init_transform,
        o3d.pipelines.registration.TransformationEstimationPointToPoint()
    )

    transformation_matrix = icp_result.transformation
    print(transformation_matrix)

    # 7.
    aligned_mesh = mesh.copy()
    aligned_mesh.apply_transform(transformation_matrix)
    aligned_mesh.export(output_stl_path)
    
    print(f"Registered STL saved to: {output_stl_path}")

if __name__ == "__main__":
    register_stl_to_json(
        stl_path="data/missing_struts/stls/0.stl",
        json_path="data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json",
        output_stl_path="registered_model.stl"
    )