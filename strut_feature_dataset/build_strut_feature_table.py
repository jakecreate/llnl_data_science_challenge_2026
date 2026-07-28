"""Build one-row-per-strut CSV datasets from registered lattice geometry and CT scores."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STEM = "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices"
DEFAULT_GEOMETRY = (
    ROOT / "data" / "missing_struts" / "registered_jsons" / f"{STEM}.json"
)
DEFAULT_CT_RESULTS = (
    ROOT / "data" / "missing_struts" / "defect_analysis" / "strut_defect_results.json"
)
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent


IDENTIFIER_FIELDS = [
    "specimen_id",
    "strut_id",
    "junction0_id",
    "junction1_id",
    "unit_cell_id",
    "unit_cell_i",
    "unit_cell_j",
    "unit_cell_k",
    "unit_cell_edge_idx",
]

DESIGN_FIELDS = IDENTIFIER_FIELDS + [
    "start_x_vox",
    "start_y_vox",
    "start_z_vox",
    "end_x_vox",
    "end_y_vox",
    "end_z_vox",
    "midpoint_x_vox",
    "midpoint_y_vox",
    "midpoint_z_vox",
    "start_x_mm",
    "start_y_mm",
    "start_z_mm",
    "end_x_mm",
    "end_y_mm",
    "end_z_mm",
    "midpoint_x_mm",
    "midpoint_y_mm",
    "midpoint_z_mm",
    "delta_x_mm",
    "delta_y_mm",
    "delta_z_mm",
    "length_mm",
    "nominal_diameter_mm",
    "expected_diameter_voxels",
    "unit_vector_x",
    "unit_vector_y",
    "unit_vector_z",
    "absolute_unit_x",
    "absolute_unit_y",
    "absolute_unit_z",
    "angle_to_build_z_deg",
    "elevation_from_xy_deg",
    "azimuth_xy_deg",
    "orientation_class",
    "junction0_degree",
    "junction1_degree",
    "minimum_endpoint_degree",
    "maximum_endpoint_degree",
    "mean_endpoint_degree",
    "neighboring_strut_count",
    "endpoint_on_boundary_count",
    "minimum_midpoint_boundary_distance_mm",
    "near_boundary_one_cell",
    "cross_section_area_mm2",
    "second_moment_area_mm4",
    "nominal_strut_volume_mm3",
    "nominal_lateral_surface_mm2",
    "slenderness_length_over_diameter",
    "slenderness_length_over_radius_gyration",
    "axial_geometry_proxy_area_over_length_mm",
    "bending_geometry_proxy_i_over_length_cubed_mm",
    "euler_buckling_proxy_pi2_i_over_length2_mm2",
]

CT_FIELDS = [
    "ct_features_available",
    "ct_support_fraction",
    "ct_longest_gap_fraction",
    "ct_mean_local_max",
    "ct_min_local_max",
    "ct_profile_min_to_mean",
    "ct_continuity_score",
    "ct_local_baseline_intensity",
    "ct_relative_local_intensity",
    "ct_defect_score",
    "ct_rank_weakest_first",
    "ct_rank_percentile",
    "ct_screening_label",
    "ct_severity_layer",
]

COMBINED_FIELDS = DESIGN_FIELDS + CT_FIELDS


def rounded(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def vector_subtract(first: list[float], second: list[float]) -> list[float]:
    return [first[index] - second[index] for index in range(3)]


def vector_length(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def severity_from_rank(rank: int, total: int) -> str:
    if rank <= max(1, round(total * 0.001)):
        return "critical"
    if rank <= max(1, round(total * 0.005)):
        return "high"
    if rank <= max(1, round(total * 0.015)):
        return "moderate"
    if rank <= max(1, round(total * 0.030)):
        return "watch"
    return "supported"


def orientation_class(angle_to_z: float) -> str:
    if angle_to_z <= 15.0:
        return "near_vertical"
    if angle_to_z >= 75.0:
        return "near_horizontal"
    return "inclined"


def build_cell_lookup(unit_cells: list[dict]) -> dict[int, dict]:
    lookup: dict[int, dict] = {}
    for cell in unit_cells:
        for strut_id in cell["struts"]:
            lookup[int(strut_id)] = {
                "unit_cell_id": int(cell["id"]),
                "indices": list(cell["indices"]),
            }
    return lookup


def load_ct_lookup(path: Path | None) -> tuple[dict[int, dict], int]:
    if path is None or not path.exists():
        return {}, 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["struts"]
    return {int(row["strut_id"]): row for row in rows}, len(rows)


def design_feature_row(
    specimen_id: str,
    strut: dict,
    junctions: dict[int, dict],
    degrees: Counter,
    cell_lookup: dict[int, dict],
    bounds_min: list[float],
    bounds_max: list[float],
    spacing_mm: float,
    nominal_diameter_mm: float,
    unit_cell_size_mm: float,
) -> dict:
    strut_id = int(strut["id"])
    junction0_id = int(strut["junction0"])
    junction1_id = int(strut["junction1"])
    start_vox = [float(value) for value in junctions[junction0_id]["position"]]
    end_vox = [float(value) for value in junctions[junction1_id]["position"]]
    midpoint_vox = [(start_vox[index] + end_vox[index]) / 2.0 for index in range(3)]
    start_mm = [value * spacing_mm for value in start_vox]
    end_mm = [value * spacing_mm for value in end_vox]
    midpoint_mm = [value * spacing_mm for value in midpoint_vox]
    delta_mm = vector_subtract(end_mm, start_mm)
    length_mm = vector_length(delta_mm)
    unit = [value / length_mm for value in delta_mm]
    absolute_unit = [abs(value) for value in unit]
    angle_to_z = math.degrees(math.acos(max(-1.0, min(1.0, absolute_unit[2]))))
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, absolute_unit[2]))))
    azimuth = math.degrees(math.atan2(unit[1], unit[0])) % 360.0

    degree0 = degrees[junction0_id]
    degree1 = degrees[junction1_id]
    bound_tolerance_vox = 1.0
    endpoint_on_boundary_count = sum(
        any(
            abs(point[axis] - bounds_min[axis]) <= bound_tolerance_vox
            or abs(point[axis] - bounds_max[axis]) <= bound_tolerance_vox
            for axis in range(3)
        )
        for point in (start_vox, end_vox)
    )
    midpoint_boundary_distance_mm = min(
        min(midpoint_vox[axis] - bounds_min[axis], bounds_max[axis] - midpoint_vox[axis])
        * spacing_mm
        for axis in range(3)
    )

    radius = nominal_diameter_mm / 2.0
    area = math.pi * radius**2
    second_moment = math.pi * nominal_diameter_mm**4 / 64.0
    volume = area * length_mm
    lateral_surface = math.pi * nominal_diameter_mm * length_mm
    cell = cell_lookup.get(strut_id)
    cell_indices = cell["indices"] if cell else ["", "", ""]

    row = {
        "specimen_id": specimen_id,
        "strut_id": strut_id,
        "junction0_id": junction0_id,
        "junction1_id": junction1_id,
        "unit_cell_id": cell["unit_cell_id"] if cell else "",
        "unit_cell_i": cell_indices[0],
        "unit_cell_j": cell_indices[1],
        "unit_cell_k": cell_indices[2],
        "unit_cell_edge_idx": strut.get("unit_cell_edge_idx", ""),
        "junction0_degree": degree0,
        "junction1_degree": degree1,
        "minimum_endpoint_degree": min(degree0, degree1),
        "maximum_endpoint_degree": max(degree0, degree1),
        "mean_endpoint_degree": rounded((degree0 + degree1) / 2.0),
        "neighboring_strut_count": degree0 + degree1 - 2,
        "endpoint_on_boundary_count": endpoint_on_boundary_count,
        "minimum_midpoint_boundary_distance_mm": rounded(midpoint_boundary_distance_mm),
        "near_boundary_one_cell": int(midpoint_boundary_distance_mm <= unit_cell_size_mm),
        "length_mm": rounded(length_mm),
        "nominal_diameter_mm": rounded(nominal_diameter_mm),
        "expected_diameter_voxels": rounded(nominal_diameter_mm / spacing_mm),
        "angle_to_build_z_deg": rounded(angle_to_z),
        "elevation_from_xy_deg": rounded(elevation),
        "azimuth_xy_deg": rounded(azimuth),
        "orientation_class": orientation_class(angle_to_z),
        "cross_section_area_mm2": rounded(area),
        "second_moment_area_mm4": rounded(second_moment, 9),
        "nominal_strut_volume_mm3": rounded(volume),
        "nominal_lateral_surface_mm2": rounded(lateral_surface),
        "slenderness_length_over_diameter": rounded(length_mm / nominal_diameter_mm),
        "slenderness_length_over_radius_gyration": rounded(4.0 * length_mm / nominal_diameter_mm),
        "axial_geometry_proxy_area_over_length_mm": rounded(area / length_mm, 9),
        "bending_geometry_proxy_i_over_length_cubed_mm": rounded(second_moment / length_mm**3, 12),
        "euler_buckling_proxy_pi2_i_over_length2_mm2": rounded(
            math.pi**2 * second_moment / length_mm**2, 12
        ),
    }
    for prefix, values in (("start", start_vox), ("end", end_vox), ("midpoint", midpoint_vox)):
        for axis, value in zip(("x", "y", "z"), values, strict=True):
            row[f"{prefix}_{axis}_vox"] = rounded(value)
    for prefix, values in (("start", start_mm), ("end", end_mm), ("midpoint", midpoint_mm)):
        for axis, value in zip(("x", "y", "z"), values, strict=True):
            row[f"{prefix}_{axis}_mm"] = rounded(value)
    for axis, value in zip(("x", "y", "z"), delta_mm, strict=True):
        row[f"delta_{axis}_mm"] = rounded(value)
    for axis, value in zip(("x", "y", "z"), unit, strict=True):
        row[f"unit_vector_{axis}"] = rounded(value)
    for axis, value in zip(("x", "y", "z"), absolute_unit, strict=True):
        row[f"absolute_unit_{axis}"] = rounded(value)
    return row


def attach_ct_features(row: dict, ct: dict | None, ct_total: int) -> None:
    if ct is None:
        row.update({field: "" for field in CT_FIELDS})
        row["ct_features_available"] = 0
        return
    rank = int(ct["rank_weakest_first"])
    row.update(
        {
            "ct_features_available": 1,
            "ct_support_fraction": rounded(ct["support_fraction"]),
            "ct_longest_gap_fraction": rounded(ct["longest_gap_fraction"]),
            "ct_mean_local_max": rounded(ct["mean_local_max"]),
            "ct_min_local_max": rounded(ct["min_local_max"]),
            "ct_profile_min_to_mean": rounded(ct["profile_min_to_mean"]),
            "ct_continuity_score": rounded(ct["continuity_score"]),
            "ct_local_baseline_intensity": rounded(ct["local_baseline_intensity"]),
            "ct_relative_local_intensity": rounded(ct["relative_local_intensity"]),
            "ct_defect_score": rounded(ct["defect_score"]),
            "ct_rank_weakest_first": rank,
            "ct_rank_percentile": rounded(rank / max(ct_total, 1)),
            "ct_screening_label": ct["label"],
            "ct_severity_layer": severity_from_rank(rank, ct_total),
        }
    )


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry", type=Path, default=DEFAULT_GEOMETRY)
    parser.add_argument("--ct-results", type=Path, default=DEFAULT_CT_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--specimen-id", default="0.5-1")
    parser.add_argument("--voxel-spacing-um", type=float, default=58.09)
    parser.add_argument("--nominal-diameter-mm", type=float, default=0.350)
    parser.add_argument("--unit-cell-size-mm", type=float, default=4.560)
    parser.add_argument(
        "--design-only",
        action="store_true",
        help="Do not join CT screening results into the combined table",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    geometry = json.loads(args.geometry.read_text(encoding="utf-8"))
    junctions = {int(item["id"]): item for item in geometry["junctions"]}
    degrees: Counter = Counter()
    for strut in geometry["struts"]:
        degrees[int(strut["junction0"])] += 1
        degrees[int(strut["junction1"])] += 1
    positions = [item["position"] for item in geometry["junctions"]]
    bounds_min = [min(float(point[axis]) for point in positions) for axis in range(3)]
    bounds_max = [max(float(point[axis]) for point in positions) for axis in range(3)]
    cell_lookup = build_cell_lookup(geometry["unit_cells"])
    ct_path = None if args.design_only else args.ct_results
    ct_lookup, ct_total = load_ct_lookup(ct_path)
    spacing_mm = args.voxel_spacing_um / 1000.0

    rows: list[dict] = []
    for strut in geometry["struts"]:
        row = design_feature_row(
            args.specimen_id,
            strut,
            junctions,
            degrees,
            cell_lookup,
            bounds_min,
            bounds_max,
            spacing_mm,
            args.nominal_diameter_mm,
            args.unit_cell_size_mm,
        )
        attach_ct_features(row, ct_lookup.get(int(strut["id"])), ct_total)
        rows.append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "strut_design_features.csv", DESIGN_FIELDS, rows)
    write_csv(args.output_dir / "strut_features_combined.csv", COMBINED_FIELDS, rows)
    summary = {
        "specimen_id": args.specimen_id,
        "row_count": len(rows),
        "design_feature_count": len(DESIGN_FIELDS),
        "combined_feature_count": len(COMBINED_FIELDS),
        "geometry_source": str(args.geometry.resolve()),
        "ct_source": str(args.ct_results.resolve()) if ct_lookup else None,
        "voxel_spacing_um": args.voxel_spacing_um,
        "nominal_diameter_mm": args.nominal_diameter_mm,
        "unit_cell_size_mm": args.unit_cell_size_mm,
    }
    (args.output_dir / "dataset_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(rows):,} rows")
    print(f"Design columns: {len(DESIGN_FIELDS)}")
    print(f"Combined columns: {len(COMBINED_FIELDS)}")
    print(f"Output directory: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
