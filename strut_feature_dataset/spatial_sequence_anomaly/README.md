# Spatial sequence anomaly experiment

This folder tests whether sequential anomaly-detection tools can add useful
information to the registered lattice CT analysis.

## Important limitation

The available data is not a time series. The ordering represents spatial
position:

1. Struts of the same unit-cell edge type are traversed in 3D Morton order.
2. Each strut is sampled at 31 ordered positions along its centerline.

Pseudo-timestamps are included only because ADTK expects a datetime index. Every
dataset includes `is_true_time_series=0` and a `sequence_semantics` field.

## Datasets

- `datasets/strut_spatial_sequence.csv`: one row per strut in a locality-preserving traversal.
- `datasets/centerline_profiles_long.csv.gz`: 31 CT samples for every strut.
- `datasets/centerline_profile_summary.csv`: one row per strut with profile-shape features.
- `datasets/adtk_spatial_anomaly_results.csv`: detector flags for every strut.
- `datasets/adtk_consensus_anomalies.csv`: struts supported by at least two ADTK detectors.
- `datasets/adtk_analysis_summary.json`: counts and overlap diagnostics.

## Run

From the repository root:

```powershell
uv run --with-requirements .\strut_feature_dataset\spatial_sequence_anomaly\requirements.txt python .\strut_feature_dataset\spatial_sequence_anomaly\build_spatial_sequence_datasets.py

uv run --with-requirements .\strut_feature_dataset\spatial_sequence_anomaly\requirements.txt python .\strut_feature_dataset\spatial_sequence_anomaly\run_adtk_spatial_analysis.py

uv run --with-requirements .\strut_feature_dataset\spatial_sequence_anomaly\requirements.txt python .\strut_feature_dataset\spatial_sequence_anomaly\visualize_spatial_anomalies.py
```

See `FINDINGS.md` for the generated interpretation and
`MODEL_RECOMMENDATIONS.md` for next-step classifiers.
