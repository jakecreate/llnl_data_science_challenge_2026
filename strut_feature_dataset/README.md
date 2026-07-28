# Strut feature dataset

This folder converts the registered `0.5-1` lattice into tabular datasets with
one row per expected strut.

## Generated tables

- `strut_design_features.csv` contains only pre-print geometry, graph,
  orientation, boundary, and mechanical-proxy features.
- `strut_features_combined.csv` contains the same design features plus the CT
  screening measurements produced by `src/detect_broken_struts.py`.

Keep the design-only table separate when training a pre-print risk model. Using
the CT columns as predictors would leak post-print information into that model.

## Feature groups

### Identity and location

Strut and junction IDs, unit-cell identifiers, edge type, endpoint coordinates,
and midpoint coordinates are included in both voxel and millimetre units.

### Geometry and orientation

Features include length, nominal diameter, normalized direction, azimuth,
elevation, angle to the assumed Z build direction, and an orientation class.

### Graph connectivity

Endpoint degrees and the number of neighboring struts describe whether a strut
connects low- or high-connectivity junctions.

### Boundary context

The table records boundary endpoints, distance from the lattice boundary, and
whether the midpoint lies within one 4.56 mm unit cell of a boundary.

### Mechanical proxies

Cross-sectional area, second moment of area, nominal volume, slenderness, and
geometry-only axial, bending, and Euler-buckling proxies are included. These
are not finite-element results because no material modulus, loading, or support
conditions have been specified.

### CT screening

The combined table includes CT support, intensity, continuity, spatially
normalized defect score, rank, screening label, and severity layer. These are
screening measurements rather than manually verified ground truth.

## Assumptions

- Registered JSON positions are `(X, Y, Z)` voxel coordinates.
- Voxel spacing is isotropic at 58.09 micrometres.
- Nominal strut diameter is 0.350 mm.
- Unit-cell size is 4.560 mm.
- Z is treated as the build direction only as an explicit working assumption.

## Run

From the repository root:

```powershell
python .\strut_feature_dataset\build_strut_feature_table.py
```

The script uses only the Python standard library. To build geometry-only tables
without joining CT results:

```powershell
python .\strut_feature_dataset\build_strut_feature_table.py --design-only
```

All physical assumptions can be overridden with command-line arguments. Run
the script with `--help` to see them.

## Visualization atlas

`visualize_strut_features.py` generates a broad exploratory atlas covering
feature distributions, severity layers, CT measurements, connectivity,
orientation, boundary effects, unit-cell position, correlations, spatial
projections, and the strongest candidates.

```powershell
uv run --with numpy --with matplotlib python .\strut_feature_dataset\visualize_strut_features.py
```

The generated images and Markdown index are written to `visualizations/`.
