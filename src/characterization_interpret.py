import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone


REQUIRED_COLUMNS = [
    "strut_id", "class", "group_id", "confidence",
    "occupancy", "gap_length_voxels", "gap_position_frac",
    "mean_density", "min_density", "bbox_extent_frac",
    "centroid_offset_voxels", "principal_axis_angle_deg", "reasoning",
]

VALID_CLASSES = {"missing", "disconnected", "thin", "bent", "uncertain"}
VALID_CONFIDENCE = {"high", "low"}


def _validate_rows(rows: list[dict]) -> list[str]:
    """Return a list of problems found. Empty list means the rows are clean."""
    problems = []

    if not rows:
        problems.append("no rows supplied")
        return problems

    seen_ids = set()
    for i, row in enumerate(rows):
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in row]
        if missing_cols:
            problems.append(f"row {i}: missing columns {missing_cols}")
            continue  # can't check further fields on this row safely

        extra_cols = [c for c in row if c not in REQUIRED_COLUMNS]
        if extra_cols:
            problems.append(f"row {i}: unexpected columns {extra_cols}")

        sid = row["strut_id"]
        if sid in seen_ids:
            problems.append(f"row {i}: duplicate strut_id {sid}")
        seen_ids.add(sid)

        if row["class"] not in VALID_CLASSES:
            problems.append(f"row {i}: invalid class '{row['class']}'")

        if row["confidence"] not in VALID_CONFIDENCE:
            problems.append(f"row {i}: invalid confidence '{row['confidence']}'")

        word_count = len(str(row["reasoning"]).split())
        if word_count > 15:
            problems.append(
                f"row {i} (strut {sid}): reasoning is {word_count} words, limit is 15"
            )

    return problems


def write_characterization_outputs(run_id: str, rows: list[dict]) -> dict:
    """Validate the schema and write characterization.csv + .md atomically.

    Args:
        run_id: Run directory name under runs/.
        rows: One dict per flagged strut, matching REQUIRED_COLUMNS exactly.

    Returns:
        {"status": "ok", "csv_path": ..., "md_path": ..., "n_rows": N}
        or {"status": "error", "message": "...", "problems": [...]}
    """
    problems = _validate_rows(rows)
    if problems:
        return {"status": "error", "message": "validation failed", "problems": problems}

    run_dir = os.path.join("runs", run_id)
    os.makedirs(run_dir, exist_ok=True)
    csv_path = os.path.join(run_dir, "characterization.csv")
    md_path = os.path.join(run_dir, "characterization.md")

    # --- write CSV atomically: write to a temp file, then rename into place.
    # If the process dies mid-write, the real characterization.csv is either
    # the old complete version or never touched -- never a half-written file.
    tmp_csv = csv_path + ".tmp"
    with open(tmp_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    os.replace(tmp_csv, csv_path)

    # --- build the markdown summary
    class_counts = Counter(row["class"] for row in rows)
    n_uncertain = class_counts.get("uncertain", 0)

    groups = defaultdict(list)
    for row in rows:
        groups[row["group_id"]].append(row)

    lines = []
    lines.append(f"# Characterization summary — run {run_id}")
    lines.append(f"_generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z_")
    lines.append("")
    lines.append("## Counts per class")
    for cls in sorted(class_counts):
        lines.append(f"- {cls}: {class_counts[cls]}")
    lines.append("")
    lines.append("## Groups")
    lines.append("")
    lines.append("| group_id | class(es) | n_struts | strut_ids |")
    lines.append("|---|---|---|---|")
    for gid in sorted(groups, key=lambda g: (g == 0, g)):
        members = groups[gid]
        classes = ", ".join(sorted({m["class"] for m in members}))
        ids = ", ".join(str(m["strut_id"]) for m in members)
        lines.append(f"| {gid} | {classes} | {len(members)} | {ids} |")
    lines.append("")
    lines.append("## Run accounting")
    lines.append(f"- processed struts: {len(rows)}")
    lines.append(f"- uncertain struts: {n_uncertain}")
    lines.append("- failed rows: 0")
    lines.append("- processing completed: yes")

    tmp_md = md_path + ".tmp"
    with open(tmp_md, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp_md, md_path)

    return {"status": "ok", "csv_path": csv_path, "md_path": md_path, "n_rows": len(rows)}

# Quick test — add this to write_characterization_outputs.py at the bottom
if __name__ == "__main__":
    # load a page
    from load_interpretation import load_interpretation_batch
    page = load_interpretation_batch("fake001", 0, 5)
    
    # classify by hand (fake this for now)
    rows = []
    for defect in page["rows"]:
        rows.append({
            "strut_id": defect["strut_id"],
            "class": "missing" if defect["occupancy"] < 0.15 else "disconnected" if defect.get("gap_length_voxels", 0) > 3 else "uncertain",
            "group_id": 0,
            "confidence": "high" if defect["occupancy"] < 0.15 else "low",
            "occupancy": defect["occupancy"],
            "gap_length_voxels": defect["gap_length_voxels"],
            "gap_position_frac": defect["gap_position_frac"],
            "mean_density": defect["mean_density"],
            "min_density": defect["min_density"],
            "bbox_extent_frac": defect["bbox_extent_frac"],
            "centroid_offset_voxels": defect["centroid_offset_voxels"],
            "principal_axis_angle_deg": defect["principal_axis_angle_deg"],
            "reasoning": "test row from fake data",
        })
    
    result = write_characterization_outputs("fake001", rows)
    print(result)


# # --- quick check ------------------------------------------------------------
# if __name__ == "__main__":
#     good_rows = [
#         {
#             "strut_id": 1042, "class": "missing", "group_id": 0, "confidence": "high",
#             "occupancy": 0.04, "gap_length_voxels": 0.0, "gap_position_frac": 0.0,
#             "mean_density": 0.03, "min_density": 0.0, "bbox_extent_frac": 0.06,
#             "centroid_offset_voxels": 0.4, "principal_axis_angle_deg": 0.0,
#             "reasoning": "rule 1, occupancy 0.04 and bbox 0.06, both below threshold",
#         },
#         {
#             "strut_id": 1533, "class": "disconnected", "group_id": 1, "confidence": "high",
#             "occupancy": 0.61, "gap_length_voxels": 7.8, "gap_position_frac": 0.48,
#             "mean_density": 0.71, "min_density": 0.02, "bbox_extent_frac": 0.97,
#             "centroid_offset_voxels": 0.9, "principal_axis_angle_deg": 1.2,
#             "reasoning": "rule 2, mid-span gap 7.8 vox, material both sides",
#         },
#         {
#             "strut_id": 1534, "class": "disconnected", "group_id": 1, "confidence": "high",
#             "occupancy": 0.58, "gap_length_voxels": 8.4, "gap_position_frac": 0.52,
#             "mean_density": 0.69, "min_density": 0.01, "bbox_extent_frac": 0.96,
#             "centroid_offset_voxels": 1.1, "principal_axis_angle_deg": 0.8,
#             "reasoning": "rule 2, mid-span gap 8.4 vox, adjacent to strut 1533",
#         },
#     ]

#     result = write_characterization_outputs("fake001", good_rows)
#     print("good case:", result)

#     bad_rows = [{"strut_id": 9999, "class": "not_a_real_class", "confidence": "high"}]
#     result_bad = write_characterization_outputs("fake001", bad_rows)
#     print("bad case:", result_bad)

#     if result["status"] == "ok":
#         print("\n--- characterization.md ---")
#         with open(result["md_path"]) as f:
#             print(f.read())
