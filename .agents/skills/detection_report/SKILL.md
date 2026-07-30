---
name: detection-report
description: Uses the skeletonization of two slices at a given height to determine whether or not the slices has a defect.
---

# Report Generation Protocol

You are the **Detection Report Expert**. When this skill is active, follow these steps to determine whether or not there is a defect in the given slices:

### Step 1: Load images
- **Input 1 (0 skeletonized slice):** Load the `0_z_#_skeletonized.png` image found in the `output` file relative to the working directory.
- **Input 2 (0.5 skeletonized slice):** Load the `0.5_z_#_skeletonized.png` image found in the `output` file relative to the working directory.
- **Action:** Determine whether or not `0.5_z_#_skeletonized.png` has a defect by using the image alongside `0_z_#_skeletonized.png` to make a conclusion.

### Step 2: Document results
In the terminal, say if there. Afterwards, explain your reasonings behind your decision.

# Technical Constraints
- All reasoning should be done through visually looking at the two images. No python script should be created for the reasoning and no tools should be evoked for the process. 
- Any instance of # used, outside of the headers, should be replaced with the corresponding slice index given to by the agent.