# 9x9x9 Octet Lattice Segmentation Report

Segmentation completed using Otsu thresholding. The threshold was estimated from slice 380, which is also the requested visual quality-check slice.

| Metric | Value |
|---|---:|
| Input volume | 761 × 815 × 837 `uint16` voxels |
| Threshold | 40,499 |
| Foreground voxels | 56,746,185 |
| Background voxels | 462,373,770 |
| Foreground fraction | 10.93% |

## Outputs

- Binary mask: `9x9x9_octet_lattice_segmented.tif`
- Slice 380 visualization: `segmentation_slice_380.png`
- Threshold histogram: `intensity_histogram.png`
- Reproducible segmentation script: `run_segmentation.py`

The mask uses value 1 for voxels at or above the threshold and 0 otherwise. The bright lattice struts are isolated against the darker background in slice 380.
