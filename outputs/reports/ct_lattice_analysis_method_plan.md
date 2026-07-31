# CT Lattice Analysis Method Plan

## Scope and execution order

The three methods in `artifact/analysis_methods.json` should be implemented as one ordered pipeline:

1. CT Volume QC & Segmentation Ensemble
2. CT-Only Skeleton Graph & Strut-Node Recovery
3. Strut & Node Morphometry / Equivalent Diameter

The segmentation mask produced by method 1 is the input to methods 2 and 3. The skeleton and edge identifiers produced by method 2 are used by method 3 to aggregate local thickness into per-strut features.

All raw files under `data/` remain read-only. Feature tables are written to `outputs/features/`; reports and diagnostic figures are written to `outputs/reports/`.

## Environment decision

Use Python 3.12 because PoreSpy 3.0.4 requires Python earlier than 3.14. The repository-local `.venv` was created with Python 3.12.13.

Approved direct dependencies:

| Distribution | Pin | Pipeline responsibility |
| --- | --- | --- |
| `scipy` | `1.18.0` | Local statistics, morphology, connected components, and Euclidean distance transform |
| `networkx` | `3.6.1` | Graph construction, topology, components, cycles, and connectivity features |
| `skan` | `0.13.1` | Skeleton branch decomposition and branch-level measurements |
| `porespy` | `3.0.4` | Supporting 3D porous-media morphology and validation metrics |

Existing direct dependencies used by the methods are `tifffile`, `scikit-image`, `numpy`, `matplotlib`, and `opencv-python`.

Compatibility corrections:

- Treat `skimage.filters` and `scipy.ndimage` as modules supplied by the `scikit-image` and `scipy` distributions, not as separate packages.
- Replace the removed `skimage.morphology.skeletonize_3d` entry point with `skimage.morphology.skeletonize(mask, method="lee")` for 3D masks.
- Implement Phansalkar thresholding from local mean and standard-deviation arrays because scikit-image does not expose a Phansalkar threshold function.

## Method 1: CT Volume QC & Segmentation Ensemble

### Atomic implementation steps

1. Accept a `.tif` path plus optional voxel spacing, foreground polarity, crop bounds, and parameter-sweep configuration through an explicitly typed FastMCP tool signature.
2. Resolve the input path and reject any non-TIFF input, missing file, or output path inside `data/`.
3. Load the volume with `tifffile`; record shape, dtype, axes, byte size, and available resolution metadata.
4. Confirm that the normalized array is three-dimensional and contains finite numeric values.
5. Resolve voxel spacing from TIFF metadata or caller input; label results as voxel units when physical spacing is unavailable.
6. Compute global minimum, maximum, mean, standard deviation, robust percentiles, histogram, and saturated-voxel fractions.
7. Compute per-slice mean, standard deviation, robust range, and foreground-background contrast along all three axes.
8. Flag abrupt slice-to-slice intensity jumps and unusually low-contrast slices using robust median-absolute-deviation scores.
9. Estimate ring severity on representative slices by comparing radial residual energy around the reconstruction center with angular residual energy.
10. Estimate beam-hardening severity from center-to-boundary intensity drift within a coarse specimen support mask.
11. Normalize intensities with percentile clipping while retaining the original array unchanged.
12. Optionally denoise each candidate input with a documented, deterministic filter configuration.
13. Compute a global Otsu threshold and create both possible foreground-polarity masks when polarity is not supplied.
14. Compute local mean and standard deviation volumes for each configured Phansalkar window size.
15. Apply the Phansalkar equation for every configured parameter tuple and polarity.
16. Remove components below a configured physical-volume or voxel-count threshold.
17. Fill only bounded holes smaller than a configured size; do not close intentional lattice pores globally.
18. Score every candidate using volume fraction, connected-component count, boundary-touch fraction, retained largest-component fraction, and slice-to-slice stability.
19. Reject candidates that are empty, nearly full, fragmented beyond tolerance, or dominated by the image boundary.
20. Rank the remaining candidates with a recorded composite score rather than an implicit visual choice.
21. Form an ensemble probability volume from the top candidates and threshold it at the configured vote fraction.
22. Compute a disagreement volume and summarize uncertain-voxel fraction globally and per slice.
23. Save the selected binary mask and disagreement volume outside `data/` using lossless formats.
24. Write one row of volume-level QC and segmentation features to `outputs/features/ct_volume_qc.csv`.
25. Write the full parameter sweep and candidate scores to `outputs/features/segmentation_sweep.csv`.
26. Render representative raw, mask, overlay, histogram, per-slice trend, and artifact-diagnostic figures to `outputs/reports/`.
27. Return a structured FastMCP result containing output paths, chosen parameters, QC flags, warnings, and success status.

### Required validation

- Synthetic two-phase volumes with known intensity separation recover the expected phase fraction.
- Empty and constant volumes fail with clear validation messages.
- Reversing foreground polarity changes the mask as expected.
- An injected ring pattern increases the ring score.
- A radial intensity bias increases the beam-hardening score.
- Repeated runs with identical inputs and configuration produce identical outputs.

## Method 2: CT-Only Skeleton Graph & Strut-Node Recovery

### Atomic implementation steps

1. Accept a selected binary-mask path, voxel spacing, connectivity convention, and pruning thresholds through an explicitly typed FastMCP tool signature.
2. Reject input or output paths that would modify `data/`.
3. Load the mask and verify that it is a nonempty three-dimensional boolean-compatible array.
4. Apply the same voxel spacing and coordinate-axis convention recorded by method 1.
5. Label connected foreground components and retain or annotate components according to an explicit policy.
6. Skeletonize the cleaned mask with `skimage.morphology.skeletonize(mask, method="lee")`.
7. Verify that every skeleton voxel lies inside the segmentation mask.
8. Build a `skan.Skeleton` object with physical voxel spacing.
9. Extract the Skan branch table and preserve original branch identifiers.
10. Classify skeleton voxels by neighbor count under the selected 3D connectivity.
11. Group adjacent junction voxels into single logical nodes instead of treating each junction voxel as a separate node.
12. Identify terminal nodes, junction nodes, isolated skeleton voxels, and boundary-intersecting nodes.
13. Trace maximal paths whose interiors contain only degree-two voxels.
14. Create one NetworkX node per logical endpoint or junction with voxel and physical coordinates.
15. Create one NetworkX edge per traced path with ordered voxel coordinates and original Skan branch identifiers.
16. Calculate edge path length using physical spacing.
17. Calculate endpoint Euclidean length, tortuosity, orientation vector, and boundary-contact flag for every edge.
18. Prune terminal spurs shorter than the configured physical threshold while retaining an audit table of removed branches.
19. Recompute node degrees and connected components after pruning.
20. Calculate graph-level node count, edge count, endpoint count, junction count, degree distribution, component count, cycle rank, and largest-component fraction.
21. Calculate node-level degree, component identifier, boundary distance, and incident-edge identifiers.
22. Validate that the sum of traced edge paths accounts for the retained skeleton, allowing only documented junction-cluster overlap.
23. Save node features to `outputs/features/skeleton_nodes.csv`.
24. Save edge features to `outputs/features/skeleton_edges.csv`.
25. Save graph-level features to `outputs/features/skeleton_graph_summary.csv`.
26. Save the serializable graph and coordinate mappings as JSON under `outputs/features/`.
27. Render slice overlays and a 3D graph diagnostic to `outputs/reports/`.
28. Return a structured FastMCP result containing feature paths, topology summary, pruning summary, warnings, and success status.

### Required validation

- A synthetic straight cylinder yields two degree-one nodes and one edge.
- A synthetic Y junction yields three terminals and one degree-three junction.
- A disconnected synthetic mask yields the expected component count.
- An injected short spur is removed only when its physical length is below the pruning threshold.
- An anisotropic-spacing case returns correct physical path and Euclidean lengths.

## Method 3: Strut & Node Morphometry / Equivalent Diameter

### Atomic implementation steps

1. Accept the selected mask, retained skeleton, edge-coordinate mapping, node-coordinate mapping, and voxel spacing through an explicitly typed FastMCP tool signature.
2. Verify that all inputs share the same shape, coordinate convention, segmentation identifier, and voxel spacing.
3. Compute the foreground Euclidean distance transform with `scipy.ndimage.distance_transform_edt(mask, sampling=spacing)`.
4. Sample the distance-transform value at every retained skeleton voxel as the local inscribed radius.
5. Convert local radius to local diameter with `diameter = 2 * radius`.
6. Associate every sampled diameter with its retained edge identifier.
7. Build a junction-exclusion zone using a configurable physical radius around each logical graph node.
8. Mark samples inside junction-exclusion zones so node thickening does not inflate strut-only diameter estimates.
9. For each edge, calculate valid sample count, mean, median, standard deviation, minimum, maximum, interquartile range, and configured diameter quantiles.
10. Calculate per-edge diameter coefficient of variation and robust taper from endpoint-adjacent to midspan samples.
11. Calculate per-edge slenderness as physical edge length divided by robust diameter.
12. Mark edges too short or too dominated by junction-exclusion zones for reliable diameter estimation.
13. Assign segmented foreground voxels to the nearest retained centerline or use a documented PoreSpy partitioning routine for an optional edge-volume estimate.
14. When edge volume is available, calculate volume-length equivalent diameter as `sqrt(4 * edge_volume / (pi * edge_length))`.
15. Keep distance-transform diameter and volume-length equivalent diameter as separate named features.
16. For each node, calculate peak local diameter, robust local diameter, incident-edge diameter contrast, and node-to-strut diameter ratio.
17. Calculate volume-level diameter distribution, edge-weighted diameter distribution, node-size distribution, and outlier fractions.
18. Propagate segmentation-disagreement values from method 1 to each sampled centerline point.
19. Calculate an uncertainty score per edge from segmentation disagreement, sample count, and junction-excluded fraction.
20. Save per-edge morphometry to `outputs/features/strut_morphometry.csv`.
21. Save per-node morphometry to `outputs/features/node_morphometry.csv`.
22. Save volume-level morphometry to `outputs/features/morphometry_summary.csv`.
23. Render diameter histograms, diameter-along-edge profiles, and color-mapped skeleton diagnostics to `outputs/reports/`.
24. Return a structured FastMCP result containing feature paths, unit labels, excluded-edge counts, uncertainty summary, warnings, and success status.

### Required validation

- A synthetic cylinder recovers its known diameter within a voxelization-dependent tolerance.
- Cylinders of several radii preserve diameter ordering and approximate scale.
- An anisotropic-spacing test recovers physical rather than voxel-unit diameter.
- Junction exclusion reduces the positive diameter bias near a synthetic Y junction.
- The volume-length equivalent diameter agrees with the analytic value for a straight cylinder.
- Empty edges and single-sample edges receive explicit reliability flags rather than silent numeric values.

## Cross-stage contracts

Every stage should record and verify:

- dataset identifier and source path;
- array shape and axis convention;
- voxel spacing and physical units;
- parameter/configuration hash;
- upstream artifact identifiers;
- software versions;
- warnings and QC flags;
- output paths and row counts.

Stage 2 must not run on a segmentation that failed stage-1 acceptance checks unless the caller explicitly permits a flagged run. Stage 3 must not mix masks, skeletons, or graphs with different identifiers or coordinate metadata.

## Recommended CodA implementation sequence

1. Define shared path guards, metadata models, feature schemas, and structured FastMCP response models.
2. Implement method-1 pure functions and synthetic tests.
3. Wrap method 1 as a FastMCP tool and validate its schema through an in-memory client.
4. Implement method-2 pure functions and synthetic topology tests.
5. Wrap method 2 as a FastMCP tool and validate its schema through an in-memory client.
6. Implement method-3 pure functions and synthetic geometry tests.
7. Wrap method 3 as a FastMCP tool and validate its schema through an in-memory client.
8. Add an orchestration tool that passes versioned artifact identifiers between stages.
9. Run the end-to-end pipeline on a small read-only fixture and confirm all writes remain under `outputs/`.
10. Run a final FastMCP discovery and invocation test for every public tool.

## Current harness note

The Python 3.12 scientific dependency set resolves successfully. The existing `src/mcp_literature_agent.py` server cannot currently be imported in the clean environment because it imports the undeclared `requests` distribution. Add and pin `requests` only after separate human approval, then rerun that server's in-memory FastMCP discovery and `validate_output` invocation.
