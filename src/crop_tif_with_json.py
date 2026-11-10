#Created by BDM on 11/02/2026
#Crops the tif file based on the boundaries of the json

import cv2
import json
import tifffile
import numpy as np

#Input:
slice_normal = 0.5
json_file = './data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json'
tif_file = './data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif'

output_file = f'./media/output_slice_{slice_normal}.png'

with open(json_file) as f:
    data = json.load(f)

junctions = data['junctions']
struts = data['struts']

img = cv2.imread(tif_file)

xmin = min(junction["position"][0] for junction in junctions)
xmax = max(junction["position"][0] for junction in junctions)
ymin = min(junction["position"][1] for junction in junctions)
ymax = max(junction["position"][1] for junction in junctions)
print(xmin, xmax, ymin, ymax)

#Normalizing the bounds for cropping.
y_range = ymax - ymin # The area at which cropping is allowed for both the array and the tif (Where cropping outside of the range would give a solid block for the tif).

slice = slice_normal * y_range

volume = tifffile.imread(tif_file)
y = int(round(ymin + slice_normal * (ymax - ymin)))
y = np.clip(y, 0, volume.shape[1] - 1)

# y = max(int(round(slice)), 0)ergr
tif_slice = volume[:, y, :]

normalized = cv2.normalize(
    tif_slice, None, 0, 255, cv2.NORM_MINMAX
)

cv2.imwrite(output_file, normalized)