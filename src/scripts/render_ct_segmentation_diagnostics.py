"""Render the CT segmentation diagnostic from cached segmentation volumes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "9x9x9_octet_lattice.tif"
MASK_PATH = ROOT / "outputs" / "features" / "ct_selected_mask_ds4.tif"
DISAGREEMENT_PATH = ROOT / "outputs" / "features" / "ct_segmentation_disagreement_ds4.tif"
OUTPUT_PATH = ROOT / "outputs" / "reports" / "ct_segmentation_diagnostics.png"


def render(example_slice: int) -> None:
    """Render all spatial panels at one axis-0 analysis-grid slice."""
    raw = tifffile.memmap(DATA_PATH)
    selected_mask = tifffile.imread(MASK_PATH)
    disagreement = tifffile.imread(DISAGREEMENT_PATH)
    if selected_mask.shape != disagreement.shape:
        raise ValueError(
            f"Mask shape {selected_mask.shape} does not match disagreement shape {disagreement.shape}."
        )
    if not 0 <= example_slice < selected_mask.shape[0]:
        raise IndexError(
            f"Diagnostic axis-0 slice {example_slice} is outside the analysis volume "
            f"with {selected_mask.shape[0]} slices."
        )

    analysis_volume = np.asarray(raw[::4, ::4, ::4], dtype=np.float32)
    clip_lo, clip_hi = np.percentile(analysis_volume, [0.5, 99.5])
    normalized_slice = np.clip(
        (analysis_volume[example_slice] - clip_lo) / (clip_hi - clip_lo), 0, 1
    )
    raw_sample = np.asarray(raw[::8, ::8, ::8], dtype=np.float32)
    z_mean = np.empty(raw.shape[0], dtype=float)
    z_std = np.empty(raw.shape[0], dtype=float)
    for z_index in range(raw.shape[0]):
        plane = np.asarray(raw[z_index, ::4, ::4], dtype=np.float32)
        z_mean[z_index] = plane.mean()
        z_std[z_index] = plane.std()

    plt.rcParams.update({"figure.dpi": 120, "savefig.dpi": 160, "axes.grid": True})
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes[0, 0].imshow(normalized_slice, cmap="gray")
    axes[0, 0].set_title(f"Normalized CT, axis-0 slice {example_slice}")
    axes[0, 1].imshow(selected_mask[example_slice], cmap="gray")
    axes[0, 1].set_title(f"Selected ensemble mask, axis-0 slice {example_slice}")
    axes[0, 2].imshow(normalized_slice, cmap="gray")
    axes[0, 2].contour(
        selected_mask[example_slice], levels=[0.5], colors="lime", linewidths=0.5
    )
    axes[0, 2].set_title(f"Segmentation overlay, axis-0 slice {example_slice}")
    axes[1, 0].hist(raw_sample.ravel(), bins=128, color="steelblue")
    axes[1, 0].axvline(clip_lo, color="orange", label="clip")
    axes[1, 0].axvline(clip_hi, color="orange")
    axes[1, 0].set_title("Stratified raw histogram")
    axes[1, 0].legend()
    axes[1, 1].plot(z_mean, label="mean")
    axes[1, 1].plot(z_std, label="std")
    axes[1, 1].set_title("Raw Z-slice intensity trends")
    axes[1, 1].legend()
    axes[1, 2].imshow(disagreement[example_slice], cmap="magma", vmin=0, vmax=1)
    axes[1, 2].set_title(f"Ensemble disagreement, axis-0 slice {example_slice}")
    for axis in axes.flat:
        if axis.images:
            axis.axis("off")
    fig.tight_layout()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice", type=int, default=70, dest="example_slice")
    args = parser.parse_args()
    render(args.example_slice)


if __name__ == "__main__":
    main()
