"""Render the repository's octet unit cell with PyVista.

The JSON coordinates are normalized from 0 to 2 on each axis.  By default they
are scaled to the 4.56 mm unit-cell pitch documented for the missing-strut data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pyvista as pv


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "data" / "unitcell" / "polyhedron_1x1x1.json"
DEFAULT_OUTPUT = ROOT / "images" / "unit_cell_pyvista.png"


def load_unit_cell(path: Path, cell_size_mm: float) -> tuple[dict[int, np.ndarray], list[dict]]:
    """Return junction coordinates in millimetres and the strut definitions."""
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = {int(j["id"]): np.asarray(j["position"], dtype=float) for j in data["junctions"]}
    points = np.vstack(list(raw.values()))
    span = np.ptp(points, axis=0)
    if np.any(span == 0):
        raise ValueError("Unit-cell coordinates must span all three axes")

    origin = points.min(axis=0)
    junctions = {
        junction_id: (point - origin) / span * cell_size_mm
        for junction_id, point in raw.items()
    }
    return junctions, data["struts"]


def build_geometry(
    junctions: dict[int, np.ndarray],
    struts: list[dict],
    strut_diameter_mm: float,
) -> tuple[pv.PolyData, pv.PolyData]:
    """Construct cylinder struts and spherical junctions as two meshes."""
    radius = strut_diameter_mm / 2.0
    strut_meshes: list[pv.PolyData] = []
    for strut in struts:
        start = junctions[int(strut["junction0"])]
        end = junctions[int(strut["junction1"])]
        vector = end - start
        length = float(np.linalg.norm(vector))
        cylinder = pv.Cylinder(
            center=(start + end) / 2.0,
            direction=vector / length,
            radius=radius,
            height=length,
            resolution=48,
            capping=True,
        )
        cylinder.cell_data["strut_id"] = np.full(cylinder.n_cells, int(strut["id"]))
        strut_meshes.append(cylinder)

    connected_ids = {
        int(strut[key])
        for strut in struts
        for key in ("junction0", "junction1")
    }
    node_meshes: list[pv.PolyData] = []
    for junction_id in sorted(connected_ids):
        point = junctions[junction_id]
        sphere = pv.Sphere(radius=radius * 1.18, center=point, theta_resolution=32, phi_resolution=24)
        sphere.cell_data["junction_id"] = np.full(sphere.n_cells, junction_id)
        node_meshes.append(sphere)

    return pv.merge(strut_meshes), pv.merge(node_meshes)


def render(
    json_path: Path,
    output_path: Path,
    mesh_path: Path,
    cell_size_mm: float,
    strut_diameter_mm: float,
    show: bool,
    label_nodes: bool,
) -> None:
    junctions, struts = load_unit_cell(json_path, cell_size_mm)
    strut_mesh, node_mesh = build_geometry(junctions, struts, strut_diameter_mm)

    combined = strut_mesh.merge(node_mesh)
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(mesh_path)

    plotter = pv.Plotter(off_screen=not show, window_size=(1400, 1100))
    plotter.set_background("#f5f7fa")
    plotter.add_mesh(
        strut_mesh,
        color="#3274a1",
        smooth_shading=True,
        specular=0.35,
        specular_power=18,
    )
    plotter.add_mesh(
        node_mesh,
        color="#d9862c",
        smooth_shading=True,
        specular=0.25,
    )
    if label_nodes:
        ids = sorted(
            {
                int(strut[key])
                for strut in struts
                for key in ("junction0", "junction1")
            }
        )
        plotter.add_point_labels(
            np.vstack([junctions[i] for i in ids]),
            [str(i) for i in ids],
            font_size=18,
            text_color="#1f2933",
            shape_color="#ffffff",
            shape_opacity=0.75,
            always_visible=True,
        )

    plotter.show_bounds(
        bounds=[0, cell_size_mm, 0, cell_size_mm, 0, cell_size_mm],
        axes_ranges=[0, cell_size_mm, 0, cell_size_mm, 0, cell_size_mm],
        xtitle="X (mm)",
        ytitle="Y (mm)",
        ztitle="Z (mm)",
        n_xlabels=3,
        n_ylabels=3,
        n_zlabels=3,
        grid="back",
        color="#3e4c59",
    )
    plotter.add_text(
        f"Octet unit cell  |  pitch {cell_size_mm:.2f} mm  |  strut Ø {strut_diameter_mm:.2f} mm",
        position="upper_left",
        font_size=15,
        color="#1f2933",
    )
    plotter.camera_position = "iso"
    plotter.camera.azimuth = 12
    plotter.camera.elevation = 8
    plotter.camera.zoom(1.08)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if show:
        plotter.show(screenshot=str(output_path), auto_close=True)
    else:
        plotter.show(screenshot=str(output_path), auto_close=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON, help="Unit-cell graph JSON")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="PNG screenshot path")
    parser.add_argument(
        "--mesh-output",
        type=Path,
        default=ROOT / "data" / "unitcell" / "unit_cell_pyvista.vtp",
        help="Combined VTK PolyData output",
    )
    parser.add_argument("--cell-size-mm", type=float, default=4.56)
    parser.add_argument("--strut-diameter-mm", type=float, default=0.35)
    parser.add_argument("--show", action="store_true", help="Open the interactive PyVista window")
    parser.add_argument("--label-nodes", action="store_true", help="Label junction IDs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    render(
        json_path=args.json,
        output_path=args.output,
        mesh_path=args.mesh_output,
        cell_size_mm=args.cell_size_mm,
        strut_diameter_mm=args.strut_diameter_mm,
        show=args.show,
        label_nodes=args.label_nodes,
    )
