import json

import numpy as np
import pyvista as pv


BRIAN_JSON = (
    'data/missing_struts/registered_jsons/'
    '210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json'
)
REFERENCE_JSON = 'data/missing_struts/octet_truss_9x9x9.json'
STL_PATH = 'data/missing_struts/stls/0.5.stl'


def load_junction_points(filepath):
    with open(filepath) as file:
        data = json.load(file)
    junctions = sorted(data['junctions'], key=lambda junction: junction['id'])
    return np.asarray([junction['position'] for junction in junctions], dtype=float)


reference_points = load_junction_points(REFERENCE_JSON)
brian_points = load_junction_points(BRIAN_JSON)

# Fit Brian coordinates from reference coordinates:
# brian = scale * (reference @ rotation.T) + translation
reference_centered = reference_points - reference_points.mean(axis=0)
brian_centered = brian_points - brian_points.mean(axis=0)
u, s, vt = np.linalg.svd(brian_centered.T @ reference_centered)
d = np.sign(np.linalg.det(u @ vt))
rotation = u @ np.diag([1, 1, d]) @ vt          # brian ≈ rotation @ reference

scale = np.sum(brian_centered * (reference_centered @ rotation.T)) / np.sum(
    reference_centered**2
)
translation = brian_points.mean(axis=0) - scale * (
    reference_points.mean(axis=0) @ rotation.T
)

fit = scale * (reference_points @ rotation.T) + translation
fit_error = np.sqrt(np.mean((fit - brian_points) ** 2))

# Express both JSON bounding regions in the reference frame and intersect them.
reference_min = reference_points.min(axis=0)
reference_max = reference_points.max(axis=0)
brian_in_reference = (brian_points - translation) @ rotation / scale
brian_min = brian_in_reference.min(axis=0)
brian_max = brian_in_reference.max(axis=0)
common_min = np.maximum(reference_min, brian_min)
common_max = np.minimum(reference_max, brian_max)

# The STL has an additional 9x9x1 metal box at the low-z end.  One lattice
# cell is 18 / 9 = 2 reference units thick, so exclude that layer.
outer_box_thickness = 18.0 / 9.0
common_min[2] += outer_box_thickness

if np.any(common_min >= common_max):
    raise ValueError('The two JSON bounding regions do not overlap.')

tilt_degrees = np.degrees(np.arccos(np.clip((np.trace(rotation) - 1) / 2, -1, 1)))
print(f'Scale (Brian / reference): {scale:.8f}')
print(f'Tilt angle: {tilt_degrees:.8f} degrees')
print(f'Registration RMS error: {fit_error:.3e}')
print('Common bounds in reference coordinates:', common_min, common_max)

# The STL is centered in its own coordinates, rather than already being in
# Brian JSON coordinates. Rotate it so its long original y direction is z,
# translate its minimum corner to the origin, and scale it into reference
# JSON units before cropping.
mesh = pv.read(STL_PATH)
mesh.rotate_x(90, inplace=True)
stl_min = np.asarray(mesh.bounds[::2])
stl_extent = np.asarray(mesh.bounds[1::2]) - stl_min
stl_to_reference_scale = 18.0 / min(stl_extent[0], stl_extent[1], stl_extent[2])

mesh_in_reference = mesh.copy()
mesh_in_reference.points = (mesh.points - stl_min) * stl_to_reference_scale

cropped_reference = mesh_in_reference.clip_box(
    bounds=[
        common_min[0], common_max[0],
        common_min[1], common_max[1],
        common_min[2], common_max[2],
    ],
    invert=False,
)
cropped_mesh = cropped_reference.copy()
cropped_mesh.points = (
    cropped_reference.points / stl_to_reference_scale + stl_min
)

print(f'STL-to-reference scale: {stl_to_reference_scale:.8f}')
print('Cropped STL bounds:', cropped_mesh.bounds)

plotter = pv.Plotter()
plotter.add_mesh(cropped_mesh, color='silver', smooth_shading=True)
plotter.add_axes()
surface_mesh = cropped_mesh.extract_surface()

surface_mesh.save("0.5_skew.stl")

plotter.camera.zoom('tight')
plotter.show()