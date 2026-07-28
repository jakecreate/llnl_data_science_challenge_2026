# Model recommendations

## First principle

The current sequences are spatial, not temporal. Do not use forecasting language,
LSTMs, or temporal transformers unless future data includes real build time,
layer timestamps, or in-situ sensor streams.

## Recommended now

1. **Robust statistical baselines**
   - Median/MAD and IQR thresholds within edge type, orientation, and spatial region.
   - Best initial benchmark because it is interpretable and works without labels.

2. **Isolation Forest**
   - Suitable for multivariate unsupervised screening using CT profile summaries,
     boundary location, connectivity, orientation, and edge type.
   - Fit separate models by specimen or use specimen-aware normalization.

3. **Local Outlier Factor**
   - Useful for comparing a strut with nearby and structurally equivalent peers.
   - Use only for retrospective scoring; standard LOF is not naturally a deployment model.

4. **Regularized logistic regression**
   - Preferred supervised baseline after manual defect labels are available.
   - Provides calibrated, interpretable coefficients after careful feature scaling.

5. **Random forest or gradient-boosted trees**
   - Strong tabular classifiers for nonlinear relationships and mixed geometry/CT features.
   - Use grouped cross-validation by physical specimen, never random strut splits.

## Profile-specific models

- Change-point detection or CUSUM for localized broken-strut gaps.
- Shape-based distance or functional PCA for 31-point centerline profiles.
- A small 1D convolutional classifier after enough manually labeled profiles exist.

## Later, with more data

- Graph neural networks can use junctions as nodes and struts as edges.
- 3D CNNs can classify local CT patches, but require substantially more labeled scans.
- Survival or forecasting models require actual chronological process measurements.

## Validation requirements

- Treat specimen as the cross-validation group.
- Report precision/recall for missing, broken, thin, and intact classes separately.
- Include a manually reviewed test set that was not used to tune thresholds.
- Measure calibration; a screening score is not automatically a probability.
