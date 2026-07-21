---
name: rubric-segmentation
description: 
---

## Criteria:

Structural Integrity: Does the result capture the connectivity of the lattice struts compared to the ground truth?
False Positives/Negatives: Identify over-segmentation (extra noise) or under-segmentation (missing struts).
Topology: Are the nodes (junctions) preserved?
Noise and Artifacts: Does the result image contain noise or artifacts not present in the clean ground truth?

## Scoring (0-5):

5: Identical to ground truth. No missing structures, no false positives.
4: Excellent with very minor differences.
3: Main topology is correct, but noticeable noise or thin struts are missing.
2: Fair, but with significant differences (e.g., large chunks missing).
1: Major structural failure or excessive noise.
0: Blank or unrelated output.

## Instructions

Create a rubric based on the criteria and scoring I gave you