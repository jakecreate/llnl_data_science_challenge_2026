# AGENTS.md

### 1. Project Overview
This repository implements an autonomous multi-agent system for Exploratory Data Analysis (EDA) on multi-modal spatial datasets (3D `.tif` volumes, `.stl` meshes, and spatial graphs).

* **Frameworks:** FastMCP (tool server), Codex (execution harness).
* **Target Output:** Feature matrices (CSV/JSON) and structured Markdown EDA reports.

---

## 2. Directory & Data Guardrails
* **`data/` (READ-ONLY):** NEVER modify, delete, or overwrite raw dataset files.
* **`outputs/` (WRITE-ONLY):** All generated feature tables must go to `outputs/features/`. All synthesized reports go to `outputs/reports/`.
* **`mcp_server/` & `agents/`:** Code modifications must be tested using the FastMCP tool harness.

