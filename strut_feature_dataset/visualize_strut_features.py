"""Generate an exploratory visualization atlas for the one-row-per-strut dataset."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE / "strut_features_combined.csv"
DEFAULT_OUTPUT = HERE / "visualizations"

SEVERITY_ORDER = ["supported", "watch", "moderate", "high", "critical"]
SEVERITY_COLORS = {
    "supported": "#7fa5bd",
    "watch": "#55a7cf",
    "moderate": "#e0b13c",
    "high": "#ef7d32",
    "critical": "#ce2e32",
}
DEFECT_CMAP = LinearSegmentedColormap.from_list(
    "defect", ["#d8e5ed", "#e7b83f", "#e87532", "#bd252d"]
)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def numeric(rows: list[dict[str, str]], field: str) -> np.ndarray:
    return np.asarray([float(row[field]) if row[field] else np.nan for row in rows])


def categorical(rows: list[dict[str, str]], field: str) -> np.ndarray:
    return np.asarray([row[field] for row in rows], dtype=object)


def display_name(field: str) -> str:
    return field.removeprefix("ct_").replace("minimum_midpoint_", "").replace("_", " ")


def save(fig: plt.Figure, output_dir: Path, filename: str) -> str:
    path = output_dir / filename
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return filename


def style_axis(axis: plt.Axes, title: str, xlabel: str = "", ylabel: str = "") -> None:
    axis.set_title(title, loc="left", fontweight="bold")
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.18, linewidth=0.7)


def severity_counts(rows: list[dict[str, str]], output: Path) -> str:
    values = categorical(rows, "ct_severity_layer")
    counts = [int(np.sum(values == level)) for level in SEVERITY_ORDER]
    fig, axis = plt.subplots(figsize=(9, 5.5))
    bars = axis.bar(SEVERITY_ORDER, counts, color=[SEVERITY_COLORS[x] for x in SEVERITY_ORDER])
    axis.bar_label(bars, labels=[f"{count:,}" for count in counts], padding=3)
    style_axis(axis, "Struts by CT screening severity", ylabel="Strut count")
    return save(fig, output, "01_severity_counts.png")


def defect_distribution(rows: list[dict[str, str]], output: Path) -> str:
    score = numeric(rows, "ct_defect_score")
    fig, axis = plt.subplots(figsize=(9, 5.5))
    axis.hist(score, bins=70, color="#ce6734", alpha=0.88)
    for percentile in (97, 98.5, 99.5, 99.9):
        value = float(np.percentile(score, percentile))
        axis.axvline(value, color="#384b5b", alpha=0.6, linewidth=1)
        axis.text(value, axis.get_ylim()[1] * 0.88, f"p{percentile:g}", rotation=90, va="top")
    style_axis(axis, "Distribution of spatially normalized defect scores", "Defect score", "Struts")
    return save(fig, output, "02_defect_score_distribution.png")


def intensity_distribution(rows: list[dict[str, str]], output: Path) -> str:
    ratio = numeric(rows, "ct_relative_local_intensity")
    severity = categorical(rows, "ct_severity_layer")
    fig, axis = plt.subplots(figsize=(9, 5.5))
    for level in SEVERITY_ORDER:
        selected = ratio[severity == level]
        axis.hist(selected, bins=55, density=True, histtype="step", linewidth=2, color=SEVERITY_COLORS[level], label=level.title())
    axis.legend(frameon=False)
    style_axis(axis, "CT intensity relative to nearby struts", "Local intensity ratio", "Density")
    return save(fig, output, "03_intensity_ratio_by_severity.png")


def support_gap(rows: list[dict[str, str]], output: Path) -> str:
    support = numeric(rows, "ct_support_fraction")
    gap = numeric(rows, "ct_longest_gap_fraction")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].hist(support, bins=32, color="#4f91b8")
    axes[1].hist(gap, bins=32, color="#d98932")
    style_axis(axes[0], "Centerline samples with CT support", "Support fraction", "Struts")
    style_axis(axes[1], "Longest unsupported centerline run", "Gap fraction", "Struts")
    return save(fig, output, "04_support_and_gap_distributions.png")


def rank_curve(rows: list[dict[str, str]], output: Path) -> str:
    rank = numeric(rows, "ct_rank_weakest_first")
    score = numeric(rows, "ct_defect_score")
    order = np.argsort(rank)
    fig, axis = plt.subplots(figsize=(9, 5.5))
    axis.plot(rank[order] / len(rank) * 100, score[order], color="#c93838", linewidth=1.6)
    axis.axvspan(0, 0.5, color="#ce2e32", alpha=0.14, label="High + critical")
    axis.axvspan(0.5, 1.5, color="#e0b13c", alpha=0.14, label="Moderate")
    axis.legend(frameon=False)
    style_axis(axis, "Defect score across screening rank", "Weakest-first percentile", "Defect score")
    return save(fig, output, "05_rank_score_curve.png")


def orientation_summary(rows: list[dict[str, str]], output: Path) -> str:
    orientation = categorical(rows, "orientation_class")
    angle = numeric(rows, "angle_to_build_z_deg")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    names, counts = np.unique(orientation, return_counts=True)
    bars = axes[0].bar(names, counts, color="#5d94b8")
    axes[0].bar_label(bars, labels=[f"{x:,}" for x in counts])
    axes[1].hist(angle, bins=45, color="#7d74ac")
    style_axis(axes[0], "Orientation classes", ylabel="Struts")
    style_axis(axes[1], "Angle to assumed Z build direction", "Degrees", "Struts")
    return save(fig, output, "06_orientation_summary.png")


def hexbin_plot(rows: list[dict[str, str]], output: Path, xfield: str, yfield: str, filename: str, title: str, xlabel: str, ylabel: str) -> str:
    x = numeric(rows, xfield)
    y = numeric(rows, yfield)
    fig, axis = plt.subplots(figsize=(8.5, 6))
    result = axis.hexbin(x, y, gridsize=45, mincnt=1, cmap="viridis")
    fig.colorbar(result, ax=axis, label="Strut count")
    style_axis(axis, title, xlabel, ylabel)
    return save(fig, output, filename)


def degree_heatmap(rows: list[dict[str, str]], output: Path) -> str:
    first = numeric(rows, "junction0_degree").astype(int)
    second = numeric(rows, "junction1_degree").astype(int)
    max_degree = max(int(first.max()), int(second.max()))
    matrix = np.zeros((max_degree + 1, max_degree + 1), dtype=int)
    for a, b in zip(first, second, strict=True):
        matrix[a, b] += 1
    fig, axis = plt.subplots(figsize=(7.5, 6))
    image = axis.imshow(matrix, origin="lower", cmap="Blues")
    fig.colorbar(image, ax=axis, label="Struts")
    style_axis(axis, "Endpoint connectivity combinations", "Junction 1 degree", "Junction 0 degree")
    return save(fig, output, "09_endpoint_degree_heatmap.png")


def grouped_boxplot(rows: list[dict[str, str]], output: Path) -> str:
    degrees = numeric(rows, "mean_endpoint_degree")
    score = numeric(rows, "ct_defect_score")
    groups = sorted(np.unique(degrees))
    data = [score[degrees == group] for group in groups]
    fig, axis = plt.subplots(figsize=(10, 5.5))
    axis.boxplot(data, tick_labels=[f"{g:g}" for g in groups], showfliers=False, patch_artist=True, boxprops={"facecolor": "#8db4c9"})
    style_axis(axis, "Defect score by mean endpoint degree", "Mean endpoint degree", "Defect score")
    return save(fig, output, "10_defect_by_endpoint_degree.png")


def edge_type_plots(rows: list[dict[str, str]], output: Path) -> list[str]:
    edges = numeric(rows, "unit_cell_edge_idx").astype(int)
    score = numeric(rows, "ct_defect_score")
    severity = categorical(rows, "ct_severity_layer")
    types = sorted(np.unique(edges))
    means = [float(np.mean(score[edges == edge])) for edge in types]
    candidate_rate = [float(np.mean(np.isin(severity[edges == edge], ["high", "critical"]))) * 100 for edge in types]
    files = []
    for values, filename, title, ylabel, color in (
        (means, "11_edge_type_mean_defect.png", "Mean defect score by unit-cell edge type", "Mean defect score", "#c86a3b"),
        (candidate_rate, "12_edge_type_candidate_rate.png", "High/critical candidate rate by edge type", "Candidate rate (%)", "#d59b31"),
    ):
        fig, axis = plt.subplots(figsize=(12, 5.5))
        axis.bar(types, values, color=color)
        style_axis(axis, title, "Unit-cell edge type", ylabel)
        files.append(save(fig, output, filename))
    return files


def stacked_composition(rows: list[dict[str, str]], output: Path, group_field: str, filename: str, title: str) -> str:
    groups = categorical(rows, group_field)
    severity = categorical(rows, "ct_severity_layer")
    names = sorted(np.unique(groups))
    fig, axis = plt.subplots(figsize=(10, 5.5))
    bottom = np.zeros(len(names))
    for level in SEVERITY_ORDER:
        values = []
        for name in names:
            selected = severity[groups == name]
            values.append(float(np.mean(selected == level) * 100) if len(selected) else 0)
        axis.bar(names, values, bottom=bottom, color=SEVERITY_COLORS[level], label=level.title())
        bottom += values
    axis.legend(frameon=False, ncol=3)
    style_axis(axis, title, group_field.replace("_", " ").title(), "Share of struts (%)")
    return save(fig, output, filename)


def spatial_projection(rows: list[dict[str, str]], output: Path, axes_fields: tuple[str, str], filename: str) -> str:
    x = numeric(rows, axes_fields[0])
    y = numeric(rows, axes_fields[1])
    score = numeric(rows, "ct_defect_score")
    fig, axis = plt.subplots(figsize=(8, 7))
    background = score < np.percentile(score, 97)
    axis.scatter(x[background], y[background], s=2, color="#b8ccd8", alpha=0.18, rasterized=True)
    foreground = ~background
    points = axis.scatter(x[foreground], y[foreground], c=score[foreground], s=15, cmap=DEFECT_CMAP, alpha=0.9)
    fig.colorbar(points, ax=axis, label="Defect score")
    style_axis(axis, f"Spatial screening projection: {axes_fields[0][-4].upper()}{axes_fields[1][-4].upper()}", axes_fields[0].replace("midpoint_", "").replace("_mm", " (mm)"), axes_fields[1].replace("midpoint_", "").replace("_mm", " (mm)"))
    axis.set_aspect("equal", adjustable="box")
    return save(fig, output, filename)


def critical_3d(rows: list[dict[str, str]], output: Path) -> str:
    x = numeric(rows, "midpoint_x_mm")
    y = numeric(rows, "midpoint_y_mm")
    z = numeric(rows, "midpoint_z_mm")
    severity = categorical(rows, "ct_severity_layer")
    fig = plt.figure(figsize=(9, 8))
    axis = fig.add_subplot(111, projection="3d")
    for level in ("moderate", "high", "critical"):
        selected = severity == level
        axis.scatter(x[selected], y[selected], z[selected], s={"moderate": 8, "high": 22, "critical": 42}[level], color=SEVERITY_COLORS[level], alpha=0.85, label=level.title())
    axis.set_xlabel("X (mm)")
    axis.set_ylabel("Y (mm)")
    axis.set_zlabel("Z (mm)")
    axis.set_title("Elevated defect candidates in 3D", loc="left", fontweight="bold")
    axis.legend(frameon=False)
    return save(fig, output, "18_elevated_candidates_3d.png")


def unit_cell_heatmap(rows: list[dict[str, str]], output: Path) -> str:
    i = numeric(rows, "unit_cell_i").astype(int)
    j = numeric(rows, "unit_cell_j").astype(int)
    k = numeric(rows, "unit_cell_k").astype(int)
    score = numeric(rows, "ct_defect_score")
    layers = sorted(np.unique(k))
    columns = 3
    figure, axes = plt.subplots(math.ceil(len(layers) / columns), columns, figsize=(12, 12), constrained_layout=True)
    all_axes = np.asarray(axes).ravel()
    global_max = float(np.max(score))
    last_image = None
    for plot_axis, layer in zip(all_axes, layers, strict=False):
        matrix = np.full((int(j.max()) + 1, int(i.max()) + 1), np.nan)
        for x_index in np.unique(i):
            for y_index in np.unique(j):
                selected = (i == x_index) & (j == y_index) & (k == layer)
                if np.any(selected):
                    matrix[y_index, x_index] = np.max(score[selected])
        last_image = plot_axis.imshow(matrix, origin="lower", cmap=DEFECT_CMAP, vmin=0, vmax=global_max)
        plot_axis.set_title(f"Cell layer k={layer}")
        plot_axis.set_xlabel("Cell i")
        plot_axis.set_ylabel("Cell j")
    for plot_axis in all_axes[len(layers):]:
        plot_axis.axis("off")
    if last_image is not None:
        figure.colorbar(last_image, ax=list(all_axes[: len(layers)]), shrink=0.7, label="Maximum strut defect score")
    figure.suptitle("Maximum defect score within each unit cell", fontweight="bold")
    return save(figure, output, "19_unit_cell_layer_heatmaps.png")


def cell_k_profile(rows: list[dict[str, str]], output: Path) -> str:
    k = numeric(rows, "unit_cell_k").astype(int)
    score = numeric(rows, "ct_defect_score")
    layers = sorted(np.unique(k))
    means = [np.mean(score[k == layer]) for layer in layers]
    p95 = [np.percentile(score[k == layer], 95) for layer in layers]
    fig, axis = plt.subplots(figsize=(9, 5.5))
    axis.plot(layers, means, marker="o", label="Mean")
    axis.plot(layers, p95, marker="s", label="95th percentile")
    axis.legend(frameon=False)
    style_axis(axis, "Defect-score profile through unit-cell layers", "Unit-cell k index", "Defect score")
    return save(fig, output, "20_defect_by_cell_k.png")


def correlation_heatmap(rows: list[dict[str, str]], output: Path) -> str:
    fields = [
        "angle_to_build_z_deg", "mean_endpoint_degree", "minimum_midpoint_boundary_distance_mm",
        "ct_support_fraction", "ct_longest_gap_fraction", "ct_profile_min_to_mean",
        "ct_relative_local_intensity", "ct_defect_score",
    ]
    data = np.column_stack([numeric(rows, field) for field in fields])
    matrix = np.corrcoef(data, rowvar=False)
    fig, axis = plt.subplots(figsize=(10, 8))
    image = axis.imshow(matrix, vmin=-1, vmax=1, cmap="coolwarm")
    labels = [display_name(field) for field in fields]
    axis.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    axis.set_yticks(range(len(labels)), labels)
    for row_index in range(len(labels)):
        for column_index in range(len(labels)):
            axis.text(column_index, row_index, f"{matrix[row_index, column_index]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=axis, label="Pearson correlation")
    axis.set_title("Selected numeric-feature correlations", loc="left", fontweight="bold")
    return save(fig, output, "21_selected_feature_correlations.png")


def variability(rows: list[dict[str, str]], output: Path) -> str:
    fields = [
        "length_mm", "angle_to_build_z_deg", "mean_endpoint_degree",
        "minimum_midpoint_boundary_distance_mm", "slenderness_length_over_diameter",
        "axial_geometry_proxy_area_over_length_mm", "ct_support_fraction",
        "ct_relative_local_intensity", "ct_defect_score",
    ]
    cvs = []
    for field in fields:
        values = numeric(rows, field)
        mean = abs(float(np.mean(values)))
        cvs.append(float(np.std(values) / mean) if mean > 1e-12 else 0.0)
    order = np.argsort(cvs)
    fig, axis = plt.subplots(figsize=(10, 6))
    labels = [display_name(fields[index]) for index in order]
    axis.barh(labels, np.asarray(cvs)[order], color="#688fac")
    style_axis(axis, "Relative variability of candidate modeling features", "Coefficient of variation", "")
    return save(fig, output, "22_feature_variability.png")


def severity_boxplots(rows: list[dict[str, str]], output: Path) -> str:
    severity = categorical(rows, "ct_severity_layer")
    fields = ["ct_relative_local_intensity", "ct_support_fraction", "ct_profile_min_to_mean"]
    titles = ["Local intensity ratio", "Supported samples", "Minimum / mean profile"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), constrained_layout=True)
    for axis, field, title in zip(axes, fields, titles, strict=True):
        values = numeric(rows, field)
        data = [values[severity == level] for level in SEVERITY_ORDER]
        boxes = axis.boxplot(data, tick_labels=[x.title() for x in SEVERITY_ORDER], showfliers=False, patch_artist=True)
        for box, level in zip(boxes["boxes"], SEVERITY_ORDER, strict=True):
            box.set_facecolor(SEVERITY_COLORS[level])
        axis.tick_params(axis="x", rotation=35)
        style_axis(axis, title, "", display_name(field))
    return save(fig, output, "26_ct_metrics_by_severity.png")


def top_struts_table(rows: list[dict[str, str]], output: Path) -> str:
    selected = sorted(rows, key=lambda row: int(row["ct_rank_weakest_first"]))[:20]
    columns = ["ct_rank_weakest_first", "strut_id", "unit_cell_edge_idx", "ct_defect_score", "ct_relative_local_intensity", "minimum_midpoint_boundary_distance_mm"]
    labels = ["Rank", "Strut", "Edge", "Defect", "Intensity ratio", "Boundary mm"]
    cell_text = [[row[column] for column in columns] for row in selected]
    fig, axis = plt.subplots(figsize=(11, 7))
    axis.axis("off")
    table = axis.table(cellText=cell_text, colLabels=labels, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.35)
    axis.set_title("Twenty strongest defect candidates", loc="left", fontweight="bold")
    return save(fig, output, "27_top_defect_candidates_table.png")


def summary_atlas(output: Path, files: list[str]) -> str:
    selected = [name for name in files if name.endswith(".png")][:12]
    fig, axes = plt.subplots(4, 3, figsize=(18, 20), constrained_layout=True)
    for axis, filename in zip(axes.ravel(), selected, strict=False):
        image = plt.imread(output / filename)
        axis.imshow(image)
        axis.set_title(filename.replace(".png", "").replace("_", " "), fontsize=10)
        axis.axis("off")
    for axis in axes.ravel()[len(selected):]:
        axis.axis("off")
    fig.suptitle("Strut feature visualization atlas", fontsize=20, fontweight="bold")
    return save(fig, output, "00_visualization_atlas.png")


def write_index(output: Path, files: list[str]) -> None:
    sections = "\n".join(
        f"## {filename.replace('.png', '').replace('_', ' ').title()}\n\n![{filename}]({filename})\n"
        for filename in files
    )
    report = f"""# Strut feature visualization atlas

These plots explore the registered `0.5-1` specimen at the individual-strut level. CT severity
is a screening rank rather than verified ground truth. Mechanical quantities are geometry-only
proxies, and Z is provisionally treated as the build direction.

{sections}
"""
    (output / "VISUALIZATION_INDEX.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows(args.input)
    files: list[str] = []
    files.append(severity_counts(rows, args.output_dir))
    files.append(defect_distribution(rows, args.output_dir))
    files.append(intensity_distribution(rows, args.output_dir))
    files.append(support_gap(rows, args.output_dir))
    files.append(rank_curve(rows, args.output_dir))
    files.append(orientation_summary(rows, args.output_dir))
    files.append(hexbin_plot(rows, args.output_dir, "angle_to_build_z_deg", "ct_defect_score", "07_angle_vs_defect_hexbin.png", "Build-angle relationship with defect score", "Angle to Z (degrees)", "Defect score"))
    files.append(hexbin_plot(rows, args.output_dir, "minimum_midpoint_boundary_distance_mm", "ct_defect_score", "08_boundary_distance_vs_defect_hexbin.png", "Boundary-distance relationship with defect score", "Boundary distance (mm)", "Defect score"))
    files.append(degree_heatmap(rows, args.output_dir))
    files.append(grouped_boxplot(rows, args.output_dir))
    files.extend(edge_type_plots(rows, args.output_dir))
    files.append(stacked_composition(rows, args.output_dir, "near_boundary_one_cell", "13_boundary_severity_composition.png", "Severity composition: boundary versus interior"))
    files.append(stacked_composition(rows, args.output_dir, "orientation_class", "14_orientation_severity_composition.png", "Severity composition by orientation"))
    files.append(spatial_projection(rows, args.output_dir, ("midpoint_x_mm", "midpoint_y_mm"), "15_xy_spatial_defect.png"))
    files.append(spatial_projection(rows, args.output_dir, ("midpoint_x_mm", "midpoint_z_mm"), "16_xz_spatial_defect.png"))
    files.append(spatial_projection(rows, args.output_dir, ("midpoint_y_mm", "midpoint_z_mm"), "17_yz_spatial_defect.png"))
    files.append(critical_3d(rows, args.output_dir))
    files.append(unit_cell_heatmap(rows, args.output_dir))
    files.append(cell_k_profile(rows, args.output_dir))
    files.append(correlation_heatmap(rows, args.output_dir))
    files.append(variability(rows, args.output_dir))
    files.append(hexbin_plot(rows, args.output_dir, "ct_relative_local_intensity", "ct_defect_score", "23_intensity_vs_defect_hexbin.png", "Normalized CT intensity versus defect score", "Local intensity ratio", "Defect score"))
    files.append(hexbin_plot(rows, args.output_dir, "ct_support_fraction", "ct_defect_score", "24_support_vs_defect_hexbin.png", "Centerline support versus defect score", "Support fraction", "Defect score"))
    files.append(hexbin_plot(rows, args.output_dir, "ct_longest_gap_fraction", "ct_defect_score", "25_gap_vs_defect_hexbin.png", "Unsupported gap versus defect score", "Longest gap fraction", "Defect score"))
    files.append(severity_boxplots(rows, args.output_dir))
    files.append(top_struts_table(rows, args.output_dir))
    atlas = summary_atlas(args.output_dir, files)
    write_index(args.output_dir, [atlas] + files)
    print(f"Generated {len(files) + 1} visualization files from {len(rows):,} struts")
    print(f"Index: {(args.output_dir / 'VISUALIZATION_INDEX.md').resolve()}")


if __name__ == "__main__":
    main()
