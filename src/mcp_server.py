from fastmcp import FastMCP
import numpy as np
from PIL import Image
from skeletonization import skeletonize_mask, skeletonize_segmented_png
from volume import volume_of_mesh
from tool_pyvista import *
from tool_opencv import *
import cv2
import pyvista as pv
import matplotlib.pyplot as plt
import tifffile
pv.OFF_SCREEN = True

# Initialize the MCP server
mcp = FastMCP("CT Segmentation")

@mcp.tool()
def segment_slice(input_filepath: str, output_filepath: str, threshold: float) -> str:
    """
    Segments a image slice based on a given density threshold value.
    
    Args:
        input_filepath: Path to the image containing the slice.
        output_filepath: Path indicating where the segmented slice should be.
        threshold: The density value to use as a threshold. Voxels >= threshold will be set to 1, others to 0.

    Returns:
        A status message indicating success and the save location, or an error message.
    """
    try:
        image = cv2.imread(input_filepath, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
        ret, thresh = cv2.threshold(image, threshold, 1.0, cv2.THRESH_BINARY_INV)
        output_image = (thresh * 255).astype(np.uint8)
        cv2.imwrite(output_filepath, output_image)
    except Exception as e:
        return f"Error while running segment_ct_dataset: {e}"
    return f"Dataset has been segmented and saved to {output_filepath}"

@mcp.tool()
def skeletonize_slice(input_filepath: str, output_filepath: str) -> str:
    """
    Creates a skeleton from a segmented image slice mask.
    
    Args:
        input_filepath: Path to the .png file containing the masked slice.
        output_filepath: Path to save the extracted skeleton (.png).
        
    Returns:
        A status message indicating success and the save location, or an error message.
    """
    try:
        skeletonize_segmented_png(input_filepath, output_filepath)
        return f"Successfully saved skeleton to {output_filepath}"
    except Exception as e:
        return f"Error while running skeletonize: {e}"

@mcp.tool()
def segment_ct_dataset(input_filepath: str, output_filepath: str, threshold: float) -> str:
    """
    Segments a image slice based on a given density threshold value.
    
    Args:
        input_filepath: Path to the image containing the image slice.
        output_filepath: Path indicating where the segmented .png file should be saved.
        threshold: The density value to use as a threshold. Voxels >= threshold will be set to 1, others to 0.
    
    Returns:
        A status message indicating success and the save location, or an error message.
    """
    try:
        if input_filepath.lower().endswith(('.tif', '.tiff')):
            voxels = tifffile.imread(input_filepath)
        else:
            voxels = np.load(input_filepath)
        mask = (voxels >= threshold).astype(np.uint8)
        np.save(output_filepath, mask)
    except Exception as e:
        return f"Error while running segment_ct_dataset: {e}"
    return f"Dataset has been segmented and saved to {output_filepath}"

@mcp.tool()
def skeletonize(input_filepath: str, output_filepath: str) -> str:
    """
    Creates a skeleton from a segmentation image mask.
    
    Args:
        input_filepath: Path to the .png file containing the smask.
        output_filepath: Path to save the extracted skeleton (.png).
        
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
        output_filepath: Path to save the screenshot
        slice: The index of the
    Returns:
        A status message indicating success and the save location, or an error message
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
        output_filepath: Path to save the screenshot

    Returns:
        A status message indicating success and the save location, or an error message
    """
    try:
        bitwise_xor(input_filepath_1, input_filepath_2, output_filepath)
        return f"Successfully saved bitwise xor to {output_filepath}"
    except Exception as e:
        return f"Error while running bitwise_xor_skeletion: {e}"

@mcp.tool()
def create_image_rectangle(input_filepath: str, output_filepath: str, top_left_point: tuple, bottom_right_point: tuple):
    """
    Takes in an image file and two points (x, y) which indicates the top left and bottom right of the rectangle.
    This creates a rectangle on the image.

    Args:
        input_filepath: Path to the skeletonized image file
        output_filepath: Path to the outputted image file
        top_left_point: A tuple (x, y) corresponding to the top left conrer of the rectangle
        bottom_right_point: A tuple (x, y) corresponding to the bottom right conrer of the rectangle

    Returns:
        An image with the rectangle box added to it.
    """
    try:
        create_rectangle(input_filepath, output_filepath, top_left_point, bottom_right_point)
        return f"Successfully saved image to {output_filepath}"
    except Exception as e:
        return f"Error while running create_image_rectangle: {e}"

if __name__ == "__main__":
    # Run the FastMCP server, exposing the tools over standard I/O (default)
    mcp.run()
