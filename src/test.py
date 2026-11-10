"""Extract a normalized slice from a 3D TIFF and save it as a PNG.

Examples:
    python src/test.py 0.5
    python src/test.py 0.25 --axis y --output media/y_slice.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import tifffile


DEFAULT_TIF = Path(
    "data/missing_struts/tif_stacks/"
    "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif"
)


def get_slice(volume: np.ndarray, position: float, axis: str) -> tuple[np.ndarray, int]:
    """Return the slice at a normalized position and its integer index."""
    if volume.ndim != 3:
        raise ValueError(f"Expected a 3D TIFF, got shape {volume.shape}")
    if not 0.0 <= position <= 1.0:
        raise ValueError("position must be between 0 and 1")

    axis_number = {"z": 0, "y": 1, "x": 2}[axis]
    index = int(round(position * (volume.shape[axis_number] - 1)))
    image = np.take(volume, index, axis=axis_number)
    return image, index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "position",
        type=float,
        help="normalized slice position from 0.0 to 1.0",
    )
    parser.add_argument("--axis", choices=("z", "y", "x"), default="z")
    parser.add_argument("--input", type=Path, default=DEFAULT_TIF)
    parser.add_argument("--output", type=Path, default=Path("media/test_slice.png"))
    args = parser.parse_args()

    volume = tifffile.imread(args.input)
    image, index = get_slice(volume, args.position, args.axis)

    # Convert the source image to an 8-bit image for a viewable PNG.
    normalized = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
    normalized = normalized.astype(np.uint8)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), normalized):
        raise OSError(f"Could not write {args.output}")

    print(f"Saved {args.output} (axis={args.axis}, index={index}, shape={image.shape})")


if __name__ == "__main__":
    main()
