# Threshold Optimizer Results

Input: `data/unitcell/unitcell.npy`

| Threshold | Foreground | Output | Shape |
|---:|---:|---|---|
| 0.3 | 0 | `threshold_0.3.npy` | 256 × 256 × 256 |
| 0.5 | 0 | `threshold_0.5.npy` | 256 × 256 × 256 |
| 0.7 | 0 | `threshold_0.7.npy` | 256 × 256 × 256 |
| 0.9 | 0 | `threshold_0.9.npy` | 256 × 256 × 256 |

## Finding

The MCP server applied each requested threshold correctly. All four masks are empty and byte-for-byte identical (SHA-256 `725e45ddd8344721d33e5942ab0c7605144ec5cc4114eac06394beb23f050473`).

The source intensity range is approximately `-0.003129` to `0.015258`. The skill's thresholds (`0.3`, `0.5`, `0.7`, and `0.9`) all exceed the maximum source intensity, so no voxel can be classified as foreground. A meaningful comparison requires either normalizing the source volume to `[0, 1]` before thresholding or selecting thresholds within the source intensity range.
