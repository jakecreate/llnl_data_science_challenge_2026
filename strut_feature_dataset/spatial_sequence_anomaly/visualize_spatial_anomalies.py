"""Visualize ADTK spatial-sequence results and centerline profile features."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE / "datasets"
DEFAULT_OUTPUT = HERE / "visualizations"


def save(fig: plt.Figure, output: Path, filename: str) -> str:
    fig.savefig(output / filename, dpi=175, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return filename


def detector_counts(data: pd.DataFrame, output: Path) -> str:
    labels = ["IQR low", "Bottom 2%", "Persistent drop", "Consensus"]
    counts = [
        int(data.adtk_iqr_low_anomaly.sum()),
        int(data.adtk_quantile_low_anomaly.sum()),
        int(data.adtk_persist_negative_anomaly.sum()),
        int(data.adtk_consensus_anomaly.sum()),
    ]
    fig, axis = plt.subplots(figsize=(9, 5.5))
    bars = axis.bar(labels, counts, color=["#6e98b4", "#d6a43a", "#e47a32", "#c83036"])
    axis.bar_label(bars, labels=[f"{value:,}" for value in counts])
    axis.set_title("ADTK spatial anomaly counts", loc="left", fontweight="bold")
    axis.set_ylabel("Struts")
    axis.grid(axis="y", alpha=0.2)
    return save(fig, output, "01_adtk_detector_counts.png")


def overlap_matrix(data: pd.DataFrame, output: Path) -> str:
    heuristic = data.ct_severity_layer.isin(["high", "critical"]).astype(int)
    adtk = data.adtk_consensus_anomaly.astype(int)
    matrix = np.zeros((2, 2), dtype=int)
    for expected, detected in zip(heuristic, adtk):
        matrix[expected, detected] += 1
    fig, axis = plt.subplots(figsize=(7, 6))
    image = axis.imshow(matrix, cmap="Blues")
    axis.set_xticks([0, 1], ["ADTK no", "ADTK yes"])
    axis.set_yticks([0, 1], ["Rank screen no", "Rank screen yes"])
    for row in range(2):
        for column in range(2):
            axis.text(column, row, f"{matrix[row, column]:,}", ha="center", va="center", fontsize=13)
    fig.colorbar(image, ax=axis, label="Struts")
    axis.set_title("ADTK agreement with existing screening\n(not ground-truth accuracy)", loc="left", fontweight="bold")
    return save(fig, output, "02_adtk_screening_overlap.png")


def spatial_maps(data: pd.DataFrame, output: Path) -> list[str]:
    files = []
    for first, second, filename in (
        ("midpoint_x_mm", "midpoint_y_mm", "03_adtk_xy_map.png"),
        ("midpoint_x_mm", "midpoint_z_mm", "04_adtk_xz_map.png"),
        ("midpoint_y_mm", "midpoint_z_mm", "05_adtk_yz_map.png"),
    ):
        fig, axis = plt.subplots(figsize=(8, 7))
        normal = data.adtk_consensus_anomaly == 0
        anomalous = ~normal
        axis.scatter(data.loc[normal, first], data.loc[normal, second], s=2, color="#aec5d3", alpha=0.2)
        axis.scatter(data.loc[anomalous, first], data.loc[anomalous, second], s=26, color="#cf3037", marker="x", label="ADTK consensus")
        axis.legend(frameon=False)
        axis.set_xlabel(first.replace("midpoint_", "").replace("_mm", " (mm)"))
        axis.set_ylabel(second.replace("midpoint_", "").replace("_mm", " (mm)"))
        axis.set_title("Spatial location of ADTK consensus anomalies", loc="left", fontweight="bold")
        axis.set_aspect("equal", adjustable="box")
        axis.grid(alpha=0.15)
        files.append(save(fig, output, filename))
    return files


def edge_sequences(data: pd.DataFrame, output: Path) -> str:
    counts = data.groupby("sequence_id").adtk_consensus_anomaly.sum().sort_values(ascending=False)
    selected_ids = list(counts.head(6).index)
    fig, axes = plt.subplots(3, 2, figsize=(14, 10), constrained_layout=True)
    for axis, sequence_id in zip(axes.ravel(), selected_ids):
        group = data[data.sequence_id == sequence_id].sort_values("sequence_position")
        axis.plot(group.sequence_position, group.ct_relative_local_intensity, color="#5d8299", linewidth=1)
        anomalies = group.adtk_consensus_anomaly == 1
        axis.scatter(group.loc[anomalies, "sequence_position"], group.loc[anomalies, "ct_relative_local_intensity"], color="#ce3036", s=30, label="Consensus")
        axis.axhline(1.0, color="#555555", linewidth=0.8, alpha=0.5)
        axis.set_title(f"{sequence_id}: Morton-ordered spatial sequence")
        axis.set_xlabel("Spatial sequence position")
        axis.set_ylabel("Relative intensity")
        axis.grid(alpha=0.15)
    return save(fig, output, "06_high_anomaly_edge_sequences.png")


def profile_summary_plot(summary: pd.DataFrame, output: Path) -> str:
    order = ["supported", "watch", "moderate", "high", "critical"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), constrained_layout=True)
    fields = [
        ("profile_relative_mean", "Mean normalized profile"),
        ("profile_fraction_below_80pct", "Fraction below 80% baseline"),
        ("profile_longest_run_below_80pct", "Longest low-intensity run"),
    ]
    for axis, (field, title) in zip(axes, fields):
        groups = [summary.loc[summary.ct_severity_layer == level, field] for level in order]
        boxes = axis.boxplot(groups, tick_labels=[name.title() for name in order], showfliers=False, patch_artist=True)
        for box, color in zip(boxes["boxes"], ["#80a5bd", "#58a7cd", "#ddb23e", "#ef7d31", "#cf3036"]):
            box.set_facecolor(color)
        axis.tick_params(axis="x", rotation=35)
        axis.set_title(title)
        axis.grid(alpha=0.15)
    return save(fig, output, "07_profile_features_by_severity.png")


def top_profiles(data_dir: Path, summary: pd.DataFrame, output: Path) -> str:
    top_ids = list(summary.sort_values("ct_defect_score", ascending=False).head(6).strut_id.astype(int))
    chunks = []
    for chunk in pd.read_csv(data_dir / "centerline_profiles_long.csv.gz", compression="gzip", chunksize=100000):
        selected = chunk[chunk.strut_id.isin(top_ids)]
        if len(selected):
            chunks.append(selected)
    profiles = pd.concat(chunks, ignore_index=True)
    fig, axes = plt.subplots(3, 2, figsize=(13, 10), constrained_layout=True)
    for axis, strut_id in zip(axes.ravel(), top_ids):
        group = profiles[profiles.strut_id == strut_id].sort_values("normalized_position")
        axis.plot(group.normalized_position, group.relative_to_local_baseline, marker="o", color="#355f7a")
        axis.axhline(0.8, color="#ce3036", linestyle="--", label="80% baseline")
        axis.fill_between(group.normalized_position, 0, 0.8, color="#ce3036", alpha=0.08)
        axis.set_title(f"Strut {strut_id}")
        axis.set_xlabel("Normalized position along strut")
        axis.set_ylabel("Relative CT intensity")
        axis.grid(alpha=0.15)
    return save(fig, output, "08_top_candidate_centerline_profiles.png")


def write_findings(data: pd.DataFrame, summary: pd.DataFrame, output_dir: Path, files: list[str]) -> None:
    analysis = json.loads((DEFAULT_DATA / "adtk_analysis_summary.json").read_text(encoding="utf-8"))
    critical = summary[summary.ct_severity_layer.isin(["high", "critical"])]
    low_profile_rate = float(np.mean(critical.profile_fraction_below_80pct >= 0.8))
    gallery = "\n".join(f"## {name.replace('.png', '').replace('_', ' ').title()}\n\n![{name}]({name})\n" for name in files)
    report = f"""# ADTK spatial-sequence findings

## Scientific status

This experiment does **not** create genuine time observations. It applies time-series machinery to
two ordered spatial domains: Morton-ordered unit cells within comparable edge types and positions
along registered strut centerlines. Results depend on those order definitions.

## Results

- ADTK IQR low anomalies: {analysis['iqr_low_anomalies']:,}
- ADTK bottom-quantile anomalies: {analysis['quantile_low_anomalies']:,}
- ADTK persistent negative changes: {analysis['persist_negative_anomalies']:,}
- Two-detector consensus anomalies: {analysis['consensus_anomalies']:,}
- Consensus overlap with the existing 92 high/critical candidates: {analysis['consensus_overlap_with_existing_high_or_critical']:,}
- Consensus agreement rate: {analysis['consensus_overlap_rate']:.1%}
- Existing candidate coverage by consensus: {analysis['existing_candidate_recall_by_consensus']:.1%}
- High/critical profiles low for at least 80% of their length: {low_profile_rate:.1%}

Agreement with the existing defect score is not independent accuracy because both methods use CT
intensity. The useful contribution is a second, edge-type-specific robust baseline and explicit
centerline profile shape features.

{gallery}
"""
    (HERE / "FINDINGS.md").write_text(report, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(args.data_dir / "adtk_spatial_anomaly_results.csv")
    summary = pd.read_csv(args.data_dir / "centerline_profile_summary.csv")
    files = [detector_counts(data, args.output_dir), overlap_matrix(data, args.output_dir)]
    files.extend(spatial_maps(data, args.output_dir))
    files.append(edge_sequences(data, args.output_dir))
    files.append(profile_summary_plot(summary, args.output_dir))
    files.append(top_profiles(args.data_dir, summary, args.output_dir))
    write_findings(data, summary, args.output_dir, files)
    print(f"Generated {len(files)} visualizations")
    print(f"Findings: {(HERE / 'FINDINGS.md').resolve()}")


if __name__ == "__main__":
    main()
