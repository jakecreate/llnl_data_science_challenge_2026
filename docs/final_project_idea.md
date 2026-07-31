# LitBloomer Autonomous Data Explorer Implementation Document

## 1. System Overview

The LitBloomer system is a multi-agent pipeline designed for producing automated data analysis reports on 3D volumetric lattice structures, specifically utilizing `.tif` stacks.

**Global Inputs (Human)**

- `lattice_type` (e.g., _Strut/Beam_).
    
- `specific_type` (e.g., _Octet_).
    
- `data_file_path` (Path to 3D volumetric `.tif` stack).
    

## 2. Agent Pipeline Architecture

### 2.1. Agent 1: Literature Agent (Lit)

**Purpose:** Method Selection and API Fallback. **Inputs:** `lattice_type`, `specific_type`, `data_file_path`. **Assumptions:** The data must strictly be a 3D volumetric `.tif` stack.

**Execution Logic:**

- Search the local knowledge base located at `Method-Wiki/{lattice_type}.md`.
    
- If the local wiki contains fewer than 3 usable methods, trigger a fallback to query external research APIs, specifically the Semantic Scholar API and CrossRef API, to retrieve 5 candidate methods.
    
- Automatically append programmatic keywords, such as `+ "Python" OR "scikit-image" OR "algorithm" OR "3D volumetric"`, to optimize the query and ensure candidate methods are computable rather than purely theoretical.
    
- Filter the candidate methods for 3D volumetric `.tif` data.
    
- Select 2 to 3 cohesive, complementary, and insightful analysis methods.
    

**Outputs:**

- A JSON object containing 2 to 3 selected analysis methods, including their Name and a Detailed Description.
    

### 2.2. Agent 2: Technical Data Scientist (TDS)

**Purpose:** Data Validation, Step Breakdown, and Package Audit. **Inputs:** 2 to 3 selected analysis methods from Lit, requests for clearer plans or step revisions from the Human Checkpoint, or escalated architectural/data errors from Eval.

**Execution Logic:**

- Run an early metadata check on the `data_file_path` using tools like `tifffile` to ensure the file exists, is readable, and is a valid 3D array $(Z, Y, X)$.
    
- If the data validation is invalid, abort immediately and alert the Human.
    
- Inspect the local `requirements.txt` against packages required for the selected methods.
    
- Identify missing dependencies, explicitly including PDF rendering engines such as `nbconvert`, `weasyprint`, or `pandoc`.
    
- Break down the analysis methods into an ordered, step-by-step implementation plan for CodA.
    

**Outputs:**

- Ordered implementation steps and a proposed list of required Python/System packages.
    

### 2.3. Checkpoint 2.5: Human Plan Review

**Purpose:** Sanity Check and Package Approval. **Inputs:** The TDS implementation plan and the proposed package list.

**Execution Logic:**

- The Human reviews the plan for clarity and feasibility.
    
- The Human approves any new package installations.
    
- If approved, the system proceeds directly to Step 3, passing to CodA.
    
- If not approved or if it needs revision, return feedback to TDS to adjust the implementation steps.
    

**Loop Constraints:**

- Maximum 3 iterations between Human and TDS.
    

### 2.4. Agent 3: Coding Agent (CodA)

**Purpose:** Environment Setup, Step Execution, and Export. **Inputs:** Approved implementation steps and approved package list from TDS/Human, or fix instructions from Eval. **Execution Model:** Interactive Sandbox or REPL.

**Execution Logic:**

- Install Human-approved packages in the sandbox before executing any analysis code.
    
- Execute or edit, if given Eval instructions, the code step-by-step in the isolated Python environment to verify correctness.
    
- Handle minor local syntax or runtime errors iteratively before compiling the final output.
    
- Assemble the successfully executed code into a unified Jupyter Notebook (`.ipynb`).
    
- Render the finalized `.pdf` report using the approved rendering dependencies.
    

**Outputs:**

- Dual artifacts consisting of a Raw `.ipynb` file and a Rendered `.pdf` file.
    

### 2.5. Agent 4: Evaluator (Eval)

**Purpose:** Quality and Completeness Audit. **Inputs:** TDS implementation steps and CodA artifacts (`.ipynb` & `.pdf`).

**Evaluation Logic & Criteria:**

- Verify step completeness to check if all TDS implementation steps were executed.
    
- Conduct a visual inspection to check if generated charts are legible, featuring clear axis labels, readable legends, and non-overlapping titles.
    
- Proofread to determine if there are spelling or grammatical errors in markdown report cells.
    
- Verify data integrity by ensuring the code executed cleanly without silent data distortion.
    

**Feedback Routing Logic:**

- Route Type A errors (Coding, Visual, or Grammatical Errors) directly back to CodA with specific fix instructions.
    
- Escalate Type B errors (Architectural, Data, or Dependency Errors) back to TDS to modify the implementation strategy.
    
- On final failure, output best-effort report artifacts with an explicit `UNRESOLVED_FLAG` and a failure summary for the human user.
    

## 3. Control Flow & Loop Constraints Summary

|**Component**|**Target (Success)**|**Feedback Routing (Failure)**|**Max Iteration Constraints**|
|---|---|---|---|
|**Lit**|TDS|N/A|N/A|
|**TDS**|Human Checkpoint (2.5)|N/A|3 loops (with Human), 2 loops (with Eval)|
|**Human (2.5)**|CodA|TDS (Needs Revision)|3 loops|
|**CodA**|Eval|N/A|2 loops (with Eval)|
|**Eval**|Final Delivery|CodA (Type A) / TDS (Type B)|2 loops (Type A), 2 loops (Type B)|