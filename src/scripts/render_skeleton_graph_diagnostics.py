"""Render the skeleton/graph diagnostic from cached CT analysis artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from skimage.morphology import skeletonize


ROOT = Path(__file__).resolve().parents[2]
FEATURE_DIR = ROOT / "outputs" / "features"
MASK_PATH = FEATURE_DIR / "ct_selected_mask_ds4.tif"
EDGES_PATH = FEATURE_DIR / "skeleton_edges.csv"
GRAPH_PATH = FEATURE_DIR / "skeleton_graph.json"
OUTPUT_PATH = ROOT / "outputs" / "reports" / "skeleton_graph_diagnostics.png"
SPACING = np.asarray([4.0, 4.0, 4.0])


def render(example_slice: int) -> None:
    """Render the mask/skeleton panel at one axis-0 analysis-grid slice."""
    selected_mask = tifffile.imread(MASK_PATH).astype(bool)
    if not 0 <= example_slice < selected_mask.shape[0]:
        raise IndexError(
            f"Diagnostic axis-0 slice {example_slice} is outside the analysis volume "
            f"with {selected_mask.shape[0]} slices."
        )
    skeleton = skeletonize(selected_mask, method="lee").astype(bool)

    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    edge_coordinates = {
        int(edge["edge_id"]): np.asarray(edge["coordinates_zyx_analysis_grid"], dtype=float)
        for edge in graph["edges"]
    }
    with EDGES_PATH.open(newline="", encoding="utf-8") as stream:
        edge_rows = [
            row
            for row in csv.DictReader(stream)
            if row["retained_after_pruning"].lower() == "true"
        ]
    edge_rows.sort(key=lambda row: float(row["path_length_original_voxels"]), reverse=True)
    diagnostic_edge_ids = [int(row["edge_id"]) for row in edge_rows[:1800]]
    junctions = [node for node in graph["nodes"] if int(node["degree"]) >= 3]

    plt.rcParams.update({"figure.dpi": 120, "savefig.dpi": 160, "axes.grid": True})
    fig = plt.figure(figsize=(13, 5.5))
    ax_slice = fig.add_subplot(1, 2, 1)
    ax_slice.imshow(selected_mask[example_slice], cmap="gray")
    ax_slice.imshow(
        np.ma.masked_where(~skeleton[example_slice], skeleton[example_slice]),
        cmap="autumn",
        alpha=0.9,
    )
    ax_slice.set_title(f"Mask + skeleton, axis-0 slice {example_slice}")
    ax_slice.axis("off")

    ax_graph = fig.add_subplot(1, 2, 2, projection="3d")
    for edge_id in diagnostic_edge_ids:
        coordinates = edge_coordinates[edge_id] * SPACING
        ax_graph.plot(
            coordinates[:, 2],
            coordinates[:, 1],
            coordinates[:, 0],
            linewidth=0.35,
            alpha=0.35,
            color="navy",
        )
    ax_graph.scatter(
        [node["x_original_voxels"] for node in junctions],
        [node["y_original_voxels"] for node in junctions],
        [node["z_original_voxels"] for node in junctions],
        s=2,
        c="crimson",
        alpha=0.35,
    )
    ax_graph.set(
        xlabel="X",
        ylabel="Y",
        zlabel="Z",
        title="Longest retained logical edges + junctions",
    )
    fig.tight_layout()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slice", type=int, default=150, dest="example_slice")
    args = parser.parse_args()
    render(args.example_slice)


if __name__ == "__main__":
    main()
