"""Visualize junction positions from a registered missing-strut lattice."""

import json
from pathlib import Path

import numpy as np
import pyvista as pv


JSON_FILENAME = (
    "polyhedron_1x1x1.json"
)


def load_lattice(json_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load junction XYZ positions and strut endpoint indices from JSON."""
    with json_path.open() as file:
        lattice = json.load(file)

    junction_positions = np.asarray(
        [junction["position"] for junction in lattice["junctions"]],
        dtype=float,
    )
    strut_endpoints = np.asarray(
        [
            [strut["junction0"], strut["junction1"]]
            for strut in lattice["struts"]
        ],
        dtype=np.int64,
    )
    return junction_positions, strut_endpoints


def build_unit_cell_mesh(
    junction_positions: np.ndarray,
    strut_endpoints: np.ndarray,
    unit_cells: list[dict],
) -> pv.PolyData:
    """Build a wireframe box around each unit cell in the lattice."""
    corners, lines = [], []
    edge_pairs = (
        (0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
        (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7),
    )
    for cell in unit_cells:
        endpoints = strut_endpoints[np.asarray(cell["struts"], dtype=np.int64)]
        low, high = junction_positions[np.unique(endpoints)].min(0), junction_positions[np.unique(endpoints)].max(0)
        base = len(corners)
        corners.extend([
            [low[0], low[1], low[2]], [high[0], low[1], low[2]],
            [high[0], high[1], low[2]], [low[0], high[1], low[2]],
            [low[0], low[1], high[2]], [high[0], low[1], high[2]],
            [high[0], high[1], high[2]], [low[0], high[1], high[2]],
        ])
        for start, end in edge_pairs:
            lines.extend((2, base + start, base + end))
    return pv.PolyData(np.asarray(corners), lines=np.asarray(lines, dtype=np.int64))


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    json_path = (
        repo_root
        / "data"
        / "unitcell"
        / JSON_FILENAME
    )

    junction_positions, strut_endpoints = load_lattice(json_path)
    with json_path.open() as file:
        unit_cells = json.load(file)["unit_cells"]
    junction_mesh = pv.PolyData(junction_positions)
    junction_mesh["junction_id"] = np.arange(len(junction_positions))

    # A VTK line cell is encoded as: [number_of_points, point_0, point_1].
    strut_lines = np.column_stack(
        [np.full(len(strut_endpoints), 2, dtype=np.int64), strut_endpoints]
    ).ravel()
    strut_mesh = pv.PolyData(junction_positions, lines=strut_lines)
    unit_cell_mesh = build_unit_cell_mesh(junction_positions, strut_endpoints, unit_cells)

    plotter = pv.Plotter()
    strut_actor = plotter.add_mesh(
        strut_mesh,
        color="dimgray",
        line_width=2,
        render_lines_as_tubes=True,
        label="Struts",
    )
    junction_actor = plotter.add_points(
        junction_mesh,
        color="royalblue",
        point_size=5,
        render_points_as_spheres=True,
        scalars="junction_id",
        show_scalar_bar=False,
        label="Junctions",
    )
    unit_cell_actor = plotter.add_mesh(
        unit_cell_mesh, color="gold", line_width=1, opacity=0.8, label="Unit cells"
    )

    def set_strut_thickness(thickness: float) -> None:
        """Update the rendered strut thickness from the slider value."""
        strut_actor.GetProperty().SetLineWidth(float(thickness))
        plotter.render()

    plotter.add_slider_widget(
        set_strut_thickness,
        rng=(1.0, 10.0),
        value=2.0,
        title="Strut thickness",
        pointa=(0.05, 0.1),
        pointb=(0.35, 0.1),
        style="modern",
        interaction_event="always",
    )

    def toggle_actor(actor: pv.Actor, name: str) -> None:
        visible = not actor.GetVisibility()
        actor.SetVisibility(visible)
        print(f"{name}: {'on' if visible else 'off'}")
        plotter.render()

    plotter.add_key_event(
        "s", lambda: toggle_actor(strut_actor, "Struts")
    )
    plotter.add_key_event(
        "j", lambda: toggle_actor(junction_actor, "Junctions")
    )
    plotter.add_key_event(
        "u", lambda: toggle_actor(unit_cell_actor, "Unit cells")
    )
    plotter.add_axes()
    plotter.show_grid()
    plotter.show(
        title=(
            f"{len(junction_positions):,} junctions, "
            f"{len(strut_endpoints):,} struts, {len(unit_cells):,} unit cells "
            "— press S/J/U to toggle"
        )
    )


if __name__ == "__main__":
    main()
