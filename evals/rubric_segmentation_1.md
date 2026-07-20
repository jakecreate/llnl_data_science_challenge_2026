Evaluation rubric for comparing a resulting image from the ground truth image.

## Rubric Criteria:
**Structural Integrity**: Does the reuslt capture the connectivity of the lattice structs compared to the ground truth?
**False Positives/Negatives**: Identify over-segmentation (extra noise) or under-segmentation (missing struts)
**Topology**: Are the nodes (junctions) preserved?
**Nosie and Artifacts**: Does the result image contain noise or artifacts not present in the clean ground truth?

## Scoring (0-5):
5: Identical to ground truth. No missing structures, no false positives
4: Excellent with very minor differences
3: Main topology is correct, but noticeable noise or thin struts are missing.
2: Fair, but with significant differences (For example, large chunks missing)
1: Major structural failure or excessive noise.
0: Blank or unrelated output.

## Output
Return a JSON block that contains "reasoning" and "score". "reasoning" should have the reasoning for the score and "score" should be the score based on the four criterias.