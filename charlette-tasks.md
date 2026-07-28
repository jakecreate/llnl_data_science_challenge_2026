# Task for Charlette

At the moment we are trying to avoid registration and there is exactly one set of files that are registered to eachother

* data\missing_struts\registered_jsons\210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json
* data\missing_struts\tif_stacks\210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif
* data\missing_struts\stls\0.5.stl

For now I will work on the visualization of highlighting the defective struts from the observation of the items.

## Implemented baseline

`src/detect_broken_struts.py` uses the registered ideal JSON as the expected
strut graph and samples CT intensity along every expected centerline. It writes
per-strut scores, a VTK graph, two highlighted 3D views, and an NDE-style
screening report under `data/missing_struts/defect_analysis/`. It also creates
`top_candidate_ct_evidence.png`, where the registered expected centerline is
drawn over a local CT maximum projection for the six strongest candidates.

Run from the repository root with:

```powershell
uv run --with numpy --with tifffile --with pyvista python .\src\detect_broken_struts.py
```

The labels are screening candidates rather than ground truth. Red marks the
weakest 0.5% of expected struts, yellow marks the next weakest 1%, and blue
marks struts with stronger CT support. The candidate fraction is configurable.

## Layered PyVista viewer

`src/visualize_defect_layers.py` converts the screening scores into five
rank-based severity layers, produces cumulative severity images, clusters the
high and critical struts into spatial defect regions, and renders close-up
images with strut IDs. Add `--show` to open the interactive viewer with layer
checkboxes.

```powershell
uv run --with numpy --with pyvista python .\src\visualize_defect_layers.py --show
```
