"""Score expected lattice struts against a registered CT volume.

This is a model-free baseline.  It samples CT intensity along every expected
JSON centerline, searches a small neighborhood to tolerate registration error,
and flags centerlines with weak or interrupted material support.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pyvista as pv
import tifffile
import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
STEM = "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices"
DEFAULT_TIFF = ROOT / "data" / "missing_struts" / "tif_stacks" / f"{STEM}.tif"
DEFAULT_JSON = ROOT / "data" / "missing_struts" / "registered_jsons" / f"{STEM}.json"
DEFAULT_OUTPUT = ROOT / "data" / "missing_struts" / "defect_analysis"


def otsu_threshold(sample: np.ndarray) -> float:
    """Calculate an Otsu threshold from a representative integer sample."""
    values = np.asarray(sample).ravel()
    lo, hi = np.percentile(values, [0.2, 99.8])
    hist, edges = np.histogram(values, bins=1024, range=(lo, hi))
    centers = (edges[:-1] + edges[1:]) / 2
    weight0 = np.cumsum(hist)
    weight1 = np.cumsum(hist[::-1])[::-1]
    mean0 = np.cumsum(hist * centers) / np.maximum(weight0, 1)
    mean1 = (
        np.cumsum((hist * centers)[::-1]) / np.maximum(weight1[::-1], 1)
    )[::-1]
    variance = weight0[:-1] * weight1[1:] * (mean0[:-1] - mean1[1:]) ** 2
    return float(centers[int(np.argmax(variance))])


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


def longest_false_run(values: np.ndarray) -> int:
    best = current = 0
    for value in values:
        if value:
            current = 0
        else:
            current += 1
            best = max(best, current)
    return best


def score_struts(
    volume: np.ndarray,
    junctions: dict[int, np.ndarray],
    struts: list[dict],
    threshold: float,
    samples_per_strut: int,
    search_radius: int,
) -> list[dict]:
    """Return CT support and gap measurements for every expected strut."""
    offsets_xyz = sphere_offsets(search_radius)[:, [2, 1, 0]]
    t = np.linspace(0.12, 0.88, samples_per_strut)
    zmax, ymax, xmax = np.asarray(volume.shape) - 1
    results: list[dict] = []

    for strut in struts:
        p0 = junctions[int(strut["junction0"])]
        p1 = junctions[int(strut["junction1"])]
        points_xyz = p0[None, :] + t[:, None] * (p1 - p0)[None, :]
        centers_zyx = np.rint(points_xyz[:, [2, 1, 0]]).astype(np.int32)
        indices = centers_zyx[:, None, :] + offsets_xyz[None, :, :]
        indices[..., 0] = np.clip(indices[..., 0], 0, zmax)
        indices[..., 1] = np.clip(indices[..., 1], 0, ymax)
        indices[..., 2] = np.clip(indices[..., 2], 0, xmax)
        local = volume[indices[..., 0], indices[..., 1], indices[..., 2]]
        profile = np.max(local, axis=1).astype(float)
        supported = profile >= threshold
        support_fraction = float(np.mean(supported))
        gap_fraction = longest_false_run(supported) / samples_per_strut
        normalized_mean = float(np.mean(profile) / max(threshold, 1.0))
        continuity_score = float(
            np.clip(0.65 * support_fraction + 0.35 * min(normalized_mean, 1.0), 0, 1)
        )
        results.append(
            {
                "strut_id": int(strut["id"]),
                "junction0": int(strut["junction0"]),
                "junction1": int(strut["junction1"]),
                "support_fraction": support_fraction,
                "longest_gap_fraction": float(gap_fraction),
                "mean_local_max": float(np.mean(profile)),
                "min_local_max": float(np.min(profile)),
                "profile_min_to_mean": float(np.min(profile) / max(np.mean(profile), 1.0)),
                "continuity_score": continuity_score,
                "midpoint_xyz_voxels": ((p0 + p1) / 2.0).tolist(),
                "start_xyz_voxels": p0.tolist(),
                "end_xyz_voxels": p1.tolist(),
            }
        )
    return results


def assign_labels(results: list[dict], candidate_fraction: float, spatial_bins: int = 18) -> None:
    """Spatially normalize CT intensity, then assign rank-based screening labels."""
    midpoints = np.asarray([row["midpoint_xyz_voxels"] for row in results])
    means = np.asarray([row["mean_local_max"] for row in results])
    lower = midpoints.min(axis=0)
    span = np.maximum(np.ptp(midpoints, axis=0), 1.0)
    bins = np.minimum(
        ((midpoints - lower) / span * spatial_bins).astype(int), spatial_bins - 1
    )
    global_median = float(np.median(means))
    axis_factors: list[np.ndarray] = []
    for axis in range(3):
        factors = np.ones(spatial_bins, dtype=float)
        for index in range(spatial_bins):
            selected = means[bins[:, axis] == index]
            if selected.size:
                factors[index] = np.median(selected) / max(global_median, 1.0)
        axis_factors.append(np.clip(factors, 0.55, 1.45))
    for row, key in zip(results, bins, strict=True):
        baseline = global_median * float(
            axis_factors[0][key[0]] * axis_factors[1][key[1]] * axis_factors[2][key[2]]
        )
        relative = row["mean_local_max"] / max(baseline, 1.0)
        internal_drop = 1.0 - min(row["profile_min_to_mean"], 1.0)
        row["local_baseline_intensity"] = baseline
        row["relative_local_intensity"] = float(relative)
        row["defect_score"] = float(
            np.clip(0.78 * (1.0 - relative) + 0.22 * internal_drop, 0.0, 1.0)
        )
    n_candidate = max(1, round(len(results) * candidate_fraction))
    n_suspect = max(n_candidate + 1, round(len(results) * candidate_fraction * 3))
    ranked = sorted(
        results,
        key=lambda row: (-row["defect_score"], row["relative_local_intensity"]),
    )
    for rank, row in enumerate(ranked, start=1):
        row["rank_weakest_first"] = rank
        if rank <= n_candidate:
            row["label"] = "candidate_defect"
        elif rank <= n_suspect:
            row["label"] = "suspect"
        else:
            row["label"] = "supported"


def save_tables(results: list[dict], output_dir: Path, metadata: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_fields = [
        "strut_id",
        "junction0",
        "junction1",
        "label",
        "rank_weakest_first",
        "continuity_score",
        "defect_score",
        "relative_local_intensity",
        "local_baseline_intensity",
        "support_fraction",
        "longest_gap_fraction",
        "mean_local_max",
        "min_local_max",
    ]
    with (output_dir / "strut_defect_scores.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda row: row["strut_id"]))
    (output_dir / "strut_defect_results.json").write_text(
        json.dumps({"metadata": metadata, "struts": results}, indent=2),
        encoding="utf-8",
    )


def graph_mesh(
    junctions: dict[int, np.ndarray], struts: list[dict], results: list[dict], spacing_mm: float
) -> pv.PolyData:
    points: list[np.ndarray] = []
    lines: list[list[int]] = []
    for strut in struts:
        first = len(points)
        points.extend(
            [
                junctions[int(strut["junction0"])] * spacing_mm,
                junctions[int(strut["junction1"])] * spacing_mm,
            ]
        )
        lines.append([2, first, first + 1])
    mesh = pv.PolyData()
    mesh.points = np.asarray(points)
    mesh.lines = np.asarray(lines).ravel()
    by_id = {row["strut_id"]: row for row in results}
    mesh.cell_data["defect_score"] = np.asarray(
        [by_id[int(strut["id"])]["defect_score"] for strut in struts]
    )
    mesh.cell_data["defect_class"] = np.asarray(
        [
            {"supported": 0, "suspect": 1, "candidate_defect": 2}[
                by_id[int(strut["id"])]["label"]
            ]
            for strut in struts
        ],
        dtype=np.uint8,
    )
    mesh.cell_data["strut_id"] = np.asarray([int(s["id"]) for s in struts])
    return mesh


def render_results(mesh: pv.PolyData, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    mesh.save(output_dir / "strut_defect_graph.vtp")
    classes = mesh.cell_data["defect_class"]
    supported = mesh.extract_cells(classes == 0)
    suspects = mesh.extract_cells(classes == 1)
    candidates = mesh.extract_cells(classes == 2)

    for name, camera in (("view_a", (30, 45)), ("view_b", (60, 45))):
        plotter = pv.Plotter(off_screen=True, window_size=(1500, 1150))
        plotter.set_background("#f6f8fa")
        plotter.add_mesh(supported, color="#86a6bf", opacity=0.16, line_width=1)
        plotter.add_mesh(suspects, color="#e5a52a", opacity=0.85, line_width=3)
        plotter.add_mesh(candidates, color="#c83232", opacity=1.0, line_width=6)
        plotter.add_legend(
            [["Candidate defect", "#c83232"], ["Suspect", "#e5a52a"], ["Supported", "#86a6bf"]],
            bcolor="#ffffff",
            face=None,
            size=(0.18, 0.13),
            loc="upper right",
        )
        plotter.add_axes(xlabel="X", ylabel="Y", zlabel="Z")
        plotter.show_bounds(
            xtitle="X (mm)", ytitle="Y (mm)", ztitle="Z (mm)", grid="back", color="#405060"
        )
        plotter.camera_position = "iso"
        plotter.camera.elevation = camera[0] - 30
        plotter.camera.azimuth = camera[1] - 45
        plotter.camera.zoom(1.05)
        plotter.show(screenshot=str(output_dir / f"defective_struts_{name}.png"), auto_close=True)


def render_ct_evidence(
    volume: np.ndarray, results: list[dict], output_dir: Path, count: int = 6, margin: int = 9
) -> None:
    """Overlay the weakest expected centerlines on local CT maximum projections."""
    selected = sorted(results, key=lambda row: row["rank_weakest_first"])[:count]
    fig, axes = plt.subplots(2, 3, figsize=(14, 9), constrained_layout=True)
    for axis_plot, row in zip(axes.ravel(), selected, strict=True):
        p0 = np.asarray(row["start_xyz_voxels"])
        p1 = np.asarray(row["end_xyz_voxels"])
        lo = np.maximum(np.floor(np.minimum(p0, p1) - margin).astype(int), 0)
        hi = np.minimum(
            np.ceil(np.maximum(p0, p1) + margin).astype(int) + 1,
            np.asarray(volume.shape)[[2, 1, 0]],
        )
        crop = volume[lo[2] : hi[2], lo[1] : hi[1], lo[0] : hi[0]]
        project_xyz_axis = int(np.argmin(np.abs(p1 - p0)))
        array_axis = {0: 2, 1: 1, 2: 0}[project_xyz_axis]
        projection = np.max(crop, axis=array_axis)
        low, high = np.percentile(projection, [2, 99.5])
        axis_plot.imshow(projection, cmap="gray", origin="lower", vmin=low, vmax=high)
        if project_xyz_axis == 2:  # XY view
            u, v = (p0[0] - lo[0], p1[0] - lo[0]), (p0[1] - lo[1], p1[1] - lo[1])
            view = "XY"
        elif project_xyz_axis == 1:  # XZ view
            u, v = (p0[0] - lo[0], p1[0] - lo[0]), (p0[2] - lo[2], p1[2] - lo[2])
            view = "XZ"
        else:  # YZ view
            u, v = (p0[1] - lo[1], p1[1] - lo[1]), (p0[2] - lo[2], p1[2] - lo[2])
            view = "YZ"
        axis_plot.plot(u, v, color="#ef3038", linewidth=2.2)
        axis_plot.scatter(u, v, color="#ef3038", s=18)
        axis_plot.set_title(
            f"Rank {row['rank_weakest_first']} · strut {row['strut_id']} · {view} projection\n"
            f"local intensity ratio {row['relative_local_intensity']:.2f}"
        )
        axis_plot.set_xticks([])
        axis_plot.set_yticks([])
    fig.suptitle("Local CT evidence: expected centerline shown in red", fontsize=16)
    fig.savefig(output_dir / "top_candidate_ct_evidence.png", dpi=170)
    plt.close(fig)


def write_report(output_dir: Path, metadata: dict, results: list[dict]) -> None:
    counts = {label: sum(row["label"] == label for row in results) for label in (
        "candidate_defect", "suspect", "supported"
    )}
    weakest = sorted(results, key=lambda row: row["rank_weakest_first"])[:15]
    rows = "\n".join(
        f"| {r['rank_weakest_first']} | {r['strut_id']} | {r['defect_score']:.3f} | "
        f"{r['relative_local_intensity']:.3f} | {r['profile_min_to_mean']:.3f} |"
        for r in weakest
    )
    report = f"""# Registered CT strut-defect screening

## Summary

| Metric | Value |
|---|---:|
| TIFF shape (Z × Y × X) | {metadata['volume_shape']} |
| Voxel spacing | {metadata['voxel_spacing_um']} µm isotropic |
| Expected JSON struts | {len(results):,} |
| Otsu material threshold | {metadata['otsu_threshold']:.1f} |
| Candidate defects | {counts['candidate_defect']:,} |
| Suspects | {counts['suspect']:,} |
| Supported | {counts['supported']:,} |

The red and yellow labels are **screening results, not ground truth**. The method searches for CT
material near each registered ideal centerline and normalizes each measurement against nearby
struts to reduce spatial CT intensity bias. Candidate defects are the weakest
{metadata['candidate_fraction']:.2%} of expected struts; suspects are the next weakest group.

## 3D views

![Defect view A](defective_struts_view_a.png)

![Defect view B](defective_struts_view_b.png)

## Local CT evidence

The red segment is the expected registered centerline. A dark or unsupported path is consistent
with a missing strut, while a bright continuous path argues against the candidate.

![Top candidate CT evidence](top_candidate_ct_evidence.png)

## Fifteen weakest expected struts

| Rank | Strut ID | Defect score | Intensity / local baseline | Minimum / mean profile |
|---:|---:|---:|---:|---:|
{rows}

## Interpretation and next validation

- Low intensity relative to nearby struts is consistent with a missing strut.
- A deep internal intensity drop is consistent with a broken or disconnected strut.
- Misregistration, CT artifacts, and centerline displacement can create false positives.
- Confirm candidates by inspecting local orthogonal CT slices or by comparing against a manually
  labeled subset. A learned model is not required until this baseline has been validated.
"""
    (output_dir / "DEFECT_SCREENING_REPORT.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiff", type=Path, default=DEFAULT_TIFF)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--voxel-spacing-um", type=float, default=58.09)
    parser.add_argument("--samples-per-strut", type=int, default=31)
    parser.add_argument("--search-radius", type=int, default=2)
    parser.add_argument(
        "--candidate-fraction",
        type=float,
        default=0.005,
        help="Fraction of weakest struts highlighted red (0.005 matches the nominal 0.5%% design)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = json.loads(args.json.read_text(encoding="utf-8"))
    junctions = {
        int(junction["id"]): np.asarray(junction["position"], dtype=float)
        for junction in data["junctions"]
    }
    volume = tifffile.memmap(args.tiff)
    threshold = otsu_threshold(volume[::8, ::8, ::8])
    results = score_struts(
        volume,
        junctions,
        data["struts"],
        threshold,
        args.samples_per_strut,
        args.search_radius,
    )
    assign_labels(results, args.candidate_fraction)
    metadata = {
        "source_tiff": str(args.tiff),
        "source_json": str(args.json),
        "volume_shape": " × ".join(map(str, volume.shape)),
        "voxel_spacing_um": args.voxel_spacing_um,
        "otsu_threshold": threshold,
        "samples_per_strut": args.samples_per_strut,
        "search_radius_voxels": args.search_radius,
        "candidate_fraction": args.candidate_fraction,
        "coordinate_mapping": "JSON (X,Y,Z) -> TIFF [Z,Y,X]",
    }
    save_tables(results, args.output_dir, metadata)
    mesh = graph_mesh(junctions, data["struts"], results, args.voxel_spacing_um / 1000.0)
    render_results(mesh, args.output_dir)
    render_ct_evidence(volume, results, args.output_dir)
    write_report(args.output_dir, metadata, results)
    print(f"Analyzed {len(results):,} expected struts")
    print(f"Otsu threshold: {threshold:.1f}")
    print(f"Outputs: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
