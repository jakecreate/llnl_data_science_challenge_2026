"""Build non-temporal spatial sequences from registered lattice CT data."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STEM = "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices"
DEFAULT_FEATURES = ROOT / "strut_feature_dataset" / "strut_features_combined.csv"
DEFAULT_GEOMETRY = ROOT / "data" / "missing_struts" / "registered_jsons" / f"{STEM}.json"
DEFAULT_TIFF = ROOT / "data" / "missing_struts" / "tif_stacks" / f"{STEM}.tif"
DEFAULT_OUTPUT = HERE / "datasets"


def morton3(x: int, y: int, z: int) -> int:
    """Interleave three small integer coordinates into a locality-preserving key."""
    result = 0
    for bit in range(8):
        result |= ((x >> bit) & 1) << (3 * bit)
        result |= ((y >> bit) & 1) << (3 * bit + 1)
        result |= ((z >> bit) & 1) << (3 * bit + 2)
    return result


def sphere_offsets(radius: int) -> np.ndarray:
    grid = np.stack(
        np.meshgrid(
            np.arange(-radius, radius + 1),
            np.arange(-radius, radius + 1),
            np.arange(-radius, radius + 1),
            indexing="ij",
        ),
        axis=-1,
    ).reshape(-1, 3)
    return grid[np.sum(grid * grid, axis=1) <= radius * radius]


def longest_true_run(values: np.ndarray) -> int:
    best = current = 0
    for value in values:
        if value:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def build_strut_spatial_sequence(features: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    frame = features.copy()
    frame["spatial_morton_code"] = [
        morton3(int(i), int(j), int(k))
        for i, j, k in zip(frame.unit_cell_i, frame.unit_cell_j, frame.unit_cell_k)
    ]
    frame = frame.sort_values(
        ["unit_cell_edge_idx", "spatial_morton_code", "strut_id"]
    ).reset_index(drop=True)
    frame["sequence_position"] = frame.groupby("unit_cell_edge_idx").cumcount()
    base = datetime(2000, 1, 1)
    frame["pseudo_timestamp"] = [
        (base + timedelta(seconds=int(position))).isoformat()
        for position in frame.sequence_position
    ]
    frame["sequence_id"] = frame.unit_cell_edge_idx.map(lambda value: f"edge_{int(value):02d}")
    frame["sequence_semantics"] = "spatial_morton_order_not_time"
    frame["is_true_time_series"] = 0
    columns = [
        "sequence_id", "pseudo_timestamp", "sequence_position", "spatial_morton_code",
        "sequence_semantics", "is_true_time_series", "specimen_id", "strut_id",
        "unit_cell_i", "unit_cell_j", "unit_cell_k", "unit_cell_edge_idx",
        "midpoint_x_mm", "midpoint_y_mm", "midpoint_z_mm",
        "ct_relative_local_intensity", "ct_defect_score", "ct_support_fraction",
        "ct_longest_gap_fraction", "ct_severity_layer", "near_boundary_one_cell",
        "angle_to_build_z_deg", "mean_endpoint_degree",
    ]
    result = frame[columns]
    result.to_csv(output_dir / "strut_spatial_sequence.csv", index=False)
    return result


def build_centerline_profiles(
    features: pd.DataFrame,
    geometry_path: Path,
    tiff_path: Path,
    output_dir: Path,
    samples_per_strut: int,
    search_radius: int,
    spacing_um: float,
) -> pd.DataFrame:
    geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
    junctions = {
        int(item["id"]): np.asarray(item["position"], dtype=float)
        for item in geometry["junctions"]
    }
    feature_lookup = features.set_index("strut_id").to_dict("index")
    volume = tifffile.memmap(tiff_path)
    offsets_zyx = sphere_offsets(search_radius)
    t_values = np.linspace(0.12, 0.88, samples_per_strut)
    spacing_mm = spacing_um / 1000.0
    zmax, ymax, xmax = np.asarray(volume.shape) - 1
    profile_path = output_dir / "centerline_profiles_long.csv.gz"
    summary_rows: list[dict] = []
    headers = [
        "specimen_id", "strut_id", "sample_index", "pseudo_timestamp",
        "normalized_position", "distance_from_start_mm", "x_vox", "y_vox", "z_vox",
        "x_mm", "y_mm", "z_mm", "local_max_intensity", "relative_to_local_baseline",
        "below_80pct_local_baseline", "ct_defect_score", "ct_severity_layer",
        "sequence_semantics", "is_true_time_series",
    ]
    base = datetime(2000, 1, 1)
    with gzip.open(profile_path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for strut in geometry["struts"]:
            strut_id = int(strut["id"])
            metadata = feature_lookup[strut_id]
            start = junctions[int(strut["junction0"])]
            end = junctions[int(strut["junction1"])]
            points_xyz = start[None, :] + t_values[:, None] * (end - start)[None, :]
            centers_zyx = np.rint(points_xyz[:, [2, 1, 0]]).astype(np.int32)
            indices = centers_zyx[:, None, :] + offsets_zyx[None, :, :]
            indices[..., 0] = np.clip(indices[..., 0], 0, zmax)
            indices[..., 1] = np.clip(indices[..., 1], 0, ymax)
            indices[..., 2] = np.clip(indices[..., 2], 0, xmax)
            local = volume[indices[..., 0], indices[..., 1], indices[..., 2]]
            profile = np.max(local, axis=1).astype(float)
            baseline = max(float(metadata["ct_local_baseline_intensity"]), 1.0)
            relative = profile / baseline
            below = relative < 0.80
            length_mm = float(np.linalg.norm(end - start) * spacing_mm)
            for sample_index, (position, point, intensity, ratio, is_below) in enumerate(
                zip(t_values, points_xyz, profile, relative, below)
            ):
                writer.writerow(
                    {
                        "specimen_id": metadata["specimen_id"],
                        "strut_id": strut_id,
                        "sample_index": sample_index,
                        "pseudo_timestamp": (base + timedelta(seconds=sample_index)).isoformat(),
                        "normalized_position": round(float(position), 6),
                        "distance_from_start_mm": round(float(position * length_mm), 6),
                        "x_vox": round(float(point[0]), 5),
                        "y_vox": round(float(point[1]), 5),
                        "z_vox": round(float(point[2]), 5),
                        "x_mm": round(float(point[0] * spacing_mm), 6),
                        "y_mm": round(float(point[1] * spacing_mm), 6),
                        "z_mm": round(float(point[2] * spacing_mm), 6),
                        "local_max_intensity": round(float(intensity), 3),
                        "relative_to_local_baseline": round(float(ratio), 6),
                        "below_80pct_local_baseline": int(is_below),
                        "ct_defect_score": metadata["ct_defect_score"],
                        "ct_severity_layer": metadata["ct_severity_layer"],
                        "sequence_semantics": "position_along_strut_not_time",
                        "is_true_time_series": 0,
                    }
                )
            differences = np.diff(relative)
            summary_rows.append(
                {
                    "specimen_id": metadata["specimen_id"],
                    "strut_id": strut_id,
                    "profile_samples": samples_per_strut,
                    "profile_relative_mean": float(np.mean(relative)),
                    "profile_relative_min": float(np.min(relative)),
                    "profile_relative_std": float(np.std(relative)),
                    "profile_fraction_below_80pct": float(np.mean(below)),
                    "profile_longest_run_below_80pct": longest_true_run(below),
                    "profile_max_absolute_step": float(np.max(np.abs(differences))),
                    "profile_minimum_position": float(t_values[int(np.argmin(relative))]),
                    "ct_defect_score": metadata["ct_defect_score"],
                    "ct_severity_layer": metadata["ct_severity_layer"],
                    "sequence_semantics": "position_along_strut_not_time",
                    "is_true_time_series": 0,
                }
            )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "centerline_profile_summary.csv", index=False)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--geometry", type=Path, default=DEFAULT_GEOMETRY)
    parser.add_argument("--tiff", type=Path, default=DEFAULT_TIFF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--samples-per-strut", type=int, default=31)
    parser.add_argument("--search-radius", type=int, default=2)
    parser.add_argument("--voxel-spacing-um", type=float, default=58.09)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    features = pd.read_csv(args.features)
    spatial = build_strut_spatial_sequence(features, args.output_dir)
    profiles = build_centerline_profiles(
        features,
        args.geometry,
        args.tiff,
        args.output_dir,
        args.samples_per_strut,
        args.search_radius,
        args.voxel_spacing_um,
    )
    metadata = {
        "scientific_status": "spatial pseudo-sequences; not elapsed-time observations",
        "strut_spatial_rows": len(spatial),
        "centerline_profile_rows": len(profiles) * args.samples_per_strut,
        "centerline_profile_count": len(profiles),
        "samples_per_profile": args.samples_per_strut,
        "ordering": "Morton order within unit_cell_edge_idx",
        "voxel_spacing_um": args.voxel_spacing_um,
    }
    (args.output_dir / "dataset_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(f"Spatial strut sequence rows: {len(spatial):,}")
    print(f"Centerline sample rows: {len(profiles) * args.samples_per_strut:,}")
    print(f"Outputs: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
