from fastmcp import FastMCP
import numpy as np
from PIL import Image
from skeletonization import skeletonize_mask
from volume import volume_of_mesh
from tool_pyvista import *
from tool_opencv import *
import cv2
import pyvista as pv
import matplotlib.pyplot as plt

# Initialize the MCP server
mcp = FastMCP("CT Segmentation")

@mcp.tool()
def segment_ct_dataset(input_filepath: str, output_filepath: str, threshold: float) -> str:
    """
    Segments a 3D CT dataset based on a given density threshold value.
    
    Args:
        input_filepath: Path to the input .npy file containing the 3D CT scan data.
        output_filepath: Path indicating where the segmented .npy file should be saved.
        threshold: The density value to use as a threshold. Voxels >= threshold will be set to 1, others to 0.
    
    Returns:
        A status message indicating success and the save location, or an error message.
    """
    try:
        voxels = np.load(input_filepath)
        mask = (voxels >= threshold).astype(np.uint8)
        np.save(output_filepath, mask)
    except Exception as e:
        return f"Error while running segment_ct_dataset: {e}"
    return f"Dataset has been segmented and saved to {output_filepath}"

@mcp.tool()
def visualize_slice(input_filepath: str, output_filepath: str, slice_index: int, axis: int = 0) -> str:
    """
    Loads a 3D CT dataset from a .npy file and saves a visualization of a specific slice to an image file.
    
    Args:
        input_filepath: Path to the input .npy file containing the 3D CT data.
        output_filepath: Path indicating where the output image should be saved (e.g., .png).
        slice_index: The index of the slice to visualize.
        axis: The axis along which to take the slice (0, 1, or 2). Default is 0.
        
    Returns:
        A status message indicating success and the save location, or an error message.
    """
    try:
        voxels = np.load(input_filepath)
        slice = np.take(voxels, slice_index, axis=axis)

        slice_min, slice_max = slice.min(), slice.max()
        if slice_max > slice_min:
            normalized = ((slice - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(slice, dtype=np.uint8)

        image = Image.fromarray(normalized)
        image.save(output_filepath)
    except Exception as e:
        return f"Error while running visualize_slice: {e}"
    return f"Dataset has been sliced and saved to {output_filepath}"

@mcp.tool()
def skeletonize(input_filepath: str, output_filepath: str) -> str:
    """
    Creates a skeleton from a 3D segmentation mask.
    
    Args:
        input_filepath: Path to the .npy file containing the 3D mask.
        output_filepath: Path to save the extracted skeleton (.npy).
        
    Returns:
        A status message indicating success and the save location, or an error message.
    """
    try:
        skeletonize_mask(input_filepath, output_filepath)
        return f"Successfully saved skeleton to {output_filepath}"
    except Exception as e:
        return f"Error while running skeletonize: {e}"

@mcp.tool()
def pyvista_screenshot(input_filepath: str, output_filepath: str, slice: int):
    """
    Take a screenshot of an .stl file for evaluation of defects.

    Args:
        input_filepath: Path to the .stl file in missing_struts
        output_filepath: Path to save the screenshot (Should point to the screenshots directory and be in a .png format)
        slice: The index of the
    Returns:
        A .png image in the screenshots directory representing a slice on the z_axis at the point of the slice
    """
    try:
        mesh = load(input_filepath)
        screenshot_slice(mesh, slice, output_filepath)
        return f"Successfully saved screenshot slice to {output_filepath}"
    except Exception as e:
        return f"Error while running pyvista_screenshot: {e}"

@mcp.tool()
def bitwise_xor_skeletion(input_filepath_1: str, input_filepath_2: str, output_filepath: str):
    """
    Takes in two skeletonized images and get a bitwise xor of both images.
    Args:
        input_filepath_1: Path to the skeletonized image file 1
        input_filepath_2: Path to the skeletonized image file 2
        output_filepath: Path to save the screenshot (Should point to the slices directory and be in a .png format)
    Returns:
        A .pngimage of the bitwise xor of both input images
    """
    try:
        bitwise_xor(input_filepath_1, input_filepath_2, output_filepath)
        return f"Successfully saved bitwise xor to {output_filepath}"
    except Exception as e:
        return f"Error while running bitwise_xor_skeletion: {e}"

if __name__ == "__main__":
    # Run the FastMCP server, exposing the tools over standard I/O (default)
    mcp.run()
