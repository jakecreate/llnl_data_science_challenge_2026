import numpy as np
from stl import mesh

def signed_volume_of_triangle(p1, p2, p3):
    v321 = p3[0] * p2[1] * p1[2]
    v231 = p2[0] * p3[1] * p1[2]
    v312 = p3[0] * p1[1] * p2[2]
    v132 = p1[0] * p3[1] * p2[2]
    v213 = p2[0] * p1[1] * p3[2]
    v123 = p1[0] * p2[1] * p3[2]
    return (1.0 / 6.0) * (-v321 + v231 + v312 - v132 - v213 + v123)

def volume_of_mesh(input_filepath: str) -> float:
    stl_mesh = mesh.Mesh.from_file(input_filepath)
    volume, cog, inertia = stl_mesh.get_mass_properties()
    print(volume)
    triangles = stl_mesh.vectors
    vols = 0.0
    for t in triangles:
        vols += signed_volume_of_triangle(t[0], t[1], t[2])
    return abs(vols)

print(volume_of_mesh("data/missing_struts/stls/0.stl"))