"""Recompute registered-strut occupancy with triangle thresholding.

The JSON coordinates are expected to already be registered in TIFF voxel
coordinates as (X, Y, Z).  In addition to the original centerline occupancy,
this script measures foreground fill in a 7.3-voxel-diameter disk normal to
each design edge.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
import numpy as np
import tifffile
from skimage.filters import threshold_triangle

matplotlib.use("Agg")
from matplotlib import pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
STEM = "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices"
DEFAULT_TIFF = ROOT / "data" / "missing_struts" / "tif_stacks" / f"{STEM}.tif"
DEFAULT_JSON = ROOT / "data" / "missing_struts" / "registered_jsons" / f"{STEM}.json"
DEFAULT_OUTPUT = ROOT / "data" / "missing_struts" / "occupancy_qa"


def perpendicular_basis(direction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    unit = direction / np.linalg.norm(direction)
    reference = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(unit, reference))) > 0.9:
        reference = np.array([0.0, 1.0, 0.0])
    first = np.cross(unit, reference)
    first /= np.linalg.norm(first)
    second = np.cross(unit, first)
    return first, second


def disk_offsets(direction: np.ndarray, radius: float) -> np.ndarray:
    first, second = perpendicular_basis(direction)
    limit = int(np.ceil(radius))
    grid = np.arange(-limit, limit + 1, dtype=float)
    aa, bb = np.meshgrid(grid, grid, indexing="ij")
    keep = aa * aa + bb * bb <= radius * radius
    return aa[keep, None] * first[None, :] + bb[keep, None] * second[None, :]


def score_edges(
    volume: np.ndarray,
    junctions: dict[int, np.ndarray],
    struts: list[dict],
    threshold: float,
    diameter: float,
    samples_per_strut: int,
) -> list[dict]:
    t = np.linspace(0.12, 0.88, samples_per_strut)
    upper_zyx = np.asarray(volume.shape) - 1
    rows: list[dict] = []

    for strut in struts:
        p0 = junctions[int(strut["junction0"])]
        p1 = junctions[int(strut["junction1"])]
        direction = p1 - p0
        centers_xyz = p0[None, :] + t[:, None] * direction[None, :]

        center_zyx = np.rint(centers_xyz[:, [2, 1, 0]]).astype(np.int32)
        center_zyx = np.clip(center_zyx, 0, upper_zyx)
        center_values = volume[center_zyx[:, 0], center_zyx[:, 1], center_zyx[:, 2]]
        center_foreground = center_values >= threshold

        offsets_xyz = disk_offsets(direction, diameter / 2.0)
        sample_xyz = centers_xyz[:, None, :] + offsets_xyz[None, :, :]
        sample_zyx = np.rint(sample_xyz[..., [2, 1, 0]]).astype(np.int32)
        sample_zyx = np.clip(sample_zyx, 0, upper_zyx)
        values = volume[sample_zyx[..., 0], sample_zyx[..., 1], sample_zyx[..., 2]]
        cross_section_fill = np.mean(values >= threshold, axis=1)

        rows.append(
            {
                "strut_id": int(strut["id"]),
                "junction0": int(strut["junction0"]),
                "junction1": int(strut["junction1"]),
                "centerline_occupancy": float(np.mean(center_foreground)),
                "tube_fill_occupancy": float(np.mean(cross_section_fill)),
                "cross_sections_with_material": float(np.mean(cross_section_fill > 0.0)),
                "minimum_cross_section_fill": float(np.min(cross_section_fill)),
                "edge_length_voxels": float(np.linalg.norm(direction)),
            }
        )
    return rows


def summarize(values: np.ndarray) -> dict[str, float]:
    quantiles = np.quantile(values, [0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1.0])
    names = ["min", "q01", "q05", "q25", "median", "q75", "q95", "q99", "max"]
    result = {name: float(value) for name, value in zip(names, quantiles, strict=True)}
    result["fraction_ge_0_8"] = float(np.mean(values >= 0.8))
    result["fraction_ge_0_9"] = float(np.mean(values >= 0.9))
    result["fraction_lt_0_3"] = float(np.mean(values < 0.3))
    result["fraction_lt_0_5"] = float(np.mean(values < 0.5))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiff", type=Path, default=DEFAULT_TIFF)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--diameter-voxels", type=float, default=7.3)
    parser.add_argument("--samples-per-strut", type=int, default=31)
    args = parser.parse_args()

    data = json.loads(args.json.read_text(encoding="utf-8"))
    junctions = {
        int(item["id"]): np.asarray(item["position"], dtype=float)
        for item in data["junctions"]
    }
    struts = data["struts"]
    volume = tifffile.memmap(args.tiff)
    threshold_sample = np.asarray(volume[::8, ::8, ::8]).ravel()
    triangle = float(threshold_triangle(threshold_sample))

    rows = score_edges(
        volume,
        junctions,
        struts,
        triangle,
        args.diameter_voxels,
        args.samples_per_strut,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = args.output_dir / "occupancy_7p3_triangle.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    center = np.asarray([row["centerline_occupancy"] for row in rows])
    tube = np.asarray([row["tube_fill_occupancy"] for row in rows])
    presence = np.asarray([row["cross_sections_with_material"] for row in rows])
    summary = {
        "source_tiff": str(args.tiff),
        "source_json": str(args.json),
        "volume_shape_zyx": list(map(int, volume.shape)),
        "triangle_threshold": triangle,
        "diameter_voxels": args.diameter_voxels,
        "samples_per_strut": args.samples_per_strut,
        "json_junction_count": len(junctions),
        "json_strut_count": len(struts),
        "unique_unordered_edge_count": len(
            {
                tuple(sorted((int(item["junction0"]), int(item["junction1"]))))
                for item in struts
            }
        ),
        "centerline_occupancy": summarize(center),
        "tube_fill_occupancy": summarize(tube),
        "cross_sections_with_material": summarize(presence),
    }
    summary_path = args.output_dir / "occupancy_7p3_triangle_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    bins = np.linspace(0.0, 1.0, 51)
    figure, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    axes[0].hist(center, bins=bins, color="#2878b5", edgecolor="white")
    axes[0].set_title("Centerline occupancy")
    axes[1].hist(tube, bins=bins, color="#e07a2d", edgecolor="white")
    axes[1].set_title("7.3-voxel design-tube fill")
    for axis in axes:
        axis.set_xlim(0, 1)
        axis.set_xlabel("Foreground fraction")
        axis.set_ylabel("JSON edges")
        axis.grid(axis="y", alpha=0.2)
    figure.suptitle(
        f"Triangle threshold = {triangle:.1f}; {len(struts):,} JSON edges",
        fontsize=13,
    )
    plot_path = args.output_dir / "occupancy_histogram_7p3_triangle.png"
    figure.savefig(plot_path, dpi=180)
    plt.close(figure)

    print(json.dumps(summary, indent=2))
    print(f"CSV: {csv_path.resolve()}")
    print(f"Histogram: {plot_path.resolve()}")


if __name__ == "__main__":
    main()
