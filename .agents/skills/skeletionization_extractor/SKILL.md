---
name: skeletonization-extractor
description: Get the skeletonization of a .png file by first segmenting two .stl slices and then skeletonization the segmented slices.
---

# Skeletonization Extraction Protocol

You are the **Image Skeletonization Expert**. When this skill is active, follow these steps to process the data and output the data as two `.png`s:

### Step 1: .stl slices
- **Input 1 (Original mesh):** Load the `0.stl` file found in the `missing_struts` directory relative to the `/data` directory.
- **Input 2 (Defect mesh):** Load the `0.5.stl` file found in the `missing_struts` directory relative to the `/data` directory.
- **Action:** Get the slices of both `.stl` inputs using the `pyvista_screenshot` MCP tool at slice=#. Store the outputted slices into a directory named `output` in the working directory. The output filepath should be `0_z_#.png` and `0.5_z_#.png` for the respective `.stl` files.

### Step 2: Slice segmentation
- **Input 1 (Original mesh slice):** Load the `0_z_#.png` file found in the `output` directory relative to the working directory.
- **Input 2 (Defect mesh slice):** Load the `0.5_z_#.png` file found in the `output` directory relative to the working directory.
- **Action:** Use the `segment_slice` MCP tool to get the segmentation of both images with a threshold of 0.5. Store the outputted segmented slices into the directory `output` in the working directory. The output filepath should be `0_z_#_segmented.png` and `0.5_z_#_segmented.png` for the respective `.png` slices.

### Step 3: Segmented slices skeletonization
- **Input 1 (Original mesh segmented slice):** Load the `0_z_#_segmented.png` file found in the `output` directory relative to the working directory.
- **Input 2 (Defect mesh segmented slice):** Load the `0.5_z_#_segmented.png` file found in the `output` directory relative to the working directory.
- **Action:** Use the `skeletonize_slice` MCP tool to get the skeletonization of both segmented slices. Store the outputted skeletonized slices into the directory `output` in the working directory. The output filepath should be `0_z_#_skeletonized.png` and `0.5_z_#_skeletonized.png` for the respective skeletonized slices.

# Technical Constraints
- You don't have to import any prior libraries. All you need to do is run just the tools with the required inputs/parameters.
- Any instance of # used, outside of the headers, should be replaced with the corresponding slice index given to by the agent.