"""Cut the raw STL and TIFF stack to a common XZ-plane volume.

The TIFF is treated as a stack of XZ pages:

    TIFF array axis 0 -> Y/page direction
    TIFF array axis 1 -> Z/row direction
    TIFF array axis 2 -> X/column direction

Consequently, cutting on the XZ plane means clipping along Y.  The raw STL
and TIFF use different units, so this utility first maps the STL bounding box
to the TIFF index volume.  For precise physical registration, use the
registered STL produced by ``register_stl_to_ct.py`` instead.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pyvista as pv
import tifffile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STL = ROOT / "data/missing_struts/stls/0.stl"
DEFAULT_TIF = ROOT / (
    "data/missing_struts/tif_stacks/"
    "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif"
)


def inclusive_bounds_to_slices(bounds: np.ndarray, shape: tuple[int, int, int]):
    """Convert XYZ bounds to TIFF slices in (Y, Z, X) order."""
    x0, x1, y0, y1, z0, z1 = bounds
    nx, ny, nz = shape[2], shape[1], shape[0]
    x0, x1 = max(0, int(np.floor(x0))), min(nx, int(np.ceil(x1)) + 1)
    y0, y1 = max(0, int(np.floor(y0))), min(ny, int(np.ceil(y1)) + 1)
    z0, z1 = max(0, int(np.floor(z0))), min(nz, int(np.ceil(z1)) + 1)
    if x0 >= x1 or y0 >= y1 or z0 >= z1:
        raise ValueError(f"Empty crop after clipping to TIFF volume: {bounds}")
    return slice(y0, y1), slice(z0, z1), slice(x0, x1)


def cut(
    stl_path: Path,
    tif_path: Path,
    stl_output: Path,
    tif_output: Path,
    page_start: int,
    page_stop: int | None,
) -> None:
    volume = tifffile.imread(tif_path)
    if volume.ndim != 3:
        raise ValueError(f"Expected a 3D TIFF stack, got shape {volume.shape}")

    mesh = pv.read(stl_path)
    n_pages = volume.shape[0]
    page_stop = n_pages if page_stop is None else page_stop
    if not (0 <= page_start < page_stop <= n_pages):
        raise ValueError(f"Page range must satisfy 0 <= start < stop <= {n_pages}")
    cropped_volume = volume[page_start:page_stop, :, :]

    # For the raw STL, crop only in the XZ plane's normal direction (Y).
    # X/Z are retained so the cut is an XZ-plane slab selection.
    y_min, y_max = mesh.bounds[2], mesh.bounds[3]
    page_fraction_start = page_start / n_pages
    page_fraction_stop = page_stop / n_pages
    stl_y_start = y_min + page_fraction_start * (y_max - y_min)
    stl_y_stop = y_min + page_fraction_stop * (y_max - y_min)
    clipped = mesh.clip_box(
        bounds=[mesh.bounds[0], mesh.bounds[1], stl_y_start, stl_y_stop, mesh.bounds[4], mesh.bounds[5]],
        invert=False,
    ).extract_surface(algorithm="dataset_surface")

    stl_output.parent.mkdir(parents=True, exist_ok=True)
    tif_output.parent.mkdir(parents=True, exist_ok=True)
    clipped.save(stl_output)
    tifffile.imwrite(tif_output, cropped_volume)

    print(f"Input TIFF shape (Y, Z, X): {volume.shape}")
    print(f"Output TIFF shape (Y, Z, X): {cropped_volume.shape}")
    print(f"TIFF page/Y slice range: {page_start}:{page_stop}")
    print(f"STL Y slab: {stl_y_start:.6f}:{stl_y_stop:.6f}")
    print(f"STL bounds: {mesh.bounds}")
    print(f"Saved STL: {stl_output}")
    print(f"Saved TIFF: {tif_output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stl", type=Path, default=DEFAULT_STL)
    parser.add_argument("--tif", type=Path, default=DEFAULT_TIF)
    parser.add_argument("--stl-output", type=Path, default=ROOT / "cut_0.stl")
    parser.add_argument("--tif-output", type=Path, default=ROOT / "cut_brian_tran.tif")
    parser.add_argument("--page-start", type=int, default=0)
    parser.add_argument("--page-stop", type=int, default=None)
    args = parser.parse_args()
    cut(args.stl, args.tif, args.stl_output, args.tif_output, args.page_start, args.page_stop)


if __name__ == "__main__":
    main()
