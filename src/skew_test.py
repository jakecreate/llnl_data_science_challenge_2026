import numpy as np
import tifffile
from scipy.ndimage import affine_transform

scan = tifffile.imread('data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif')  # shape (Z, Y, X)
threshold = 0.5
coords = np.argwhere(scan > threshold)
coords = coords - coords.mean(axis=0)

cov = np.cov(coords.T)
eigvals, eigvecs = np.linalg.eigh(cov)
R_scan = eigvecs[:, ::-1]

R_inv = R_scan.T
center = np.array(scan.shape) / 2
offset = center - R_inv @ center

deskewed = affine_transform(scan, R_inv, offset=offset, order=1, mode='constant', cval=0)
tifffile.imwrite('deskewed.tif', deskewed)

def largest_inscribed_box(volume, threshold=0):
    mask = volume > threshold
    z0, z1 = 0, mask.shape[0]
    y0, y1 = 0, mask.shape[1]
    x0, x1 = 0, mask.shape[2]

    def face_full(a0, a1, b0, b1, c0, c1, axis, idx):
        if axis == 0: sl = mask[idx, b0:b1, c0:c1]
        elif axis == 1: sl = mask[a0:a1, idx, c0:c1]
        else: sl = mask[a0:a1, b0:b1, idx]
        return sl.all()

    changed = True
    while changed:
        changed = False
        if not face_full(z0,z1,y0,y1,x0,x1,0,z0): z0 += 1; changed = True
        if not face_full(z0,z1,y0,y1,x0,x1,0,z1-1): z1 -= 1; changed = True
        if not face_full(z0,z1,y0,y1,x0,x1,1,y0): y0 += 1; changed = True
        if not face_full(z0,z1,y0,y1,x0,x1,1,y1-1): y1 -= 1; changed = True
        if not face_full(z0,z1,y0,y1,x0,x1,2,x0): x0 += 1; changed = True
        if not face_full(z0,z1,y0,y1,x0,x1,2,x1-1): x1 -= 1; changed = True

    return volume[z0:z1, y0:y1, x0:x1]

cropped = largest_inscribed_box(deskewed)
tifffile.imwrite('cropped_cube.tif', cropped)