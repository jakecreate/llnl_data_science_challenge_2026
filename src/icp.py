import trimesh
import numpy as np
import json

# Load STL
mesh = trimesh.load('data/missing_struts/stls/0.stl')

# Load JSON junctions as target point cloud
with open('data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json') as f:
    data = json.load(f)
junction_pts = np.array([j['position'] for j in data['junctions']])

# Sample points from the STL surface as the source cloud
stl_pts = mesh.sample(5000)

# ICP: align stl_pts onto junction_pts
matrix, transformed, cost = trimesh.registration.icp(
    stl_pts, junction_pts, max_iterations=50
)
print("Alignment cost (lower = better fit):", cost)
print("Transform:\n", matrix)

# Apply the found transform to the actual mesh
mesh.apply_transform(matrix)
mesh.export('model_aligned.stl')