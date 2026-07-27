"""Create a fully connected Brian Tran-frame lattice JSON.

The nominal 9x9x9 JSON contains the complete lattice topology.  The Brian
Tran JSON contains junction coordinates already registered to the CT volume.
This script combines those facts: it transforms the nominal junctions into
the Brian Tran coordinate frame and copies the complete nominal strut and
unit-cell definitions.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOMINAL = ROOT / "data/missing_struts/octet_truss_9x9x9.json"
DEFAULT_BRIAN = ROOT / (
    "data/missing_struts/registered_jsons/"
    "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json"
)
DEFAULT_OUTPUT = ROOT / (
    "data/missing_struts/registered_jsons/"
    "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices_full.json"
)


def load(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


def points_by_id(data: dict) -> tuple[np.ndarray, np.ndarray]:
    junctions = sorted(data["junctions"], key=lambda item: item["id"])
    ids = np.asarray([item["id"] for item in junctions], dtype=int)
    points = np.asarray([item["position"] for item in junctions], dtype=float)
    return ids, points


def fit_transform(nominal: dict, brian: dict) -> tuple[np.ndarray, np.ndarray, float]:
    nominal_ids, nominal_points = points_by_id(nominal)
    brian_ids, brian_points = points_by_id(brian)
    if not np.array_equal(nominal_ids, brian_ids):
        raise ValueError("The two JSON files must contain the same junction IDs")

    # Row-vector convention: brian = [nominal, 1] @ coefficients.
    design = np.c_[nominal_points, np.ones(len(nominal_points))]
    coefficients, *_ = np.linalg.lstsq(design, brian_points, rcond=None)
    predicted = design @ coefficients
    rms = float(np.sqrt(np.mean((predicted - brian_points) ** 2)))
    return coefficients[:3], coefficients[3], rms


def make_full_json(nominal_path: Path, brian_path: Path, output_path: Path) -> dict:
    nominal = load(nominal_path)
    brian = load(brian_path)
    matrix, translation, rms = fit_transform(nominal, brian)

    result = copy.deepcopy(brian)
    nominal_ids, nominal_points = points_by_id(nominal)
    transformed = nominal_points @ matrix + translation
    transformed_by_id = {
        int(junction_id): point.tolist()
        for junction_id, point in zip(nominal_ids, transformed)
    }

    # Keep Brian's junction metadata/indices, but replace coordinates with
    # the exact nominal lattice coordinates in the Brian/CT frame.
    for junction in result["junctions"]:
        junction["position"] = transformed_by_id[int(junction["id"])]

    # These definitions come from the nominal complete lattice.  Deep-copy
    # prevents accidental sharing if this function is imported elsewhere.
    result["struts"] = copy.deepcopy(nominal["struts"])
    result["unit_cells"] = copy.deepcopy(nominal["unit_cells"])
    result["registration"] = {
        "source_nominal_json": str(nominal_path),
        "target_brian_json": str(brian_path),
        "nominal_to_brian_matrix": matrix.tolist(),
        "nominal_to_brian_translation": translation.tolist(),
        "junction_fit_rms": rms,
        "strut_source": "nominal complete 9x9x9 lattice",
    }

    endpoint_ids = {int(j["id"]) for j in result["junctions"]}
    bad = [
        s["id"] for s in result["struts"]
        if s["junction0"] not in endpoint_ids or s["junction1"] not in endpoint_ids
    ]
    if bad:
        raise ValueError(f"Struts reference missing junction IDs: {bad[:10]}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nominal", type=Path, default=DEFAULT_NOMINAL)
    parser.add_argument("--brian", type=Path, default=DEFAULT_BRIAN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = make_full_json(args.nominal, args.brian, args.output)
    print(f"Saved: {args.output}")
    print(f"Junctions: {len(result['junctions'])}")
    print(f"Complete struts: {len(result['struts'])}")
    print(f"Unit cells: {len(result['unit_cells'])}")
    print(f"Junction fit RMS: {result['registration']['junction_fit_rms']:.3e}")


if __name__ == "__main__":
    main()
