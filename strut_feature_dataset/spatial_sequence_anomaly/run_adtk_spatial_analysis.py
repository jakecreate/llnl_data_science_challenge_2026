"""Apply ADTK detectors to locality-preserving spatial strut sequences."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from adtk.data import validate_series
from adtk.detector import InterQuartileRangeAD, PersistAD, QuantileAD


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE / "datasets" / "strut_spatial_sequence.csv"
DEFAULT_OUTPUT = HERE / "datasets"


def boolean_result(values: pd.Series) -> pd.Series:
    return values.fillna(False).astype(bool)


def analyze_group(group: pd.DataFrame) -> pd.DataFrame:
    group = group.sort_values("sequence_position").copy()
    index = pd.to_datetime(group["pseudo_timestamp"])
    series = pd.Series(
        group["ct_relative_local_intensity"].to_numpy(dtype=float),
        index=index,
        name="relative_intensity",
    )
    series = validate_series(series)
    median = float(series.median())
    iqr = boolean_result(InterQuartileRangeAD(c=1.5).fit_detect(series))
    quantile = boolean_result(QuantileAD(low=0.02).fit_detect(series))
    try:
        persist = boolean_result(
            PersistAD(window=5, c=3.0, side="negative", min_periods=3).fit_detect(series)
        )
    except (RuntimeError, ValueError, ZeroDivisionError):
        persist = pd.Series(False, index=series.index)
    low_side = series < median
    iqr_low = iqr & low_side
    quantile_low = quantile & low_side
    result = group.reset_index(drop=True)
    result["adtk_iqr_low_anomaly"] = iqr_low.to_numpy(dtype=int)
    result["adtk_quantile_low_anomaly"] = quantile_low.to_numpy(dtype=int)
    result["adtk_persist_negative_anomaly"] = persist.to_numpy(dtype=int)
    result["adtk_detector_votes"] = result[
        ["adtk_iqr_low_anomaly", "adtk_quantile_low_anomaly", "adtk_persist_negative_anomaly"]
    ].sum(axis=1)
    result["adtk_consensus_anomaly"] = (result.adtk_detector_votes >= 2).astype(int)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(args.input)
    analyzed = pd.concat(
        [analyze_group(group) for _, group in data.groupby("sequence_id", sort=True)],
        ignore_index=True,
    )
    analyzed.to_csv(args.output_dir / "adtk_spatial_anomaly_results.csv", index=False)
    consensus = analyzed[analyzed.adtk_consensus_anomaly == 1].copy()
    consensus.to_csv(args.output_dir / "adtk_consensus_anomalies.csv", index=False)
    heuristic_candidate = analyzed.ct_severity_layer.isin(["high", "critical"])
    adtk_candidate = analyzed.adtk_consensus_anomaly.astype(bool)
    overlap = int(np.sum(heuristic_candidate & adtk_candidate))
    summary = {
        "total_struts": len(analyzed),
        "iqr_low_anomalies": int(analyzed.adtk_iqr_low_anomaly.sum()),
        "quantile_low_anomalies": int(analyzed.adtk_quantile_low_anomaly.sum()),
        "persist_negative_anomalies": int(analyzed.adtk_persist_negative_anomaly.sum()),
        "consensus_anomalies": int(analyzed.adtk_consensus_anomaly.sum()),
        "existing_high_or_critical": int(heuristic_candidate.sum()),
        "consensus_overlap_with_existing_high_or_critical": overlap,
        "consensus_overlap_rate": overlap / max(int(adtk_candidate.sum()), 1),
        "existing_candidate_recall_by_consensus": overlap / max(int(heuristic_candidate.sum()), 1),
        "interpretation": "agreement with existing screening ranks is not ground-truth accuracy",
    }
    (args.output_dir / "adtk_analysis_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
