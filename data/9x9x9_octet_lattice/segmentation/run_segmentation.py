from pathlib import Path
import numpy as np
import tifffile
from skimage.filters import threshold_otsu
import matplotlib.pyplot as plt

root = Path(__file__).parent.parent
out = root / "segmentation"
src = root / "9x9x9_octet_lattice.tif"
mask_path = out / "9x9x9_octet_lattice_segmented.tif"
slice_path = out / "segmentation_slice_380.png"
hist_path = out / "intensity_histogram.png"

with tifffile.TiffFile(src) as tif:
    reference = tif.pages[380].asarray()
    threshold = float(threshold_otsu(reference))
    shape = (len(tif.pages),) + reference.shape
    foreground = 0
    with tifffile.TiffWriter(mask_path, bigtiff=True) as writer:
        for page in tif.pages:
            mask = (page.asarray() >= threshold).astype(np.uint8)
            foreground += int(mask.sum())
            writer.write(mask, photometric="minisblack", compression="deflate")

background = int(np.prod(shape) - foreground)
plt.figure(figsize=(8, 5))
plt.hist(reference.ravel(), bins=256, color="steelblue")
plt.axvline(threshold, color="crimson", label=f"Otsu = {threshold:.0f}")
plt.xlabel("Intensity"); plt.ylabel("Pixels"); plt.legend(); plt.tight_layout()
plt.savefig(hist_path, dpi=150); plt.close()

plt.imsave(slice_path, ((reference >= threshold).astype(np.uint8)), cmap="gray", vmin=0, vmax=1)
(out / "segmentation_stats.txt").write_text(
    f"input={src.name}\nslices={shape[0]}\nheight={shape[1]}\nwidth={shape[2]}\n"
    f"threshold_otsu_slice_380={threshold:.3f}\nforeground_voxels={foreground}\n"
    f"background_voxels={background}\nforeground_fraction={foreground / (foreground + background):.6f}\n"
)
print(f"threshold={threshold:.3f} foreground={foreground} background={background}")
