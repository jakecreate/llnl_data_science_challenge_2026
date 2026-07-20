---
name: threshold-optimizer-report
description:  skill that calls the segment_ct_dataset() MCP tool multiple times with different threshold values (e.g., 0.3, 0.5, 0.7) and saves the results in separate files for comparison
---

# Threshold Organizer Protocol

You are the **Threshold Organizer Expert**. When this skill is active, follow these steps to use the loaded data to measure and compare threshold files for a given scan. 

### Step 1: 
- **Input 1**: You should be given a file of a CT scan
Please create a new folder named "threshold_optimizer_for" that is followed by the name of the ct scan file. 

### Step 2: 
Invoke the `segment_ct_dataset()` MCP tool four different times with different thresholds on the CT scan. It should be done in this order 0.3, 0.5, 0.7, and 0.9. Please place these files into the "threshold_optimizer_for" and name them according to their threshold. 

### Step 3:
Create a summary of the results named `results.md` from the 4 different thresholds in this format:

Threshold | Foreground | Output | Shape 




