# AGENTS.md — LitBloomer Autonomous Data Explorer

This file governs how Codex should work in this repository. Read it before making changes. If a task conflicts with this file, follow this file.

## What this project is
LitBloomer is a 4-stage pipeline that turns a 3D volumetric `.tif` lattice scan into an automated analysis report (`.ipynb` + `.pdf`). The stages — Lit (literature/method selection), TDS (data validation & planning), CodA (code execution & export), Eval (QA & feedback routing) — are defined in `docs/final_project_idea.md`. That file is the spec of record; do not contradict it without flagging the conflict to the human first.

Codex is being used to build this pipeline as software, not to role-play the agents. Each "agent" should end up as a discrete, testable Python module or script with a clear input/output contract, exposed as FastMCP tools. Treat the agent boundaries in the spec as module boundaries in code.

## Repository layout (target — create as you go)
/src
  /lit/          # Agent 1 — method selection, Semantic Scholar/CrossRef fallback
  /tds/          # Agent 2 — data validation, dependency audit, step planning
  /coda/         # Agent 3 — sandboxed execution, notebook assembly, PDF export
  /eval/         # Agent 4 — completeness/visual/grammar/data-integrity checks
/schemas/        # Pydantic schemas for inter-agent payloads
/tests/          # unit tests per module + fixtures (small synthetic .tif stacks)
/Method-Wiki/    # local knowledge base, one {lattice_type}.md per type
/docs/           # final_project_idea.md and any ADRs
server.py        # FastMCP Server exposing agents as @mcp.tool() endpoints
requirements.txt

## Inter-agent contracts
Every hand-off in the spec is a JSON payload defined by Pydantic models in `/schemas`. Validate outputs against the schema before returning — don't let malformed payloads propagate downstream.

## Orchestration & FastMCP Mechanics
The orchestration layer is handled by the FastMCP server (`server.py`). 
* **State Management:** FastMCP must manage the state of the loops (e.g., tracking how many times Eval has rejected CodA's output).
* **Human Checkpoint 2.5:** Do not use `input()` which freezes headless servers. The TDS tool must return a payload with `"status": "requires_human_approval"`. FastMCP will expose a separate `@mcp.tool()` called `approve_tds_plan` that the Human calls to pass the payload to CodA.

## Loop constraints are hard limits, not suggestions
Enforce these in `server.py` state management:
* **TDS Total Budget:** Max 3 iterations total (Shared between Human revisions and Eval Type B escalations).
* **CodA ↔ Eval Budget:** Max 2 iterations (For Type A errors).
* On exceeding a limit, stop and emit the best-effort artifacts with an `UNRESOLVED_FLAG` and failure summary, per §2.5 of the spec. Do not silently retry past these caps.

## Sandboxing (CodA)
CodA's code execution must run in an isolated `subprocess` using Python's built-in `venv` module. Never let generated analysis code execute with the same privileges/network access as Codex itself. Package installs (`pip install`) happen inside this `venv` only after Human approval at Checkpoint 2.5 — don't auto-install anything CodA "thinks" it needs.

## What Codex should do unprompted
* Write unit tests alongside each module (`pytest`). A module without tests is not done.
* Validate `.tif` inputs are 3D (Z, Y, X) arrays before passing them downstream using `tifffile` — fail loudly and early, per TDS's spec'd behavior.
* Keep external API calls (Semantic Scholar, CrossRef) behind a thin client wrapper in `/src/lit/clients.py` so they're mockable in tests.
* Use `nbconvert --to html` and a headless browser library (like `playwright`) for PDF rendering to avoid heavy OS-level dependencies like LaTeX/GTK3.

## What Codex should NOT do
* Don't implement Lit's external-API fallback to hit real network APIs in tests — mock them.
* Don't skip the Human Checkpoint 2.5 step by auto-routing TDS output to CodA.
* Don't merge Eval's four checks into one pass/fail blob — keep step completeness, visual legibility, proofreading, and data-integrity as separately reported checks.
* Don't install or run PDF rendering tools without checking `requirements.txt` first, per TDS's dependency-audit responsibility.

## Validation before calling something done
For any module: run its unit tests, then run it end-to-end against a small synthetic `.tif` fixture in `/tests/fixtures`. For the FastMCP server: simulate a full pipeline pass on a fixture and confirm the loop counters, schema validation, and `UNRESOLVED_FLAG` path all work by forcing at least one failure case.