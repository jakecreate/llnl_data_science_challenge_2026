from fastmcp import FastMCP
import numpy as np
import matplotlib.pyplot as plt
import skeletonization as skel

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
        ct_data = np.load(input_filepath)
        
        if ct_data.ndim != 3:
            return f"Error: Expected a 3D dataset, but got {ct_data.ndim}D."
        
        segmented_data = (ct_data >= threshold).astype(np.uint8)
        np.save(output_filepath, segmented_data)
        
        return f"Segmentation successful. Segmented data saved to {output_filepath}."
    
    except Exception as e:
        return f"An error occurred: {e}"


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

    ct_data = np.load(input_filepath)
    if axis == 0:
        slice_data = ct_data[slice_index, :, :]
    elif axis == 1:
        slice_data = ct_data[:, slice_index, :]
    elif axis == 2:
        slice_data = ct_data[:, :, slice_index]
    else:
        return "Axis must be 0, 1, or 2."

    plt.imshow(slice_data, cmap="gray")
    plt.savefig(output_filepath)

    return f"Visualization saved to {output_filepath}."

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
    skel.skeletonize_mask(input_filepath, output_filepath)
    return f"Skeletonization completed. Skeleton saved to {output_filepath}."

if __name__ == "__main__":
    # Run the FastMCP server, exposing the tools over standard I/O (default)
    mcp.run()
