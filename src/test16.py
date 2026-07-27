import trimesh
import numpy as np
import json

# ---------- Load STL (full 9x11x9, metal included) ----------
mesh = trimesh.load('data/missing_struts/stls/0.stl')

# ---------- Load JSON junctions ----------
with open('data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json') as f:
    data = json.load(f)
junction_pts = np.array([j['position'] for j in data['junctions']])

# ---------- Sample points from STL surface ----------
stl_pts = mesh.sample(20000)  # denser sampling helps ICP converge better

# ---------- Rough pre-alignment (helps ICP avoid bad local minima) ----------
# Use your already-confirmed orientation fix (metal axis -> matches JSON's longest axis)
# and a rough scale guess, so ICP starts close to correct.
stl_centered = stl_pts - stl_pts.mean(axis=0)
json_centered = junction_pts - junction_pts.mean(axis=0)

rough_scale = np.linalg.norm(json_centered, axis=1).mean() / np.linalg.norm(stl_centered, axis=1).mean()

initial = np.eye(4)
initial[:3, :3] *= rough_scale
initial[:3, 3] = junction_pts.mean(axis=0) - rough_scale * stl_pts.mean(axis=0)

# ---------- ICP with scale ----------
matrix, transformed, cost = trimesh.registration.icp(
    stl_pts, junction_pts,
    initial=initial,
    max_iterations=100,
    scale=True
)
print("ICP cost (lower is better):", cost)
print("Final transform:\n", matrix)

#----- part 2

# Apply the found transform to the FULL mesh (not just sampled points)
mesh.apply_transform(matrix)
print("Aligned STL bounds:", mesh.bounds)
print("JSON bounds:", junction_pts.min(axis=0), junction_pts.max(axis=0))

json_min = junction_pts.min(axis=0)
json_max = junction_pts.max(axis=0)

# Add a small margin so strut walls (which extend slightly past junction centerlines) aren't clipped
margin = 2.0  # in JSON units — adjust based on strut thickness scaled appropriately

crop_min = json_min - margin
crop_max = json_max + margin

cropped = mesh.slice_plane(plane_origin=crop_min, plane_normal=[1,0,0])
cropped = cropped.slice_plane(plane_origin=crop_max, plane_normal=[-1,0,0])
cropped = cropped.slice_plane(plane_origin=crop_min, plane_normal=[0,1,0])
cropped = cropped.slice_plane(plane_origin=crop_max, plane_normal=[0,-1,0])
cropped = cropped.slice_plane(plane_origin=crop_min, plane_normal=[0,0,1])
cropped = cropped.slice_plane(plane_origin=crop_max, plane_normal=[0,0,-1])

cropped.export('model_aligned_cropped.stl')
print("Cropped extents:", cropped.bounds[1] - cropped.bounds[0])
print("JSON extents:   ", json_max - json_min)