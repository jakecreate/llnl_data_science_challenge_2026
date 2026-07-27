import numpy as np
import trimesh

mesh = trimesh.load('data/missing_struts/stls/0.stl')  # uncropped, includes metal

scale_factor = 79.4 / 4.617  # json_cell_size_scalar / stl_cell_size, from your earlier numbers
cell_len_y = 4.640000430020419  # STL units, one Y-cell length

mesh.apply_scale(scale_factor)  # now both are in the same "JSON units" scale

# Compute the offset to skip the metal cell along Y (now scaled too)
y_offset = cell_len_y * scale_factor

full_min = np.array(mesh.bounds[0])
lattice_origin = full_min.copy()
lattice_origin[1] += y_offset  # shift past the metal on the low-Y end

# Translate so the TRUE LATTICE start (not the metal) sits at (0,0,0)
mesh.apply_translation(-lattice_origin)

mesh.export('model_scaled_translated_full.stl')