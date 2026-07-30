import numpy as np
import cv2
import os
from skimage.morphology import skeletonize

def skeletonize_mask(file_path, output_path):
    """
    Creates a skeleton from a 3D segmentation mask.
    
    Args:
        file_path (str): Path to the .npy file containing the 3D mask.
        output_path (str): Path to save the extracted skeleton (.npy).
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"Loading mask from {file_path}...")
    mask = np.load(file_path)
    print(f"Original mask shape: {mask.shape}")
    
    # Ensure the mask is boolean
    if mask.dtype != bool:
        print("Converting mask to boolean array...")
        # Assuming background is 0 and object is > 0
        mask = mask > 0

    print("Extracting skeleton (this may take a moment for 3D data)...")
    skeleton = skeletonize(mask)
    
    print(f"Skeleton extracted. Non-zero voxels: {np.count_nonzero(skeleton)}")
    
    np.save(output_path, skeleton)
    print(f"Saved skeleton to: {output_path}")
    
    return skeleton

def skeletonize_segmented_png(input_filepath: str, output_filepath: str) -> str:
    try:
        # 1. Load the segmented PNG in grayscale
        image = cv2.imread(input_filepath, cv2.IMREAD_GRAYSCALE)
        
        if image is None:
            return f"Error: Could not read image at {input_filepath}"

        # 2. Convert to a boolean array
        # skeletonize() requires True/False values, not 0-255 pixel brightness.
        # Anything greater than 127 becomes True (active structure).
        bool_image = image > 127
        
        # 3. Perform the skeletonization
        skeleton = skeletonize(bool_image)
        
        # 4. Convert back to an 8-bit OpenCV format (0 and 255)
        skeleton_image = (skeleton * 255).astype(np.uint8)
        
        # 5. Export the skeletonized image
        success = cv2.imwrite(output_filepath, skeleton_image)
        
        if not success:
             return f"Error: Failed to write image to {output_filepath}"
             
    except Exception as e:
        return f"Error processing image: {e}"
        
    return f"Image successfully skeletonized and saved to {output_filepath}"

if __name__ == "__main__":
    # Hardcoded parameters for testing
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "unitcell", "unitcell.npy"))
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "octet_truss_unit_cell_skeleton.npy"))
    
    # Create the data directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    skeletonize_mask(
        file_path=file_path, 
        output_path=output_path
    )
