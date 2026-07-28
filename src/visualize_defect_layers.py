"""Create layered PyVista views and spatial close-ups of CT-scored lattice defects."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyvista as pv


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = (
    ROOT / "data" / "missing_struts" / "defect_analysis" / "strut_defect_results.json"
)
DEFAULT_OUTPUT = ROOT / "data" / "missing_struts" / "defect_analysis" / "layered_views"


@dataclass(frozen=True)
class LayerStyle:
    name: str
    color: str
    line_width: float
    opacity: float


LAYER_STYLES = {
    0: LayerStyle("Supported", "#84a5bd", 1.0, 0.10),
    1: LayerStyle("Watch", "#65a9cf", 1.5, 0.42),
    2: LayerStyle("Moderate", "#e0b13c", 2.4, 0.76),
    3: LayerStyle("High", "#ef7d32", 4.0, 0.94),
    4: LayerStyle("Critical", "#ce2e32", 6.5, 1.00),
}


def assign_severity(rows: list[dict]) -> None:
    """Create stable, rank-based severity layers from the detector output."""
    n_rows = len(rows)
    critical_end = max(1, round(n_rows * 0.001))
    high_end = max(critical_end, round(n_rows * 0.005))
    moderate_end = max(high_end, round(n_rows * 0.015))
    watch_end = max(moderate_end, round(n_rows * 0.030))
    for row in rows:
        rank = int(row["rank_weakest_first"])
        if rank <= critical_end:
            level = 4
        elif rank <= high_end:
            level = 3
        elif rank <= moderate_end:
            level = 2
        elif rank <= watch_end:
            level = 1
        else:
            level = 0
        row["severity_level"] = level
        row["severity_name"] = LAYER_STYLES[level].name.lower()


def rows_to_mesh(rows: list[dict], spacing_mm: float) -> pv.PolyData:
    points: list[np.ndarray] = []
    lines: list[list[int]] = []
    for row in rows:
        first = len(points)
        points.extend(
            [
                np.asarray(row["start_xyz_voxels"], dtype=float) * spacing_mm,
                np.asarray(row["end_xyz_voxels"], dtype=float) * spacing_mm,
            ]
        )
        lines.append([2, first, first + 1])
    mesh = pv.PolyData()
    mesh.points = np.asarray(points)
    mesh.lines = np.asarray(lines).ravel()
    mesh.cell_data["strut_id"] = np.asarray([int(row["strut_id"]) for row in rows])
    mesh.cell_data["severity_level"] = np.asarray(
        [int(row["severity_level"]) for row in rows], dtype=np.uint8
    )
    mesh.cell_data["defect_score"] = np.asarray(
        [float(row["defect_score"]) for row in rows]
    )
    mesh.cell_data["relative_local_intensity"] = np.asarray(
        [float(row["relative_local_intensity"]) for row in rows]
    )
    return mesh


def add_layers(
    plotter: pv.Plotter,
    mesh: pv.PolyData,
    minimum_level: int = 0,
    local_opacity_boost: bool = False,
) -> dict[int, object]:
    actors: dict[int, object] = {}
    severity = mesh.cell_data["severity_level"]
    for level, style in LAYER_STYLES.items():
        if level < minimum_level:
            continue
        layer = mesh.extract_cells(severity == level)
        if layer.n_cells == 0:
            continue
        opacity = max(style.opacity, 0.22) if local_opacity_boost and level == 0 else style.opacity
        actors[level] = plotter.add_mesh(
            layer,
            color=style.color,
            line_width=style.line_width,
            opacity=opacity,
            label=style.name,
            render_lines_as_tubes=level >= 3,
        )
    return actors


def configure_plotter(plotter: pv.Plotter, title: str, camera: tuple[float, float]) -> None:
    plotter.set_background("#f5f7fa")
    plotter.add_text(title, position="upper_left", font_size=14, color="#253342")
    plotter.add_axes(xlabel="X", ylabel="Y", zlabel="Z")
    plotter.show_bounds(
        xtitle="X (mm)",
        ytitle="Y (mm)",
        ztitle="Z (mm)",
        grid="back",
        color="#405060",
        n_xlabels=4,
        n_ylabels=4,
        n_zlabels=4,
    )
    plotter.camera_position = "iso"
    plotter.camera.elevation = camera[0] - 30.0
    plotter.camera.azimuth = camera[1] - 45.0
    plotter.camera.zoom(1.06)


def add_legend(plotter: pv.Plotter, minimum_level: int = 0) -> None:
    entries = [
        [style.name, style.color]
        for level, style in reversed(LAYER_STYLES.items())
        if level >= minimum_level
    ]
    plotter.add_legend(entries, loc="upper right", size=(0.17, 0.19), bcolor="#ffffff")


def render_overviews(mesh: pv.PolyData, output_dir: Path) -> None:
    views = (("view_a", (30.0, 45.0)), ("view_b", (60.0, 45.0)))
    for suffix, camera in views:
        plotter = pv.Plotter(off_screen=True, window_size=(1500, 1150))
        add_layers(plotter, mesh)
        add_legend(plotter)
        configure_plotter(plotter, "CT strut defect severity layers", camera)
        plotter.show(screenshot=str(output_dir / f"defect_layers_{suffix}.png"), auto_close=True)

    cumulative = (
        (4, "critical_only", "Critical candidates"),
        (3, "high_and_critical", "High and critical candidates"),
        (2, "moderate_and_above", "Moderate through critical candidates"),
        (1, "watch_and_above", "All elevated defect layers"),
    )
    for minimum, filename, title in cumulative:
        plotter = pv.Plotter(off_screen=True, window_size=(1400, 1050))
        add_layers(plotter, mesh, minimum_level=minimum)
        add_legend(plotter, minimum_level=minimum)
        configure_plotter(plotter, title, (30.0, 45.0))
        plotter.show(screenshot=str(output_dir / f"{filename}.png"), auto_close=True)


def union_find_regions(midpoints: np.ndarray, radius_mm: float) -> list[list[int]]:
    parent = list(range(len(midpoints)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first: int, second: int) -> None:
        root_first, root_second = find(first), find(second)
        if root_first != root_second:
            parent[root_second] = root_first

    for first in range(len(midpoints)):
        distances = np.linalg.norm(midpoints[first + 1 :] - midpoints[first], axis=1)
        for offset in np.flatnonzero(distances <= radius_mm):
            union(first, first + 1 + int(offset))
    groups: dict[int, list[int]] = {}
    for index in range(len(midpoints)):
        groups.setdefault(find(index), []).append(index)
    return list(groups.values())


def render_regions(
    rows: list[dict],
    output_dir: Path,
    spacing_mm: float,
    cluster_radius_mm: float,
    max_regions: int,
) -> list[dict]:
    severe = [row for row in rows if int(row["severity_level"]) >= 3]
    midpoints = np.asarray(row_midpoints(severe, spacing_mm))
    groups = union_find_regions(midpoints, cluster_radius_mm)
    groups.sort(
        key=lambda group: (
            -max(int(severe[index]["severity_level"]) for index in group),
            -len(group),
            min(int(severe[index]["rank_weakest_first"]) for index in group),
        )
    )
    if max_regions > 0:
        groups = groups[:max_regions]

    all_midpoints = np.asarray(row_midpoints(rows, spacing_mm))
    region_records: list[dict] = []
    for region_number, group in enumerate(groups, start=1):
        members = [severe[index] for index in group]
        endpoints = np.vstack(
            [
                np.asarray(row[key], dtype=float) * spacing_mm
                for row in members
                for key in ("start_xyz_voxels", "end_xyz_voxels")
            ]
        )
        lower = endpoints.min(axis=0) - 3.8
        upper = endpoints.max(axis=0) + 3.8
        nearby_mask = np.all((all_midpoints >= lower) & (all_midpoints <= upper), axis=1)
        nearby_rows = [row for row, keep in zip(rows, nearby_mask, strict=True) if keep]
        local_mesh = rows_to_mesh(nearby_rows, spacing_mm)

        plotter = pv.Plotter(off_screen=True, window_size=(1250, 1000))
        add_layers(plotter, local_mesh, local_opacity_boost=True)
        candidate_midpoints = np.asarray(row_midpoints(members, spacing_mm))
        plotter.add_point_labels(
            candidate_midpoints,
            [f"ID {row['strut_id']}" for row in members],
            font_size=15,
            text_color="#263645",
            shape_color="#ffffff",
            shape_opacity=0.82,
            always_visible=True,
        )
        plotter.set_background("#f5f7fa")
        plotter.add_axes(xlabel="X", ylabel="Y", zlabel="Z")
        plotter.show_bounds(
            bounds=[lower[0], upper[0], lower[1], upper[1], lower[2], upper[2]],
            xtitle="X (mm)",
            ytitle="Y (mm)",
            ztitle="Z (mm)",
            grid="back",
            color="#405060",
        )
        plotter.add_text(
            f"Defect region {region_number:02d} · {len(members)} high/critical strut(s)",
            position="upper_left",
            font_size=14,
            color="#253342",
        )
        add_legend(plotter)
        plotter.camera_position = "iso"
        plotter.camera.zoom(1.12)
        filename = f"defect_region_{region_number:02d}.png"
        plotter.show(screenshot=str(output_dir / filename), auto_close=True)
        region_records.append(
            {
                "region": region_number,
                "image": filename,
                "strut_ids": [int(row["strut_id"]) for row in members],
                "highest_severity": max(row["severity_name"] for row in members),
                "minimum_rank": min(int(row["rank_weakest_first"]) for row in members),
                "center_xyz_mm": candidate_midpoints.mean(axis=0).tolist(),
            }
        )
    return region_records


def row_midpoints(rows: list[dict], spacing_mm: float) -> list[np.ndarray]:
    return [
        (
            np.asarray(row["start_xyz_voxels"], dtype=float)
            + np.asarray(row["end_xyz_voxels"], dtype=float)
        )
        * 0.5
        * spacing_mm
        for row in rows
    ]


def write_region_index(output_dir: Path, regions: list[dict], rows: list[dict]) -> None:
    with (output_dir / "defect_regions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["region", "image", "strut_ids", "highest_severity", "minimum_rank", "center_xyz_mm"],
        )
        writer.writeheader()
        for region in regions:
            writer.writerow(
                {
                    **region,
                    "strut_ids": ";".join(map(str, region["strut_ids"])),
                    "center_xyz_mm": ";".join(f"{value:.3f}" for value in region["center_xyz_mm"]),
                }
            )

    counts = {
        style.name: sum(int(row["severity_level"]) == level for row in rows)
        for level, style in LAYER_STYLES.items()
    }
    region_gallery = "\n".join(
        f"### Region {region['region']:02d}\n\n"
        f"Struts: {', '.join(map(str, region['strut_ids']))}\n\n"
        f"![Region {region['region']:02d}]({region['image']})\n"
        for region in regions
    )
    report = f"""# PyVista defect-layer visualization

## Layer counts

| Layer | Struts |
|---|---:|
| Critical | {counts['Critical']:,} |
| High | {counts['High']:,} |
| Moderate | {counts['Moderate']:,} |
| Watch | {counts['Watch']:,} |
| Supported | {counts['Supported']:,} |

Severity is rank-based and intended for screening. Critical plus high contains the weakest 0.5%
of expected struts; these are the primary missing-strut candidates.

## Overview

![Layered view A](defect_layers_view_a.png)

![Layered view B](defect_layers_view_b.png)

## Defect-region close-ups

{region_gallery}
"""
    (output_dir / "LAYERED_DEFECT_REPORT.md").write_text(report, encoding="utf-8")


def interactive_view(mesh: pv.PolyData) -> None:
    plotter = pv.Plotter(window_size=(1500, 1100))
    actors = add_layers(plotter, mesh)
    configure_plotter(plotter, "Interactive CT defect layers", (30.0, 45.0))
    add_legend(plotter)
    for position, level in enumerate(reversed(LAYER_STYLES)):
        style = LAYER_STYLES[level]

        def toggle(visible: bool, target=actors.get(level)) -> None:
            if target is not None:
                target.SetVisibility(visible)

        plotter.add_checkbox_button_widget(
            toggle,
            value=True,
            position=(12, 12 + position * 34),
            size=25,
            color_on=style.color,
            color_off="#6b7785",
            background_color="#ffffff",
        )
        plotter.add_text(
            style.name,
            position=(47, 16 + position * 34),
            font_size=10,
            color="#253342",
        )
    plotter.show()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--voxel-spacing-um", type=float, default=58.09)
    parser.add_argument("--cluster-radius-mm", type=float, default=6.0)
    parser.add_argument(
        "--max-regions",
        type=int,
        default=0,
        help="Maximum region close-ups; the default 0 renders every region",
    )
    parser.add_argument("--show", action="store_true", help="Open the interactive layered viewer")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(args.results.read_text(encoding="utf-8"))
    rows = payload["struts"]
    assign_severity(rows)
    spacing_mm = args.voxel_spacing_um / 1000.0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    mesh = rows_to_mesh(rows, spacing_mm)
    mesh.save(args.output_dir / "strut_defect_layers.vtp")
    render_overviews(mesh, args.output_dir)
    regions = render_regions(
        rows,
        args.output_dir,
        spacing_mm,
        args.cluster_radius_mm,
        args.max_regions,
    )
    write_region_index(args.output_dir, regions, rows)
    print(f"Rendered five severity layers and {len(regions)} defect regions")
    print(f"Outputs: {args.output_dir.resolve()}")
    if args.show:
        interactive_view(mesh)


if __name__ == "__main__":
    main()
