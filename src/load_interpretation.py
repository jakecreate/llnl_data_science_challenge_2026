import json
import os


def load_interpretation_batch(run_id: str, offset: int = 0, limit: int = 20) -> dict:
    """Page through flagged struts for a run, sorted by strut_id.

    Args:
        run_id: Run directory name under runs/.
        offset: Index of the first strut to return (0-based).
        limit: Max number of struts to return in this call.

    Returns:
        {"status": "ok", "rows": [...], "total": N,
         "next_offset": int, "has_more": bool}
        or {"status": "error", "message": "..."}
    """
    path = os.path.join("runs", run_id, "defects.json")

    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"status": "error", "message": f"no defects file at {path}"}
    except json.JSONDecodeError as exc:
        return {"status": "error", "message": f"malformed json in {path}: {exc}"}

    defects = data.get("defects", [])
    if not defects:
        return {"status": "ok", "rows": [], "total": 0,
                "next_offset": 0, "has_more": False}

    # stable order: without this, offset/limit paging is meaningless
    defects_sorted = sorted(defects, key=lambda d: d["strut_id"])

    total = len(defects_sorted)
    page = defects_sorted[offset:offset + limit]
    next_offset = offset + len(page)

    return {
        "status": "ok",
        "rows": page,
        "total": total,
        "next_offset": next_offset,
        "has_more": next_offset < total,
    }


# --- quick check against the fake data -------------------------------------
if __name__ == "__main__":
    os.makedirs("runs/fake001", exist_ok=True)
    # assumes defects.json already placed at runs/fake001/defects.json

    page1 = load_interpretation_batch("fake001", offset=0, limit=3)
    print("page 1:", [r["strut_id"] for r in page1["rows"]],
          "has_more:", page1["has_more"])

    page2 = load_interpretation_batch("fake001", offset=page1["next_offset"], limit=3)
    print("page 2:", [r["strut_id"] for r in page2["rows"]],
          "has_more:", page2["has_more"])

    missing = load_interpretation_batch("does_not_exist")
    print("missing run:", missing)