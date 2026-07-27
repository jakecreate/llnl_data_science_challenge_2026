"""Register the design STL into the CT/TIFF coordinate system.

The specimen JSON is already registered to the TIFF stack.  This script uses
the shared junction IDs to recover that nominal-JSON -> CT transform, then
maps the nine-cell portion of the STL through the nominal JSON frame.

Example:
    python src/register_stl_to_ct.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pyvista as pv


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOMINAL = ROOT / "data/missing_struts/octet_truss_9x9x9.json"
DEFAULT_REGISTERED = ROOT / (
    "data/missing_struts/registered_jsons/"
    "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json"
)
DEFAULT_STL = ROOT / "data/missing_struts/stls/0.stl"
DEFAULT_OUTPUT = ROOT / "registered_0.stl"
DEFAULT_DIAGNOSTICS = ROOT / "registered_0.registration.json"


def junction_points(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open() as handle:
        data = json.load(handle)
    junctions = sorted(data["junctions"], key=lambda item: item["id"])
    ids = np.asarray([item["id"] for item in junctions], dtype=int)
    points = np.asarray([item["position"] for item in junctions], dtype=float)
    return ids, points


def fit_nominal_to_registered(nominal: Path, registered: Path) -> tuple[np.ndarray, np.ndarray, float]:
    nominal_ids, nominal_points = junction_points(nominal)
    registered_ids, registered_points = junction_points(registered)
    if not np.array_equal(nominal_ids, registered_ids):
        raise ValueError("Nominal and registered JSONs do not have matching junction IDs")

    # Row-vector convention: registered = [nominal, 1] @ coefficients.
    design = np.c_[nominal_points, np.ones(len(nominal_points))]
    coefficients, *_ = np.linalg.lstsq(design, registered_points, rcond=None)
    predicted = design @ coefficients
    residual = float(np.sqrt(np.mean((predicted - registered_points) ** 2)))
    return coefficients[:3], coefficients[3], residual


def crop_extra_y(mesh: pv.PolyData) -> tuple[pv.PolyData, dict[str, float]]:
    """Remove the two extra STL boundary-cell lengths along Y.

    The STL is approximately 9 cells wide in X/Z and 11 cells in Y.  Cropping
    symmetrically to the X extent retains the nine-cell lattice.  The bounds
    are recorded so the choice is visible in the diagnostics file.
    """
    xmin, xmax, ymin, ymax, zmin, zmax = mesh.bounds
    x_extent = xmax - xmin
    y_extent = ymax - ymin
    trim = max(0.0, (y_extent - x_extent) / 2.0)
    cropped = mesh.clip_box(
        bounds=[xmin, xmax, ymin + trim, ymax - trim, zmin, zmax],
        invert=False,
    ).extract_surface(algorithm="dataset_surface")
    return cropped, {
        "original_y_min": float(ymin),
        "original_y_max": float(ymax),
        "trim_each_side": float(trim),
        "target_y_min": float(ymin + trim),
        "target_y_max": float(ymax - trim),
    }


def register_mesh(
    stl_path: Path,
    nominal_json: Path,
    registered_json: Path,
    output_path: Path,
    diagnostics_path: Path,
    crop_y: bool = True,
) -> dict:
    coefficients, translation, json_rms = fit_nominal_to_registered(
        nominal_json, registered_json
    )
    mesh = pv.read(stl_path)
    original_bounds = np.asarray(mesh.bounds, dtype=float)

    crop_info: dict[str, float] = {}
    if crop_y:
        mesh, crop_info = crop_extra_y(mesh)

    points = np.asarray(mesh.points, dtype=float)
    stl_min = points.min(axis=0)
    stl_extent = points.max(axis=0) - stl_min
    nominal_extent = 18.0
    # Use the two unaffected transverse axes for a robust uniform scale.
    scale = nominal_extent / float(np.mean([stl_extent[0], stl_extent[2]]))
    nominal_points = (points - stl_min) * scale
    nominal_extent_measured = nominal_points.max(axis=0) - nominal_points.min(axis=0)

    # Apply the fitted nominal -> CT affine using the same row-vector
    # convention used during the least-squares fit.
    affine = np.vstack([coefficients, translation])
    mesh.points = np.c_[nominal_points, np.ones(len(nominal_points))] @ affine
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.save(output_path)

    result = {
        "stl": str(stl_path),
        "nominal_json": str(nominal_json),
        "registered_json": str(registered_json),
        "output_stl": str(output_path),
        "original_stl_bounds": original_bounds.reshape(3, 2).tolist(),
        "output_ct_bounds": np.asarray(mesh.bounds).reshape(3, 2).tolist(),
        "stl_to_nominal_scale": float(scale),
        "nominal_extent_measured": nominal_extent_measured.tolist(),
        "nominal_to_registered_matrix": coefficients.tolist(),
        "nominal_to_registered_translation": translation.tolist(),
        "json_fit_rms_voxels": json_rms,
        "cropping": crop_info,
    }
    diagnostics_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stl", type=Path, default=DEFAULT_STL)
    parser.add_argument("--nominal-json", type=Path, default=DEFAULT_NOMINAL)
    parser.add_argument("--registered-json", type=Path, default=DEFAULT_REGISTERED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--diagnostics", type=Path, default=DEFAULT_DIAGNOSTICS)
    parser.add_argument(
        "--no-crop-y", action="store_true", help="Keep the STL's extra Y boundary geometry"
    )
    args = parser.parse_args()
    result = register_mesh(
        args.stl,
        args.nominal_json,
        args.registered_json,
        args.output,
        args.diagnostics,
        crop_y=not args.no_crop_y,
    )
    print(f"Saved registered STL: {result['output_stl']}")
    print(f"Saved diagnostics: {args.diagnostics}")
    print(f"Nominal→registered JSON fit RMS: {result['json_fit_rms_voxels']:.3e} voxels")
    print(f"STL→nominal scale: {result['stl_to_nominal_scale']:.6f}")


if __name__ == "__main__":
    main()
