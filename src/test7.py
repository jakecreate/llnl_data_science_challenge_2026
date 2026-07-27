import numpy as np
import pyvista as pv

mesh = pv.read('data/missing_struts/stls/0.stl')
# xmin, xmax, ymin, ymax, zmin, zmax = mesh.bounds
# print(mesh.bounds)
# xsize = xmax - xmin
# ysize = ymax - ymin
# zsize = zmax - zmin
# print(xsize,ysize,zsize)
# print('dividing by octets:', xsize/9, ysize/11, zsize/9)

# mesh = pv.read(STL_PATH)
xmin, xmax, ymin, ymax, zmin, zmax = mesh.bounds

x_size = xmax - xmin
y_size = ymax - ymin
z_size = zmax - zmin

trim = (y_size - x_size) / 2  # amount to remove from EACH side of Y

new_ymin = ymin + trim
new_ymax = ymax - trim

cropped = mesh.clip_box(
    bounds=[xmin, xmax, new_ymin, new_ymax, zmin, zmax],
    invert=False,
)

print('Original bounds:', mesh.bounds)
print('Cropped bounds:', cropped.bounds)
print('Cropped size:', cropped.bounds[1]-cropped.bounds[0],
                        cropped.bounds[3]-cropped.bounds[2],
                        cropped.bounds[5]-cropped.bounds[4])
surface_mesh = cropped.extract_surface()
surface_mesh.save('cropped_0.stl')