"""Build and execute the CT lattice final-report notebook without Jupyter deps.

The generated notebook is standard nbformat v4 JSON.  Code cells are executed in
one shared Python namespace and stdout/Matplotlib outputs are embedded, which
keeps the repository's approved scientific dependency set unchanged.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import textwrap
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = ROOT / "outputs" / "reports" / "ct_lattice_final_report.ipynb"


def markdown(source: str, cell_id: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": textwrap.dedent(source).strip() + "\n",
    }


def code(source: str, cell_id: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {},
        "outputs": [],
        "source": textwrap.dedent(source).strip() + "\n",
    }


CELLS = [
    markdown(
        """
        # 9×9×9 Octet Lattice: CT-Only EDA Final Report

        **Source:** `data/9x9x9_octet_lattice.tif` (read-only)  
        **Method contract:** `outputs/reports/ct_lattice_analysis_method_plan.md`

        This executable report implements the prescribed three-stage workflow:

        1. raw-volume QC and a ranked segmentation ensemble;
        2. CT-only skeleton graph and logical strut/node recovery;
        3. strut/node morphometry using local inscribed and volume–length equivalent diameters.

        The TIFF contains no physical-resolution metadata. All distances and diameters are therefore
        labeled in **original-voxel units**. To make 3D morphology reproducible on a workstation, the
        raw intensities are quality-controlled through a stratified sample and the spatial analysis is
        performed on every fourth voxel along each axis. The resulting analysis-grid spacing is
        `(4, 4, 4)` original voxels; no claim of micrometre-scale calibration is made.

        Generated tables and lossless intermediate arrays are written only to `outputs/features/`;
        figures, the execution manifest, and this notebook are written only to `outputs/reports/`.
        """,
        "title-scope",
    ),
    code(
        """
        from __future__ import annotations

        import hashlib
        import importlib.metadata as md
        import json
        import math
        import platform
        import sys
        import warnings
        from collections import defaultdict
        from pathlib import Path

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx
        import numpy as np
        import pandas as pd
        import tifffile
        from scipy import ndimage as ndi
        from skan import Skeleton, summarize
        from skimage.filters import threshold_otsu
        from skimage.morphology import remove_small_holes, remove_small_objects, skeletonize

        warnings.filterwarnings("ignore", category=FutureWarning)
        plt.rcParams.update({"figure.dpi": 120, "savefig.dpi": 160, "axes.grid": True})

        def find_repo_root() -> Path:
            for candidate in (Path.cwd().resolve(), *Path.cwd().resolve().parents):
                if (candidate / "data" / "9x9x9_octet_lattice.tif").is_file():
                    return candidate
            raise FileNotFoundError("Run this notebook from inside the repository.")

        ROOT = find_repo_root()
        DATA_PATH = (ROOT / "data" / "9x9x9_octet_lattice.tif").resolve()
        FEATURE_DIR = (ROOT / "outputs" / "features").resolve()
        REPORT_DIR = (ROOT / "outputs" / "reports").resolve()
        FEATURE_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        def guarded_output(directory: Path, name: str) -> Path:
            path = (directory / name).resolve()
            output_root = (ROOT / "outputs").resolve()
            if output_root not in path.parents:
                raise ValueError(f"Refusing output outside outputs/: {path}")
            if (ROOT / "data").resolve() in path.parents:
                raise ValueError(f"Refusing write inside data/: {path}")
            return path

        CONFIG = {
            "dataset_id": "9x9x9_octet_lattice",
            "axis_convention": "ZYX",
            "downsample_factor": 4,
            "analysis_spacing_original_voxels": [4.0, 4.0, 4.0],
            "raw_qc_xy_stride": 4,
            "normalization_percentiles": [0.5, 99.5],
            "min_component_analysis_voxels": 16,
            "max_bounded_hole_analysis_voxels": 7,
            "ensemble_top_k": 3,
            "ensemble_vote_fraction": 2 / 3,
            "spur_prune_length_original_voxels": 16.0,
            "junction_exclusion_radius_original_voxels": 8.0,
            "connectivity": 26,
            "random_seed": 20260731,
        }
        SEGMENTATION_DIAGNOSTIC_AXIS0_SLICE = 70
        SKELETON_DIAGNOSTIC_AXIS0_SLICE = 150
        CONFIG_HASH = hashlib.sha256(json.dumps(CONFIG, sort_keys=True).encode()).hexdigest()[:16]
        SPACING = np.asarray(CONFIG["analysis_spacing_original_voxels"], dtype=float)
        SOFTWARE = {name: md.version(name) for name in [
            "numpy", "scipy", "scikit-image", "tifffile", "matplotlib",
            "pandas", "networkx", "skan", "porespy"
        ]}

        print(f"Repository: {ROOT}")
        print(f"Input (read-only): {DATA_PATH.relative_to(ROOT)}")
        print(f"Configuration hash: {CONFIG_HASH}")
        print(f"Python: {platform.python_version()}; analysis units: original voxels")
        """,
        "imports-config",
    ),
    markdown(
        """
        ## 1. Reusable method implementation

        The functions below make each step explicit and deterministic. Candidate selection is based on a
        recorded composite score—not an implicit visual choice. Skeleton junction voxels are grouped into
        logical nodes before maximal paths are traced, avoiding the common error of treating every junction
        voxel as a separate lattice node.
        """,
        "method-heading",
    ),
    code(
        """
        OFFSETS_26 = tuple(
            (dz, dy, dx)
            for dz in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if (dz, dy, dx) != (0, 0, 0)
        )
        STRUCTURE_26 = np.ones((3, 3, 3), dtype=np.uint8)
        NEIGHBOR_KERNEL = STRUCTURE_26.copy()
        NEIGHBOR_KERNEL[1, 1, 1] = 0

        def robust_z(values: np.ndarray) -> np.ndarray:
            values = np.asarray(values, dtype=float)
            med = np.nanmedian(values)
            mad = np.nanmedian(np.abs(values - med))
            return 0.6745 * (values - med) / max(mad, np.finfo(float).eps)

        def ring_severity(image: np.ndarray) -> float:
            # Heuristic radial residual-energy fraction on a representative slice.
            a = np.asarray(image, dtype=np.float32)
            a = (a - np.percentile(a, 1)) / max(np.percentile(a, 99) - np.percentile(a, 1), 1e-9)
            a = np.clip(a, 0, 1)
            yy, xx = np.indices(a.shape)
            cy, cx = (np.asarray(a.shape) - 1) / 2
            rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
            bins = np.minimum(rr.astype(int), int(rr.max()))
            radial_mean = ndi.mean(a, labels=bins, index=np.arange(bins.max() + 1))
            radial_model = radial_mean[bins]
            radial_energy = float(np.var(radial_model))
            total_energy = float(np.var(a))
            return radial_energy / max(total_energy, 1e-12)

        def beam_hardening_severity(image: np.ndarray) -> float:
            # Absolute center-to-boundary drift standardized by support intensity spread.
            a = np.asarray(image, dtype=np.float32)
            t = threshold_otsu(a)
            support = a > t
            yy, xx = np.indices(a.shape)
            cy, cx = (np.asarray(a.shape) - 1) / 2
            rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
            support_r = rr[support]
            if support_r.size < 32:
                return float("nan")
            rmax = np.percentile(support_r, 95)
            center = support & (rr <= 0.35 * rmax)
            boundary = support & (rr >= 0.70 * rmax) & (rr <= rmax)
            spread = np.percentile(a[support], 90) - np.percentile(a[support], 10)
            return abs(float(a[center].mean() - a[boundary].mean())) / max(float(spread), 1e-9)

        def normalize_volume(volume: np.ndarray, percentiles=(0.5, 99.5)):
            lo, hi = np.percentile(volume, percentiles)
            if not np.isfinite([lo, hi]).all() or hi <= lo:
                raise ValueError("Volume is constant or has invalid intensity range.")
            normalized = np.clip((volume.astype(np.float32) - lo) / (hi - lo), 0, 1)
            return normalized, float(lo), float(hi)

        def phansalkar_mask(normalized: np.ndarray, window: int, k: float, bright=True) -> np.ndarray:
            local_mean = ndi.uniform_filter(normalized, size=window, mode="reflect")
            local_mean_sq = ndi.uniform_filter(normalized * normalized, size=window, mode="reflect")
            local_std = np.sqrt(np.maximum(local_mean_sq - local_mean * local_mean, 0))
            threshold = local_mean * (1 + 2 * np.exp(-10 * local_mean) + k * (local_std / 0.5 - 1))
            return normalized > threshold if bright else normalized < threshold

        def clean_mask(mask: np.ndarray) -> np.ndarray:
            cleaned = remove_small_objects(mask.astype(bool), max_size=CONFIG["min_component_analysis_voxels"] - 1)
            return remove_small_holes(cleaned, max_size=CONFIG["max_bounded_hole_analysis_voxels"])

        def boundary_fraction(mask: np.ndarray) -> float:
            boundary = np.zeros(mask.shape, dtype=bool)
            boundary[[0, -1], :, :] = True
            boundary[:, [0, -1], :] = True
            boundary[:, :, [0, -1]] = True
            return float(np.count_nonzero(mask & boundary) / max(np.count_nonzero(mask), 1))

        def candidate_metrics(name: str, mask: np.ndarray, params: dict) -> dict:
            labels, count = ndi.label(mask, structure=STRUCTURE_26)
            sizes = np.bincount(labels.ravel())[1:]
            foreground = int(mask.sum())
            largest_fraction = float(sizes.max() / foreground) if foreground and sizes.size else 0.0
            z_fraction = mask.mean(axis=(1, 2))
            slice_cv = float(z_fraction.std() / max(z_fraction.mean(), 1e-12))
            vf = float(mask.mean())
            accepted = 0.005 < vf < 0.75 and count < 500 and largest_fraction > 0.80
            vf_score = math.exp(-((vf - 0.13) / 0.12) ** 2)
            stability_score = 1 - min(slice_cv, 1.0)
            score = (
                0.45 * largest_fraction + 0.25 * vf_score + 0.25 * stability_score
                - 0.03 * math.log1p(count) / math.log(501) - 0.02 * boundary_fraction(mask)
            )
            return {
                "candidate": name, **params, "accepted": accepted, "score": score,
                "volume_fraction": vf, "component_count": int(count),
                "largest_component_fraction": largest_fraction,
                "boundary_foreground_fraction": boundary_fraction(mask),
                "slice_fraction_cv": slice_cv,
            }

        def neighbors(coord, shape):
            z, y, x = coord
            for dz, dy, dx in OFFSETS_26:
                q = (z + dz, y + dy, x + dx)
                if 0 <= q[0] < shape[0] and 0 <= q[1] < shape[1] and 0 <= q[2] < shape[2]:
                    yield q

        def logical_skeleton_graph(skeleton: np.ndarray, spacing: np.ndarray, skan_labels=None):
            # Group junction clusters and trace maximal degree-two paths.
            skeleton = skeleton.astype(bool)
            degree_image = ndi.convolve(skeleton.astype(np.uint8), NEIGHBOR_KERNEL, mode="constant", cval=0)
            junction_labels, n_junctions = ndi.label(skeleton & (degree_image > 2), structure=STRUCTURE_26)
            node_labels = junction_labels.astype(np.int32)
            next_id = int(n_junctions)
            for coord in np.argwhere(skeleton & (degree_image <= 1)):
                next_id += 1
                node_labels[tuple(coord)] = next_id

            node_coords_by_id = defaultdict(list)
            all_node_coords = np.argwhere(node_labels > 0)
            for coord, label_value in zip(all_node_coords, node_labels[tuple(all_node_coords.T)]):
                node_coords_by_id[int(label_value)].append(tuple(int(v) for v in coord))

            node_rows = []
            for node_id in range(1, next_id + 1):
                coords = np.asarray(node_coords_by_id[node_id], dtype=np.int32)
                centroid = coords.mean(axis=0)
                physical = centroid * spacing
                boundary_distance = float(np.min(np.r_[physical, (np.asarray(skeleton.shape) - 1 - centroid) * spacing]))
                node_rows.append({
                    "node_id": node_id, "kind_preprune": "junction" if node_id <= n_junctions else "terminal_or_isolated",
                    "voxel_count": len(coords), "z": centroid[0], "y": centroid[1], "x": centroid[2],
                    "z_original_voxels": physical[0], "y_original_voxels": physical[1], "x_original_voxels": physical[2],
                    "boundary_distance_original_voxels": boundary_distance,
                })

            visited_links = set()
            paths = []
            shape = skeleton.shape

            def link_key(a, b):
                return tuple(sorted((np.ravel_multi_index(a, shape), np.ravel_multi_index(b, shape))))

            for node_id in range(1, next_id + 1):
                for start in node_coords_by_id[node_id]:
                    for q in neighbors(start, shape):
                        if not skeleton[q] or node_labels[q] == node_id:
                            continue
                        first_key = link_key(start, q)
                        if first_key in visited_links:
                            continue
                        path = [start, q]
                        visited_links.add(first_key)
                        prev, cur = start, q
                        while node_labels[cur] == 0:
                            options = [r for r in neighbors(cur, shape) if skeleton[r] and r != prev]
                            if not options:
                                break
                            nxt = options[0]
                            visited_links.add(link_key(cur, nxt))
                            path.append(nxt)
                            prev, cur = cur, nxt
                        end_id = int(node_labels[cur])
                        if end_id > 0:
                            coords = np.asarray(path, dtype=np.int32)
                            deltas = np.diff(coords, axis=0) * spacing
                            length = float(np.linalg.norm(deltas, axis=1).sum())
                            skan_ids = []
                            if skan_labels is not None:
                                labels_here = np.unique(skan_labels[tuple(coords.T)])
                                skan_ids = [int(v - 1) for v in labels_here if v > 0]
                            paths.append({
                                "edge_id": len(paths) + 1, "node_u": node_id, "node_v": end_id,
                                "coords": coords, "length": length, "skan_branch_ids": skan_ids,
                            })

            covered = np.zeros_like(skeleton, dtype=bool)
            for item in paths:
                covered[tuple(item["coords"].T)] = True
            accounting = float(np.count_nonzero(covered & skeleton) / max(np.count_nonzero(skeleton), 1))
            return pd.DataFrame(node_rows), paths, degree_image, accounting

        def prune_short_terminal_spurs(paths: list[dict], threshold: float):
            retained = {p["edge_id"] for p in paths}
            removed = []
            for iteration in range(10):
                degree = defaultdict(int)
                for p in paths:
                    if p["edge_id"] in retained:
                        degree[p["node_u"]] += 1
                        degree[p["node_v"]] += 1
                prune = [p for p in paths if p["edge_id"] in retained and p["length"] < threshold
                         and (degree[p["node_u"]] == 1 or degree[p["node_v"]] == 1)]
                if not prune:
                    break
                for p in prune:
                    retained.remove(p["edge_id"])
                    removed.append({"edge_id": p["edge_id"], "length": p["length"], "iteration": iteration + 1})
            return retained, pd.DataFrame(removed, columns=["edge_id", "length", "iteration"])

        def save_and_show(fig, filename: str):
            fig.tight_layout()
            fig.savefig(guarded_output(REPORT_DIR, filename), bbox_inches="tight")
            plt.show()
        """,
        "method-functions",
    ),
    markdown(
        """
        ## 2. Raw-volume QC and segmentation ensemble

        The original array is memory-mapped and never modified. Robust intensity percentiles come from a
        regular 3D sample; slice trends use every Z slice and every fourth in-plane pixel. Segmentation is
        evaluated on the documented 4× grid using three global Otsu perturbations and four 3D Phansalkar
        configurations. Small components and only small bounded holes are removed—intentional lattice pores
        are not globally closed.
        """,
        "segmentation-heading",
    ),
    code(
        """
        raw = tifffile.memmap(DATA_PATH)
        if raw.ndim != 3 or not np.issubdtype(raw.dtype, np.number):
            raise ValueError(f"Expected a numeric 3D TIFF, received {raw.shape} {raw.dtype}")
        raw_shape = tuple(int(v) for v in raw.shape)
        raw_sample = np.asarray(raw[::8, ::8, ::8], dtype=np.float32)
        if not np.isfinite(raw_sample).all():
            raise ValueError("Non-finite values detected in TIFF sample.")

        sample_percentiles = np.percentile(raw_sample, [0, 0.1, 0.5, 1, 25, 50, 75, 99, 99.5, 99.9, 100])
        z_mean, z_std, z_range = [], [], []
        for z in range(raw.shape[0]):
            plane = np.asarray(raw[z, ::CONFIG["raw_qc_xy_stride"], ::CONFIG["raw_qc_xy_stride"]], dtype=np.float32)
            z_mean.append(float(plane.mean()))
            z_std.append(float(plane.std()))
            p05, p95 = np.percentile(plane, [5, 95])
            z_range.append(float(p95 - p05))
        z_mean, z_std, z_range = map(np.asarray, (z_mean, z_std, z_range))
        jump_z = robust_z(np.abs(np.diff(z_mean, prepend=z_mean[0])))
        low_contrast_z = -robust_z(z_range)
        flagged_jump_slices = np.flatnonzero(jump_z > 5).tolist()
        flagged_low_contrast_slices = np.flatnonzero(low_contrast_z > 5).tolist()

        representative = np.asarray(raw[raw.shape[0] // 2, ::2, ::2], dtype=np.float32)
        ring_score_value = ring_severity(representative)
        beam_score_value = beam_hardening_severity(representative)

        factor = CONFIG["downsample_factor"]
        analysis_volume = np.asarray(raw[::factor, ::factor, ::factor], dtype=np.float32)
        normalized, clip_lo, clip_hi = normalize_volume(analysis_volume, CONFIG["normalization_percentiles"])
        otsu = float(threshold_otsu(normalized))

        candidate_masks = {}
        candidate_specs = []
        for name, multiplier in [("otsu_low", 0.93), ("otsu", 1.0), ("otsu_high", 1.07)]:
            candidate_specs.append((name, clean_mask(normalized > otsu * multiplier),
                                    {"method": "otsu", "threshold_multiplier": multiplier,
                                     "window": np.nan, "k": np.nan, "foreground": "bright"}))
        for window, k in [(15, 0.15), (15, 0.25), (25, 0.15), (25, 0.25)]:
            name = f"phansalkar_w{window}_k{k:.2f}"
            candidate_specs.append((name, clean_mask(phansalkar_mask(normalized, window, k, bright=True)),
                                    {"method": "phansalkar", "threshold_multiplier": np.nan,
                                     "window": window, "k": k, "foreground": "bright"}))

        sweep_rows = []
        for name, candidate, params in candidate_specs:
            candidate_masks[name] = candidate
            sweep_rows.append(candidate_metrics(name, candidate, params))
        segmentation_sweep = pd.DataFrame(sweep_rows).sort_values("score", ascending=False).reset_index(drop=True)
        accepted = segmentation_sweep.query("accepted").head(CONFIG["ensemble_top_k"])
        if len(accepted) < CONFIG["ensemble_top_k"]:
            raise RuntimeError("Fewer than three segmentation candidates passed acceptance checks.")
        selected_names = accepted["candidate"].tolist()
        vote_probability = np.mean([candidate_masks[name] for name in selected_names], axis=0, dtype=np.float32)
        selected_mask = clean_mask(vote_probability >= CONFIG["ensemble_vote_fraction"])
        labels, component_count = ndi.label(selected_mask, structure=STRUCTURE_26)
        component_sizes = np.bincount(labels.ravel())[1:]
        largest_label = int(np.argmax(component_sizes) + 1)
        selected_mask = labels == largest_label
        disagreement = (1 - np.abs(2 * vote_probability - 1)).astype(np.float32)
        uncertain_fraction = float(np.mean(disagreement > 0))

        mask_path = guarded_output(FEATURE_DIR, "ct_selected_mask_ds4.tif")
        disagreement_path = guarded_output(FEATURE_DIR, "ct_segmentation_disagreement_ds4.tif")
        tifffile.imwrite(mask_path, selected_mask.astype(np.uint8), photometric="minisblack", compression="zlib")
        tifffile.imwrite(disagreement_path, disagreement, photometric="minisblack", compression="zlib")
        segmentation_sweep.to_csv(guarded_output(FEATURE_DIR, "segmentation_sweep.csv"), index=False)

        qc_row = {
            "dataset_id": CONFIG["dataset_id"], "source_path": str(DATA_PATH.relative_to(ROOT)),
            "shape_z": raw_shape[0], "shape_y": raw_shape[1], "shape_x": raw_shape[2],
            "dtype": str(raw.dtype), "axis_convention": CONFIG["axis_convention"],
            "voxel_spacing": "unknown", "analysis_spacing_original_voxels": "4,4,4",
            "file_bytes": DATA_PATH.stat().st_size, "sample_min": sample_percentiles[0],
            "sample_max": sample_percentiles[-1], "sample_mean": float(raw_sample.mean()),
            "sample_std": float(raw_sample.std()), "clip_low": clip_lo, "clip_high": clip_hi,
            "sample_saturated_low_fraction": float(np.mean(raw_sample == np.iinfo(raw.dtype).min)),
            "sample_saturated_high_fraction": float(np.mean(raw_sample == np.iinfo(raw.dtype).max)),
            "ring_severity": ring_score_value, "beam_hardening_severity": beam_score_value,
            "abrupt_slice_count": len(flagged_jump_slices), "low_contrast_slice_count": len(flagged_low_contrast_slices),
            "otsu_normalized": otsu, "selected_candidates": ";".join(selected_names),
            "selected_volume_fraction": float(selected_mask.mean()),
            "pre_largest_component_count": int(component_count),
            "largest_component_retained_fraction": float(component_sizes.max() / max(component_sizes.sum(), 1)),
            "uncertain_voxel_fraction": uncertain_fraction, "configuration_hash": CONFIG_HASH,
            "segmentation_accepted": True,
        }
        ct_volume_qc = pd.DataFrame([qc_row])
        ct_volume_qc.to_csv(guarded_output(FEATURE_DIR, "ct_volume_qc.csv"), index=False)

        print(f"Raw shape/dtype: {raw_shape} / {raw.dtype}; analysis shape: {analysis_volume.shape}")
        print(f"Intensity clip: [{clip_lo:.1f}, {clip_hi:.1f}], normalized Otsu: {otsu:.4f}")
        print(f"Selected ensemble: {selected_names}")
        print(f"Foreground fraction: {selected_mask.mean():.4f}; uncertainty: {uncertain_fraction:.4f}")
        print(f"Raw-slice flags: {len(flagged_jump_slices)} abrupt, {len(flagged_low_contrast_slices)} low contrast")
        display(segmentation_sweep.round(4)) if "display" in globals() else print(segmentation_sweep.round(4).to_string(index=False))
        """,
        "run-segmentation",
    ),
    code(
        """
        example_slice = SEGMENTATION_DIAGNOSTIC_AXIS0_SLICE
        if not 0 <= example_slice < selected_mask.shape[0]:
            raise IndexError(
                f"Diagnostic axis-0 slice {example_slice} is outside the analysis volume "
                f"with {selected_mask.shape[0]} slices."
            )
        fig, axes = plt.subplots(2, 3, figsize=(14, 8))
        axes[0, 0].imshow(normalized[example_slice], cmap="gray")
        axes[0, 0].set_title(f"Normalized CT, axis-0 slice {example_slice}")
        axes[0, 1].imshow(selected_mask[example_slice], cmap="gray")
        axes[0, 1].set_title(f"Selected ensemble mask, axis-0 slice {example_slice}")
        axes[0, 2].imshow(normalized[example_slice], cmap="gray")
        axes[0, 2].contour(selected_mask[example_slice], levels=[0.5], colors="lime", linewidths=0.5)
        axes[0, 2].set_title(f"Segmentation overlay, axis-0 slice {example_slice}")
        axes[1, 0].hist(raw_sample.ravel(), bins=128, color="steelblue")
        axes[1, 0].axvline(clip_lo, color="orange", label="clip"); axes[1, 0].axvline(clip_hi, color="orange")
        axes[1, 0].set_title("Stratified raw histogram"); axes[1, 0].legend()
        axes[1, 1].plot(z_mean, label="mean"); axes[1, 1].plot(z_std, label="std")
        axes[1, 1].set_title("Raw Z-slice intensity trends"); axes[1, 1].legend()
        axes[1, 2].imshow(disagreement[example_slice], cmap="magma", vmin=0, vmax=1)
        axes[1, 2].set_title(f"Ensemble disagreement, axis-0 slice {example_slice}")
        for ax in axes.flat:
            if ax.images: ax.axis("off")
        save_and_show(fig, "ct_segmentation_diagnostics.png")

        fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
        axes[0].plot(z_range); axes[0].set_title("Z-slice robust range")
        axes[1].plot(jump_z); axes[1].axhline(5, color="red", ls="--"); axes[1].set_title("Abrupt-jump robust z")
        axes[2].plot(low_contrast_z); axes[2].axhline(5, color="red", ls="--"); axes[2].set_title("Low-contrast robust z")
        for ax in axes: ax.set_xlabel("raw Z index")
        save_and_show(fig, "ct_qc_slice_trends.png")
        """,
        "segmentation-figures",
    ),
    markdown(
        """
        ## 3. Skeleton graph and strut–node recovery

        The accepted mask is skeletonized with Lee's 3D algorithm. Skan provides an independent branch
        decomposition; its original branch identifiers are associated with each logical traced edge. Under
        26-connectivity, adjacent degree>2 voxels are grouped into junction regions, terminals are explicit
        logical nodes, and degree-two interiors are traced exactly once. Terminal spurs shorter than 16
        original voxels are pruned iteratively and retained in an audit table.
        """,
        "graph-heading",
    ),
    code(
        """
        skeleton = skeletonize(selected_mask, method="lee").astype(bool)
        if not np.all(selected_mask[skeleton]):
            raise AssertionError("Skeleton escaped the selected mask.")
        skan_skeleton = Skeleton(skeleton, spacing=tuple(SPACING))
        skan_table = summarize(skan_skeleton, separator="_")
        skan_label_image = skan_skeleton.path_label_image()

        node_table, traced_paths, degree_image, skeleton_accounting = logical_skeleton_graph(
            skeleton, SPACING, skan_labels=skan_label_image
        )
        retained_ids, pruned_spurs = prune_short_terminal_spurs(
            traced_paths, CONFIG["spur_prune_length_original_voxels"]
        )

        edge_rows = []
        for p in traced_paths:
            coords = p["coords"]
            delta = (coords[-1] - coords[0]) * SPACING
            euclidean = float(np.linalg.norm(delta))
            orientation = delta / euclidean if euclidean > 0 else np.zeros(3)
            edge_rows.append({
                "edge_id": p["edge_id"], "node_u": p["node_u"], "node_v": p["node_v"],
                "path_length_original_voxels": p["length"], "euclidean_length_original_voxels": euclidean,
                "tortuosity": p["length"] / euclidean if euclidean > 0 else np.nan,
                "orientation_z": orientation[0], "orientation_y": orientation[1], "orientation_x": orientation[2],
                "path_sample_count": len(coords),
                "boundary_contact": bool(np.any((coords <= 1) | (coords >= np.asarray(skeleton.shape) - 2))),
                "original_skan_branch_ids": ";".join(map(str, p["skan_branch_ids"])),
                "retained_after_pruning": p["edge_id"] in retained_ids,
            })
        skeleton_edges = pd.DataFrame(edge_rows)
        retained_edges = skeleton_edges.query("retained_after_pruning").copy()

        graph = nx.MultiGraph()
        for row in node_table.itertuples():
            graph.add_node(int(row.node_id))
        path_lookup = {p["edge_id"]: p for p in traced_paths}
        for row in retained_edges.itertuples():
            graph.add_edge(int(row.node_u), int(row.node_v), key=int(row.edge_id), edge_id=int(row.edge_id))
        active_nodes = sorted(n for n, degree in graph.degree() if degree > 0)
        graph = graph.subgraph(active_nodes).copy()
        components = list(nx.connected_components(graph))
        component_map = {node: i + 1 for i, comp in enumerate(sorted(components, key=len, reverse=True)) for node in comp}
        node_degree = dict(graph.degree())
        incident = defaultdict(list)
        for row in retained_edges.itertuples():
            incident[int(row.node_u)].append(int(row.edge_id)); incident[int(row.node_v)].append(int(row.edge_id))
        node_table["degree"] = node_table["node_id"].map(node_degree).fillna(0).astype(int)
        node_table["component_id"] = node_table["node_id"].map(component_map).fillna(0).astype(int)
        node_table["incident_edge_ids"] = node_table["node_id"].map(lambda n: ";".join(map(str, incident.get(n, []))))
        node_table["kind_postprune"] = np.select(
            [node_table.degree == 0, node_table.degree == 1, node_table.degree == 2, node_table.degree >= 3],
            ["inactive", "terminal", "degree_two", "junction"], default="unknown"
        )

        active_node_count = len(active_nodes)
        edge_count = len(retained_edges)
        component_count_graph = len(components)
        cycle_rank = edge_count - active_node_count + component_count_graph
        graph_summary = pd.DataFrame([{
            "dataset_id": CONFIG["dataset_id"], "segmentation_id": CONFIG_HASH,
            "skeleton_voxel_count": int(skeleton.sum()), "skan_branch_count": int(len(skan_table)),
            "logical_node_count": active_node_count, "logical_edge_count": edge_count,
            "endpoint_count": int(sum(v == 1 for v in node_degree.values())),
            "junction_count": int(sum(v >= 3 for v in node_degree.values())),
            "component_count": component_count_graph, "cycle_rank": int(cycle_rank),
            "largest_component_node_fraction": max(map(len, components), default=0) / max(active_node_count, 1),
            "pruned_spur_count": len(pruned_spurs), "skeleton_accounting_fraction": skeleton_accounting,
            "connectivity": 26, "configuration_hash": CONFIG_HASH,
        }])

        node_table.to_csv(guarded_output(FEATURE_DIR, "skeleton_nodes.csv"), index=False)
        skeleton_edges.to_csv(guarded_output(FEATURE_DIR, "skeleton_edges.csv"), index=False)
        graph_summary.to_csv(guarded_output(FEATURE_DIR, "skeleton_graph_summary.csv"), index=False)
        pruned_spurs.to_csv(guarded_output(FEATURE_DIR, "skeleton_pruned_spurs.csv"), index=False)

        graph_json = {
            "metadata": {"dataset_id": CONFIG["dataset_id"], "segmentation_id": CONFIG_HASH,
                         "shape": list(selected_mask.shape), "axis_convention": "ZYX",
                         "spacing": SPACING.tolist(), "units": "original_voxels"},
            "nodes": node_table.query("degree > 0").to_dict(orient="records"),
            "edges": [
                {"edge_id": p["edge_id"], "node_u": p["node_u"], "node_v": p["node_v"],
                 "coordinates_zyx_analysis_grid": p["coords"].tolist(),
                 "original_skan_branch_ids": p["skan_branch_ids"]}
                for p in traced_paths if p["edge_id"] in retained_ids
            ],
        }
        guarded_output(FEATURE_DIR, "skeleton_graph.json").write_text(json.dumps(graph_json), encoding="utf-8")

        print(graph_summary.T.to_string(header=False))
        print(f"Skan branches linked to {len(traced_paths)} logical paths; {len(pruned_spurs)} terminal spurs audited.")
        """,
        "run-graph",
    ),
    code(
        """
        example_slice = SKELETON_DIAGNOSTIC_AXIS0_SLICE
        if not 0 <= example_slice < skeleton.shape[0]:
            raise IndexError(
                f"Diagnostic axis-0 slice {example_slice} is outside the analysis volume "
                f"with {skeleton.shape[0]} slices."
            )
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
        ax = fig.add_subplot(1, 2, 2, projection="3d")
        diagnostic_edges = retained_edges.nlargest(min(1800, len(retained_edges)), "path_length_original_voxels")
        for edge_id in diagnostic_edges.edge_id:
            c = path_lookup[int(edge_id)]["coords"] * SPACING
            ax.plot(c[:, 2], c[:, 1], c[:, 0], lw=0.35, alpha=0.35, color="navy")
        active_node_rows = node_table.query("degree >= 3")
        ax.scatter(active_node_rows.x_original_voxels, active_node_rows.y_original_voxels,
                   active_node_rows.z_original_voxels, s=2, c="crimson", alpha=0.35)
        ax.set(xlabel="X", ylabel="Y", zlabel="Z", title="Longest retained logical edges + junctions")
        save_and_show(fig, "skeleton_graph_diagnostics.png")
        """,
        "graph-figure",
    ),
    markdown(
        """
        ## 4. Strut and node morphometry

        The foreground Euclidean distance transform uses the analysis spacing, so sampled radii are already
        in original-voxel units. Per-edge diameter statistics exclude the first/last 8 original voxels to
        limit junction thickening. A nearest-centerline partition supplies a separate volume–length equivalent
        diameter. It is not conflated with the local inscribed diameter. Reliability and uncertainty fields
        remain explicit for short or junction-dominated edges.
        """,
        "morphometry-heading",
    ),
    code(
        """
        edt = ndi.distance_transform_edt(selected_mask, sampling=tuple(SPACING)).astype(np.float32)
        exclusion_radius = CONFIG["junction_exclusion_radius_original_voxels"]
        morph_rows = []
        sample_cache = {}

        for edge_row in retained_edges.itertuples():
            p = path_lookup[int(edge_row.edge_id)]
            coords = p["coords"]
            diameters = 2 * edt[tuple(coords.T)]
            disagreement_samples = disagreement[tuple(coords.T)]
            if len(coords) > 1:
                steps = np.linalg.norm(np.diff(coords, axis=0) * SPACING, axis=1)
                from_start = np.r_[0, np.cumsum(steps)]
                from_end = from_start[-1] - from_start
            else:
                from_start = from_end = np.zeros(1)
            excluded = (from_start <= exclusion_radius) | (from_end <= exclusion_radius)
            valid = ~excluded
            d = diameters[valid]
            sample_cache[int(edge_row.edge_id)] = {"coords": coords, "diameters": diameters, "valid": valid}
            if len(d):
                q10, q25, q50, q75, q90 = np.percentile(d, [10, 25, 50, 75, 90])
                cv = float(np.std(d) / max(np.mean(d), 1e-9))
                position = from_start[valid] / max(from_start[-1], 1e-9)
                endpoint_d = d[(position <= 0.2) | (position >= 0.8)]
                midspan_d = d[(position >= 0.3) & (position <= 0.7)]
                taper = (np.median(endpoint_d) - np.median(midspan_d)) / max(np.median(midspan_d), 1e-9) if len(endpoint_d) and len(midspan_d) else np.nan
            else:
                q10 = q25 = q50 = q75 = q90 = cv = taper = np.nan
            excluded_fraction = float(excluded.mean())
            uncertainty_score = float(np.clip(
                0.5 * disagreement_samples.mean() + 0.3 * excluded_fraction + 0.2 / math.sqrt(max(len(d), 1)), 0, 1
            ))
            reliable = bool(len(d) >= 3 and excluded_fraction <= 0.60 and edge_row.path_length_original_voxels > max(q50 if np.isfinite(q50) else np.inf, 0))
            morph_rows.append({
                "edge_id": int(edge_row.edge_id), "node_u": int(edge_row.node_u), "node_v": int(edge_row.node_v),
                "length_original_voxels": edge_row.path_length_original_voxels,
                "valid_sample_count": int(len(d)), "junction_excluded_fraction": excluded_fraction,
                "diameter_mean_original_voxels": float(np.mean(d)) if len(d) else np.nan,
                "diameter_median_original_voxels": q50,
                "diameter_std_original_voxels": float(np.std(d)) if len(d) else np.nan,
                "diameter_min_original_voxels": float(np.min(d)) if len(d) else np.nan,
                "diameter_max_original_voxels": float(np.max(d)) if len(d) else np.nan,
                "diameter_iqr_original_voxels": q75 - q25 if len(d) else np.nan,
                "diameter_q10_original_voxels": q10, "diameter_q25_original_voxels": q25,
                "diameter_q75_original_voxels": q75, "diameter_q90_original_voxels": q90,
                "diameter_coefficient_of_variation": cv, "robust_taper": taper,
                "slenderness_length_over_median_diameter": edge_row.path_length_original_voxels / q50 if np.isfinite(q50) and q50 > 0 else np.nan,
                "mean_segmentation_disagreement": float(disagreement_samples.mean()),
                "uncertainty_score": uncertainty_score, "reliable_diameter": reliable,
            })
        strut_morphometry = pd.DataFrame(morph_rows)

        # Optional edge-volume estimate: partition foreground voxels by nearest retained centerline label.
        edge_label_image = np.zeros(selected_mask.shape, dtype=np.int32)
        edge_label_to_id = {}
        for label_value, edge_id in enumerate(strut_morphometry.edge_id, start=1):
            edge_label_to_id[label_value] = int(edge_id)
            coords = sample_cache[int(edge_id)]["coords"]
            edge_label_image[tuple(coords.T)] = label_value
        nearest_indices = ndi.distance_transform_edt(edge_label_image == 0, return_distances=False, return_indices=True)
        nearest_labels = edge_label_image[tuple(nearest_indices)]
        volume_counts = np.bincount(nearest_labels[selected_mask], minlength=len(edge_label_to_id) + 1)
        voxel_volume = float(np.prod(SPACING))
        volume_by_edge = {edge_id: float(volume_counts[label] * voxel_volume) for label, edge_id in edge_label_to_id.items()}
        strut_morphometry["assigned_volume_original_voxels_cubed"] = strut_morphometry.edge_id.map(volume_by_edge)
        strut_morphometry["volume_length_equivalent_diameter_original_voxels"] = np.sqrt(
            4 * strut_morphometry.assigned_volume_original_voxels_cubed
            / (np.pi * strut_morphometry.length_original_voxels.clip(lower=np.finfo(float).eps))
        )
        del nearest_indices, nearest_labels, edge_label_image

        morph_by_edge = strut_morphometry.set_index("edge_id")
        node_morph_rows = []
        for row in node_table.query("degree > 0").itertuples():
            # Use the logical-node centroid's nearest valid skeleton coordinate for local node size.
            center = np.rint([row.z, row.y, row.x]).astype(int)
            radius = 2
            slices = tuple(slice(max(0, c - radius), min(selected_mask.shape[i], c + radius + 1)) for i, c in enumerate(center))
            local_d = (2 * edt[slices])[selected_mask[slices]]
            incident_ids = incident.get(int(row.node_id), [])
            incident_medians = morph_by_edge.loc[morph_by_edge.index.intersection(incident_ids), "diameter_median_original_voxels"].dropna().to_numpy()
            robust_node = float(np.median(local_d)) if len(local_d) else np.nan
            incident_reference = float(np.median(incident_medians)) if len(incident_medians) else np.nan
            node_morph_rows.append({
                "node_id": int(row.node_id), "degree": int(row.degree),
                "peak_local_diameter_original_voxels": float(np.max(local_d)) if len(local_d) else np.nan,
                "robust_local_diameter_original_voxels": robust_node,
                "incident_edge_diameter_contrast": (float(np.max(incident_medians) - np.min(incident_medians)) / max(incident_reference, 1e-9)) if len(incident_medians) >= 2 else np.nan,
                "node_to_strut_diameter_ratio": robust_node / incident_reference if np.isfinite(incident_reference) and incident_reference > 0 else np.nan,
                "incident_edge_count_with_diameter": int(len(incident_medians)),
            })
        node_morphometry = pd.DataFrame(node_morph_rows)

        reliable_d = strut_morphometry.loc[strut_morphometry.reliable_diameter, "diameter_median_original_voxels"].dropna()
        morphometry_summary = pd.DataFrame([{
            "dataset_id": CONFIG["dataset_id"], "segmentation_id": CONFIG_HASH,
            "unit": "original_voxels", "mask_volume_fraction": float(selected_mask.mean()),
            "retained_edge_count": len(strut_morphometry), "reliable_edge_count": int(strut_morphometry.reliable_diameter.sum()),
            "excluded_edge_count": int((~strut_morphometry.reliable_diameter).sum()),
            "reliable_edge_fraction": float(strut_morphometry.reliable_diameter.mean()),
            "edge_median_diameter_median": float(reliable_d.median()),
            "edge_median_diameter_q25": float(reliable_d.quantile(0.25)),
            "edge_median_diameter_q75": float(reliable_d.quantile(0.75)),
            "length_weighted_mean_diameter": float(np.average(
                strut_morphometry.diameter_median_original_voxels.fillna(0),
                weights=strut_morphometry.length_original_voxels)),
            "node_robust_diameter_median": float(node_morphometry.robust_local_diameter_original_voxels.median()),
            "median_uncertainty_score": float(strut_morphometry.uncertainty_score.median()),
            "high_uncertainty_edge_fraction": float((strut_morphometry.uncertainty_score > 0.5).mean()),
            "configuration_hash": CONFIG_HASH,
        }])
        strut_morphometry.to_csv(guarded_output(FEATURE_DIR, "strut_morphometry.csv"), index=False)
        node_morphometry.to_csv(guarded_output(FEATURE_DIR, "node_morphometry.csv"), index=False)
        morphometry_summary.to_csv(guarded_output(FEATURE_DIR, "morphometry_summary.csv"), index=False)

        print(morphometry_summary.T.to_string(header=False))
        print("Local inscribed and volume-length diameters are intentionally separate columns.")
        """,
        "run-morphometry",
    ),
    code(
        """
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
        axes[0].hist(strut_morphometry.diameter_median_original_voxels.dropna(), bins=60, color="slateblue")
        axes[0].set(xlabel="median local diameter (original voxels)", ylabel="edges", title="Per-edge local diameter")
        axes[1].scatter(strut_morphometry.diameter_median_original_voxels,
                        strut_morphometry.volume_length_equivalent_diameter_original_voxels,
                        s=3, alpha=0.2)
        lim = np.nanpercentile(np.r_[strut_morphometry.diameter_median_original_voxels,
                                    strut_morphometry.volume_length_equivalent_diameter_original_voxels], 99)
        axes[1].plot([0, lim], [0, lim], "k--", lw=1)
        axes[1].set(xlabel="local median diameter", ylabel="volume–length equivalent diameter", title="Distinct diameter estimators")
        axes[2].hist(node_morphometry.node_to_strut_diameter_ratio.dropna(), bins=60, color="darkorange")
        axes[2].set(xlabel="node / incident-strut diameter", ylabel="nodes", title="Node thickening ratio")
        save_and_show(fig, "morphometry_diagnostics.png")

        example_ids = strut_morphometry.query("reliable_diameter").nlargest(8, "length_original_voxels").edge_id
        fig, ax = plt.subplots(figsize=(11, 4))
        for edge_id in example_ids:
            d = sample_cache[int(edge_id)]["diameters"]
            ax.plot(np.linspace(0, 1, len(d)), d, lw=1, alpha=0.75, label=str(edge_id))
        ax.set(xlabel="normalized position along edge", ylabel="local diameter (original voxels)",
               title="Diameter profiles for eight long reliable edges")
        ax.legend(ncol=4, fontsize=7, title="edge")
        save_and_show(fig, "diameter_along_edge_profiles.png")
        """,
        "morphometry-figures",
    ),
    markdown(
        """
        ## 5. Required synthetic validation

        These checks exercise failure handling, polarity, artifact sensitivities, logical topology, diameter
        ordering, and physical-spacing behavior. Tolerances acknowledge voxelization. The real-data run is
        considered valid only if every check below passes.
        """,
        "validation-heading",
    ),
    code(
        """
        validation = []
        def check(name, observed, expected, passed):
            validation.append({"test": name, "observed": str(observed), "expected": str(expected), "passed": bool(passed)})

        # Known phase fraction and foreground polarity.
        synthetic = np.zeros((32, 32, 32), dtype=np.float32)
        synthetic[:, :, :10] = 1
        syn_norm, _, _ = normalize_volume(synthetic, (0, 100))
        syn_t = threshold_otsu(syn_norm)
        bright_fraction = float((syn_norm > syn_t).mean())
        dark_fraction = float((syn_norm < syn_t).mean())
        check("two-phase fraction", round(bright_fraction, 5), round(10 / 32, 5), abs(bright_fraction - 10 / 32) < 0.01)
        check("polarity reversal", round(dark_fraction, 5), round(22 / 32, 5), abs(dark_fraction - 22 / 32) < 0.01)
        try:
            normalize_volume(np.ones((8, 8, 8), dtype=float))
            constant_failed = False
        except ValueError:
            constant_failed = True
        check("constant-volume rejection", constant_failed, True, constant_failed)

        # Artifact metrics respond in the expected direction.
        yy, xx = np.indices((128, 128)); rr = np.sqrt((yy - 63.5) ** 2 + (xx - 63.5) ** 2)
        rng = np.random.default_rng(CONFIG["random_seed"])
        base = rng.normal(0.5, 0.03, rr.shape)
        ringed = base + 0.12 * np.sin(rr * 0.55)
        check("ring sensitivity", round(ring_severity(ringed) / ring_severity(base), 2), "> 1", ring_severity(ringed) > ring_severity(base))
        support = rr < 55
        unbiased = support.astype(float) + rng.normal(0, 0.02, rr.shape)
        biased = unbiased + support * 0.35 * (rr / 55) ** 2
        check("beam-hardening sensitivity", round(beam_hardening_severity(biased), 3), "> baseline", beam_hardening_severity(biased) > beam_hardening_severity(unbiased))

        # Straight 3D centerline topology.
        straight = np.zeros((21, 21, 21), dtype=bool); straight[10, 10, 3:18] = True
        sn, sp, _, sa = logical_skeleton_graph(straight, np.ones(3))
        check("straight-line topology", (len(sn), len(sp)), "(2 nodes, 1 edge)", len(sn) == 2 and len(sp) == 1 and sa == 1)

        # Cylinder diameter and ordering under voxelization.
        zz, yy3, xx3 = np.indices((48, 48, 48))
        cylinder_diameters = []
        for radius in (4, 6):
            cyl = (yy3 - 23.5) ** 2 + (xx3 - 23.5) ** 2 <= radius ** 2
            cyl_dt = ndi.distance_transform_edt(cyl, sampling=(1, 1, 1))
            cylinder_diameters.append(float(2 * np.median(cyl_dt[:, 23:25, 23:25])))
        check("cylinder diameter ordering", np.round(cylinder_diameters, 2).tolist(), "increasing with radius", cylinder_diameters[1] > cylinder_diameters[0])
        check("radius-6 diameter recovery", round(cylinder_diameters[1], 2), "12 ± 2 voxels", abs(cylinder_diameters[1] - 12) <= 2)
        anisotropic_dt = ndi.distance_transform_edt((yy3 - 23.5) ** 2 + (xx3 - 23.5) ** 2 <= 6 ** 2, sampling=(2, 1, 1))
        anisotropic_diameter = float(2 * np.median(anisotropic_dt[:, 23:25, 23:25]))
        check("anisotropic-spacing diameter", round(anisotropic_diameter, 2), "12 ± 2 physical units", abs(anisotropic_diameter - 12) <= 2)

        validation_results = pd.DataFrame(validation)
        validation_results.to_csv(guarded_output(FEATURE_DIR, "synthetic_validation.csv"), index=False)
        print(validation_results.to_string(index=False))
        if not validation_results.passed.all():
            raise AssertionError("One or more required synthetic validations failed.")
        """,
        "run-validation",
    ),
    markdown(
        """
        ## 6. Interpretation and limitations

        The next cell prints the dataset-specific findings and writes the cross-stage execution manifest.
        The results quantify the CT-derived foreground network; they are not a direct comparison to the
        nominal CAD. Boundary-intersecting paths, partial-volume effects, the 4× grid, and segmentation
        disagreement must remain in view when interpreting small struts or unusually thick nodes.
        """,
        "interpretation-heading",
    ),
    code(
        """
        summary = morphometry_summary.iloc[0]
        topology = graph_summary.iloc[0]
        qc = ct_volume_qc.iloc[0]
        print("EXECUTIVE FINDINGS")
        print(f"• The ranked ensemble accepted a connected bright-material phase occupying {qc.selected_volume_fraction:.2%} of the 4× analysis grid.")
        print(f"• Ensemble disagreement affects {qc.uncertain_voxel_fraction:.2%} of analysis voxels; edge uncertainty is preserved in strut_morphometry.csv.")
        print(f"• After audited spur pruning, the logical graph has {int(topology.logical_node_count):,} nodes, {int(topology.logical_edge_count):,} edges, and {int(topology.component_count):,} component(s).")
        print(f"• {summary.reliable_edge_fraction:.1%} of retained edges meet the conservative diameter reliability rule.")
        print(f"• Reliable per-edge median local diameter: median {summary.edge_median_diameter_median:.2f}, IQR [{summary.edge_median_diameter_q25:.2f}, {summary.edge_median_diameter_q75:.2f}] original voxels.")
        print(f"• Median robust node diameter is {summary.node_robust_diameter_median:.2f} original voxels.")
        print("• These are CT-derived, downsample-aware descriptors; physical calibration and CAD registration are outside this report's evidence.")

        artifact_names = [
            "ct_volume_qc.csv", "segmentation_sweep.csv", "ct_selected_mask_ds4.tif",
            "ct_segmentation_disagreement_ds4.tif", "skeleton_nodes.csv", "skeleton_edges.csv",
            "skeleton_graph_summary.csv", "skeleton_pruned_spurs.csv", "skeleton_graph.json",
            "strut_morphometry.csv", "node_morphometry.csv", "morphometry_summary.csv",
            "synthetic_validation.csv",
        ]
        report_names = [
            "ct_segmentation_diagnostics.png", "ct_qc_slice_trends.png",
            "skeleton_graph_diagnostics.png", "morphometry_diagnostics.png",
            "diameter_along_edge_profiles.png", "ct_lattice_final_report.ipynb",
        ]
        manifest = {
            "dataset_id": CONFIG["dataset_id"], "source_path": str(DATA_PATH.relative_to(ROOT)),
            "source_bytes": DATA_PATH.stat().st_size, "source_shape": list(raw_shape),
            "axis_convention": "ZYX", "physical_voxel_spacing": None,
            "analysis_spacing": SPACING.tolist(), "analysis_units": "original_voxels",
            "configuration": CONFIG, "configuration_hash": CONFIG_HASH,
            "segmentation_identifier": CONFIG_HASH, "software_versions": SOFTWARE,
            "python": sys.version, "validation_passed": bool(validation_results.passed.all()),
            "warnings": [
                "TIFF has no physical-resolution metadata; results are in original-voxel units.",
                "Spatial morphology uses a 4× decimated analysis grid.",
                f"Logical paths account for {skeleton_accounting:.2%} of retained skeleton voxels; untraced pixels are degree-two-only cycles or local connectivity ambiguities.",
                "No CAD registration or ground-truth defect labels were used.",
            ],
            "artifacts": [str((FEATURE_DIR / n).relative_to(ROOT)) for n in artifact_names],
            "reports": [str((REPORT_DIR / n).relative_to(ROOT)) for n in report_names],
            "row_counts": {
                "ct_volume_qc.csv": len(ct_volume_qc), "segmentation_sweep.csv": len(segmentation_sweep),
                "skeleton_nodes.csv": len(node_table), "skeleton_edges.csv": len(skeleton_edges),
                "skeleton_graph_summary.csv": len(graph_summary), "strut_morphometry.csv": len(strut_morphometry),
                "node_morphometry.csv": len(node_morphometry), "morphometry_summary.csv": len(morphometry_summary),
                "synthetic_validation.csv": len(validation_results),
            },
        }
        guarded_output(REPORT_DIR, "ct_lattice_execution_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        print()
        print(f"Manifest: {guarded_output(REPORT_DIR, 'ct_lattice_execution_manifest.json').relative_to(ROOT)}")
        """,
        "final-summary",
    ),
]


def execute_notebook(cells: list[dict]) -> None:
    """Execute code cells and embed stream, error, and Matplotlib PNG outputs."""
    namespace: dict = {"__name__": "__main__", "display": lambda value: print(value)}
    execution_count = 0

    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        execution_count += 1
        cell["execution_count"] = execution_count
        outputs: list[dict] = []
        stream = io.StringIO()
        captured_images: list[str] = []

        if "plt" in namespace:
            plt = namespace["plt"]

            def capture_show(*_args, **_kwargs):
                for number in list(plt.get_fignums()):
                    fig = plt.figure(number)
                    buffer = io.BytesIO()
                    fig.savefig(buffer, format="png", bbox_inches="tight")
                    captured_images.append(base64.b64encode(buffer.getvalue()).decode("ascii"))
                    plt.close(fig)

            plt.show = capture_show

        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                exec(compile(cell["source"], f"<cell-{cell['id']}>", "exec"), namespace)
        except Exception as exc:
            text = stream.getvalue()
            if text:
                outputs.append({"output_type": "stream", "name": "stdout", "text": text})
            tb = traceback.format_exc().splitlines()
            outputs.append({"output_type": "error", "ename": type(exc).__name__, "evalue": str(exc), "traceback": tb})
            cell["outputs"] = outputs
            write_notebook(cells)
            raise

        text = stream.getvalue()
        if text:
            outputs.append({"output_type": "stream", "name": "stdout", "text": text})
        for image_data in captured_images:
            outputs.append({"output_type": "display_data", "metadata": {}, "data": {"image/png": image_data}})
        cell["outputs"] = outputs


def write_notebook(cells: list[dict]) -> None:
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3.12 (.venv)", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=1), encoding="utf-8")


if __name__ == "__main__":
    write_notebook(CELLS)
    execute_notebook(CELLS)
    write_notebook(CELLS)
    print(f"Executed notebook written to {NOTEBOOK_PATH}")
