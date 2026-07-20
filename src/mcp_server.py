import numpy as np
from fastmcp import FastMCP
from skimage.filters import threshold_otsu, try_all_threshold
from PIL import Image

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

    # Raw CT scan data turns into .npy file 

    try:
        # A simulated CT scan: A 3D Numpy array (.npy) where values correspond to X-ray CT density within [0, 1].
        
        # Segmentation based on the color density values in the .npy file, the saved file should be binary 0/1 as a mask
        # the same size/dimesions as the original .npy file

        file_to_segment = np.load(input_filepath)

        thresh = threshold_otsu(file_to_segment)
        mask = (file_to_segment > thresh).astype(np.uint8)  

        np.save(output_filepath, mask)

    except FileNotFoundError:
        return f"Segmentation failed: input file not found: {input_filepath}"
    else:
        return (
            f"Segmentation successful. Saved to: {output_filepath}. "
            f"Otsu threshold: {float(thresh):.10g}."
        )


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
        file_to_visualize = np.load(input_filepath)

        specified_slice = np.take(file_to_visualize, slice_index, axis=axis)

        s = specified_slice.astype(np.float32)
        s = (s - s.min()) / (s.max() - s.min()) * 255
        visualized_slice = Image.fromarray(s.astype(np.uint8), mode='L')

        visualized_slice.save(output_filepath)
    
    except FileNotFoundError:
        return f"Visualization failed: input file not found: {input_filepath}"

    else:
        return (f"Visualization successful. Saved to: {output_filepath}. ")
    
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
    pass # Implementation goes here, calling skeletonize_mask internally

if __name__ == "__main__":
    # Run the FastMCP server, exposing the tools over standard I/O (default)
    mcp.run()
