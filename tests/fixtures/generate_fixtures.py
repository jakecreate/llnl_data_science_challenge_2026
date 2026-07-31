"""Generate small TIFF fixtures for volumetric input validation tests."""

from pathlib import Path

import numpy as np
import tifffile


FIXTURE_DIR = Path(__file__).resolve().parent
VOLUME_SHAPE = (20, 20, 20)


def create_sample_lattice() -> np.ndarray:
    """Return a binary 3D lattice made of intersecting, two-voxel struts."""
    volume = np.zeros(VOLUME_SHAPE, dtype=np.uint8)
    strut_starts = (4, 9, 14)

    for first in strut_starts:
        for second in strut_starts:
            volume[:, first : first + 2, second : second + 2] = 255
            volume[first : first + 2, :, second : second + 2] = 255
            volume[first : first + 2, second : second + 2, :] = 255

    return volume


def create_invalid_2d_image() -> np.ndarray:
    """Return a 2D checkerboard that is intentionally not a volume."""
    row, column = np.indices(VOLUME_SHAPE[1:])
    return (((row // 4 + column // 4) % 2) * 255).astype(np.uint8)


def generate_fixtures(output_dir: Path = FIXTURE_DIR) -> tuple[Path, Path]:
    """Write the valid 3D and invalid 2D TIFF fixtures."""
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_path = output_dir / "sample_lattice.tif"
    invalid_path = output_dir / "invalid_2d.tif"

    tifffile.imwrite(sample_path, create_sample_lattice(), photometric="minisblack")
    tifffile.imwrite(invalid_path, create_invalid_2d_image(), photometric="minisblack")

    return sample_path, invalid_path


if __name__ == "__main__":
    generated_paths = generate_fixtures()
    for generated_path in generated_paths:
        print(f"Generated {generated_path}")
