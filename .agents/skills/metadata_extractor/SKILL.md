---
name: metadata-extractor
description: Loads a generated .npy file and prints out basic metadata: the shape, the data type, and the maximum and minimum values to the terminal.
---

# Report Generation Protocol

You are the **Non Destructive Evaluation Report Expert**. When this skill is active, follow these steps to process the data and output the data into the terminal:

### Step 1: Load file
- **Input 1 (Original Volume):** Load the raw intensity data from the original `.npy` file.

### Step 2: Output 
Extract the shape, data type, and the maximum and minimum values of the `.npy` file into the terminal.

# Technical Constraints
- if you created python scripts, make sure to remove them once you are finished. 