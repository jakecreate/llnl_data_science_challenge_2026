"""Interactive Gabor-filter viewer for 2-D slices of a TIFF volume.

Examples
--------
    python test/gabor_filter.py data/9x9x9_octet_lattice/9x9x9_octet_lattice.tif
    python test/gabor_filter.py  # opens a file picker

The Gabor controls use the same names and units as ``cv2.getGaborKernel``.
In particular, ``theta`` is in radians and ``lambd`` is the wavelength in
pixels.  The selected viewpoint identifies the volume axis being sliced:
``x`` -> axis 0, ``y`` -> axis 1, and ``z`` -> axis 2.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import cv2
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from matplotlib.widgets import RadioButtons, Slider


AXES = {"x": 0, "y": 1, "z": 2}


def choose_input_file() -> Path:
    """Open a file picker when no input path was supplied on the command line."""
    root = tk.Tk()
    root.withdraw()
    filename = filedialog.askopenfilename(
        title="Choose a TIFF volume",
        filetypes=[("TIFF files", "*.tif *.tiff"), ("All files", "*.*")],
    )
    root.destroy()
    if not filename:
        raise SystemExit("No TIFF file selected.")
    return Path(filename)


def load_volume(path: Path) -> np.ndarray:
    """Load a TIFF image/stack and return a finite floating-point array."""
    volume = np.asarray(tifffile.imread(path))
    if volume.ndim == 2:
        volume = volume[np.newaxis, ...]
    if volume.ndim != 3:
        raise ValueError(f"Expected a 2-D image or 3-D TIFF stack, got shape {volume.shape}.")
    volume = volume.astype(np.float32, copy=False)
    if not np.isfinite(volume).all():
        volume = np.nan_to_num(volume, copy=False)
    return volume


def display_image(image: np.ndarray) -> np.ndarray:
    """Normalize an image for stable display without changing filter input."""
    image = np.asarray(image, dtype=np.float32)
    low, high = np.percentile(image, (1, 99))
    if high <= low:
        low, high = float(image.min()), float(image.max())
    if high <= low:
        return np.zeros(image.shape, dtype=np.float32)
    return np.clip((image - low) / (high - low), 0, 1)


def build_kernel(values: dict[str, float | int]) -> np.ndarray:
    """Build a kernel using OpenCV's getGaborKernel argument names."""
    ksize = int(values["ksize"])
    return cv2.getGaborKernel(
        (ksize, ksize),
        float(values["sigma"]),
        float(values["theta"]),
        float(values["lambd"]),
        float(values["gamma"]),
        float(values["psi"]),
        int(values["ktype"]),
    )


def run_viewer(path: Path) -> None:
    volume = load_volume(path)
    state = {"axis": "z", "slice": volume.shape[2] // 2}
    values: dict[str, float | int] = {
        "ksize": 21,
        "sigma": 5.0,
        "theta": 0.0,
        "lambd": 10.0,
        "gamma": 0.5,
        "psi": 0.0,
        "ktype": cv2.CV_32F,
    }

    fig, (raw_ax, kernel_ax, filtered_ax) = plt.subplots(1, 3, figsize=(14, 8))
    fig.canvas.manager.set_window_title(f"Gabor filter viewer — {path.name}")
    plt.subplots_adjust(left=0.07, right=0.97, top=0.91, bottom=0.36, wspace=0.22)
    raw_ax.set_title("Raw slice")
    kernel_ax.set_title("Active Gabor kernel")
    filtered_ax.set_title("Gabor-filtered slice")
    raw_image = raw_ax.imshow(np.zeros((2, 2)), cmap="gray", vmin=0, vmax=1)
    kernel_image = kernel_ax.imshow(np.zeros((3, 3)), cmap="coolwarm", vmin=-1, vmax=1)
    filtered_image = filtered_ax.imshow(np.zeros((2, 2)), cmap="gray")

    status = fig.text(0.5, 0.945, "", ha="center", va="center")
    kernel_status = fig.text(0.5, 0.325, "", ha="center", va="center", family="monospace")

    # All slider labels deliberately use OpenCV's parameter names.
    slider_specs = [
        ("ksize", 3, 51, 21, 2, "odd kernel width"),
        ("sigma", 0.1, 20.0, 5.0, 0.1, "Gaussian sigma"),
        ("theta", 0.0, 2 * np.pi, 0.0, np.pi / 36, "orientation (radians)"),
        ("lambd", 1.0, 40.0, 10.0, 0.5, "wavelength (pixels)"),
        ("gamma", 0.05, 2.0, 0.5, 0.05, "aspect ratio"),
        ("psi", -np.pi, np.pi, 0.0, np.pi / 36, "phase offset (radians)"),
    ]
    sliders: dict[str, Slider] = {}
    for row, (name, low, high, initial, step, description) in enumerate(slider_specs):
        y = 0.275 - row * 0.035
        slider_ax = fig.add_axes((0.18, y, 0.72, 0.018))
        sliders[name] = Slider(
            slider_ax, name, low, high, valinit=initial, valstep=step,
            valfmt="%1.3f", color="#4c78a8",
        )
        slider_ax.text(-0.19, 0.5, description, transform=slider_ax.transAxes,
                       ha="right", va="center", fontsize=8)

    axis_ax = fig.add_axes((0.03, 0.075, 0.10, 0.14))
    axis_radio = RadioButtons(axis_ax, ("x", "y", "z"), active=2)
    axis_ax.set_title("viewpoint", fontsize=9)
    ktype_ax = fig.add_axes((0.86, 0.075, 0.11, 0.14))
    ktype_radio = RadioButtons(ktype_ax, ("CV_32F", "CV_64F"), active=0)
    ktype_ax.set_title("ktype", fontsize=9)
    slice_ax = fig.add_axes((0.18, 0.075, 0.60, 0.018))
    slice_slider = Slider(slice_ax, "slice", 0, volume.shape[2] - 1,
                          valinit=state["slice"], valstep=1, valfmt="%d", color="#59a14f")

    def update(_value=None) -> None:
        axis = AXES[state["axis"]]
        index = int(np.clip(round(slice_slider.val), 0, volume.shape[axis] - 1))
        image = np.take(volume, index, axis=axis)
        kernel = build_kernel(values)
        filtered = cv2.filter2D(image, ddepth=-1, kernel=kernel)
        kernel_limit = max(float(np.abs(kernel).max()), 1e-12)
        raw_image.set_data(display_image(image))
        kernel_image.set_data(kernel)
        kernel_image.set_clim(-kernel_limit, kernel_limit)
        filtered_image.set_data(display_image(filtered))
        filtered_image.set_clim(0, 1)
        raw_ax.set_aspect("equal")
        kernel_ax.set_aspect("equal")
        filtered_ax.set_aspect("equal")
        status.set_text(f"{path.name}   shape={volume.shape}   viewpoint={state['axis']}   slice={index}")
        kernel_status.set_text(
            "kernel: " + "  ".join(f"{name}={values[name]}" for name, *_ in slider_specs)
        )
        fig.canvas.draw_idle()

    def update_parameter(name: str, slider: Slider) -> None:
        value = slider.val
        values[name] = int(round(value)) if name == "ksize" else float(value)
        update()

    def change_axis(label: str) -> None:
        state["axis"] = label
        maximum = volume.shape[AXES[label]] - 1
        slice_slider.ax.set_xlim(slice_slider.valmin, maximum)
        slice_slider.valmax = maximum
        slice_slider.set_val(min(state["slice"], maximum))
        state["slice"] = int(slice_slider.val)
        update()

    def change_ktype(label: str) -> None:
        values["ktype"] = cv2.CV_64F if label == "CV_64F" else cv2.CV_32F
        update()

    for name, *_ in slider_specs:
        sliders[name].on_changed(lambda value, parameter=name: update_parameter(parameter, sliders[parameter]))
    slice_slider.on_changed(lambda value: (state.__setitem__("slice", int(value)), update()))
    axis_radio.on_clicked(change_axis)
    ktype_radio.on_clicked(change_ktype)
    update()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="2-D TIFF image or 3-D TIFF stack")
    args = parser.parse_args()
    path = args.input or choose_input_file()
    if not path.is_file():
        parser.error(f"TIFF file not found: {path}")
    run_viewer(path)


if __name__ == "__main__":
    main()
