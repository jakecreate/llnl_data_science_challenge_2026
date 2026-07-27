# Open-Ended Agentic AI for Materials Science Project

| Layer                | Answers                                               | Scope                            |
| -------------------- | ----------------------------------------------------- | -------------------------------- |
| `AGENTS.md`          | "What are the rules for working in this repo?"        | Always loaded                    |
| `.agents/skills/`    | "How do I perform this specific recurring task well?" | Loaded on demand, cross-tool     |
| `.codex/agents/`     | "Who does the work, with what permissions and model?" | Codex-specific, spawned per task |
| `.codex/config.toml` | "How is Codex configured for this project?"           | Codex-specific, always applied   |
| `src/` + `data/`     | The actual code and data being operated on            | N/A                              |

In the second half of the challenge, the training wheels come off. You are free to move beyond the raw Codex CLI and explore different frameworks and paradigms to build a sophisticated multi-agent system.

## New Dataset: Octet Lattices with Missing Struts

For the final project, we will focus on a more complex, real-world dataset: **X-ray CT scan of octet lattice structures with intentionally missing struts**, which is available in **.data/missing_struts**. 


This dataset includes CT data of 9x9x9 Octet lattices printed via laser powder bed fusion (LPBF) using Ti5553. These lattices were designed with intentionally missing struts at varying percentages (0%, 0.1%, 0.5%, and 1%) to develop inspection techniques for identifying defects.
Unit cell size 4.56 mm at 10% relative density or 350 micron strut diameter. There is also accompanying STL files of the design used to print the lattices. It uses X-ray CT to inspect truss lattice cubes and quantifies both missing and disconnected struts, which are the primary defect classes the released CT data is intended to support. It also notes that measured missing strut percentages may exceed nominal values and that disconnected struts are commonly observed, providing important context for downstream users performing validation, training, or benchmarking of inspection methods. 

More information about the data can be found in the following publication by Tran et al.: 
Tran, B. et al., [“Resonant ultrasound spectroscopy measurement and modeling of additively manufactured octet truss lattice cubes,”](https://www.osti.gov/servlets/purl/2246722) *NDT&E International* 138 (2023) 102870.

**Dataset Contents:**
*   **CT Data:** Volumetric data provided as a series of `.tif` slices.
*   **Design STL:** The original STL files used for printing.
*   **3D Graph Description:** Structural information describing the lattice geometry (e.g. node and edge lists).

> **Note:** The STL file is not aligned/registered with the TIF or JSON file. Registration is a problem by itself. If you do not want to work on registration, `210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json` is already aligned with the respective TIF file of the same name.

### Project Goals

Your objective is to implement a multi-agent system that can visualize, analyze, and reason about this dataset. You should build upon what you learned in Part 1 (MCP tools, skills, subagents) but aim for a higher level of autonomy and integration.

### Project Ideas

Here are some suggested tracks for your multi-agent system. You can choose one of these or propose your own!

1.  **The Autonomous Data Explorer**
    *   **Concept:** Build a system of agents that performs exploratory data analysis.
    *   **Workflow:** One agent explores the dataset directory (primarily file names), while others figure out appropriate methods to extract features from the `.tif` volumes, `.stl` files, and 3D graphs.
    *   **Components:** Include a **Literature Research Agent** to find relevant analysis methods and a **Coding Agent** to implement the extraction logic.
    *   **Output:** Comprehensive reports on how to analyze the data either computationally or using existing specialized software.

2.  **The Visual Reasoner**
    *   **Concept:** Equip an agent with the ability to "see" and reason about 3D data.
    *   **Workflow:** Integrate a visualization engine (e.g., **PyVista**, **ParaView**, or **Napari**) within the agentic loop.
    *   **Capability:** The system should render the lattice structures and allow the agent to reason about the visualizations—identifying anomalies or structural characteristics directly from the rendered output.

3.  **The Interactive Co-Pilot & Dashboard**
    *   **Concept:** Create a user-centric analysis platform.
    *   **Workflow:** Build an interactive dashboard that visualizes the data in 3D and features a chat interface.
    *   **Capability:** The agent should be able to "see" the current viewport of the dashboard and execute analysis tasks in real-time based on your questions (e.g., "Analyze the connectivity in the region I'm looking at").

