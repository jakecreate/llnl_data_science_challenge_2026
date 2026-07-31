# LitBloomer

> **⚠️ Project Status: Incomplete / Work in Progress**
> Please note that this project is currently incomplete and has yet to combine all development branches into a single unified pipeline. 

---

## 📌 Overview

**LitBloomer** automates the Exploratory Data Analysis (EDA) of lattice CT scans using agentic AI orchestration. By replacing slow, manual specialist analysis with targeted AI agents, LitBloomer determines analysis methods based solely on a given lattice structure (such as the *octet-truss*). 

Integrated with a **custom registration method**, LitBloomer delivers spatial alignment and automated reporting while significantly reducing total analysis time and token usage.

---

## 💡 Why AI Agentic Workflow?

* **Eliminates Manual Bottlenecks:** Manual CT scan EDA can take a specialist hours. LitBloomer automates the workflow: **Literature Search → Implementation Plan → Code Generation → Review**.
* **Model Context Protocol (MCP):** Gives each specialized agent one narrow, verifiable job instead of relying on a single long, unreliable prompt.
* **Human-in-the-Loop:** A human reviewer stays involved throughout the entire EDA process to approve implementation plans.
* **Cost & Time Efficient:** Saves API tokens and developer time through structured, modular agent execution.

---

## ⚙️ Agentic AI Pipeline Architecture

1. **Human Input & Alignment Preprocessing:** User inputs a lattice structure CT scan (e.g., octet-truss).
2. **Literature Agent:** Searches external sources (Internet, Wiki) to find relevant domain-specific analysis methods.
3. **Technical Data Scientist Agent:** Installs necessary packages and drafts implementation plan steps.
4. **Human Review:** The human expert reviews and approves/modifies the implementation plan.
5. **Coding Agent & Evaluator Loop:** 
   * The **Coding Agent** builds the analysis code and generates reports.
   * The **Evaluator** checks quality and gives feedback in an iterative loop until requirements are met.
6. **Final Report:** Generates an automated output report for the end-user.

---

## 📐 Alignment Preprocessing

* **Problem:** Original 3D meshes are often not registered (aligned) properly with the raw CT scan data.
* **Solution:** Utilizes custom registration methods (`.json` alignment files) to crop both the CT scan and mesh, creating near-perfect alignment/registration even with scanner artifacts.

---

## 🎯 Current Conclusions & Results

* Successfully created an **agentic AI pipeline** for detection and analysis of lattice structures (specifically octet-truss).
* Achieved **close-to-perfect registration** between the original mesh and CT scan data.
* Generated detailed experimental outputs (e.g., abrupt-jump robust Z-profiles, geodesic skeleton path analysis, and diameter profiles along reliable edges).

---

## ⚠️ Limitations & Future Work

- [ ] **Combine Branches:** Merge all active development branches into a master pipeline.
- [ ] **Integrate Registration:** Registration currently relies on a prior alignment `.json`; it needs full automated integration into the alignment pipeline.
- [ ] **Expand Lattice Testing:** Agentic AI has currently only been tested on $9 \times 9 \times 9$ lattice structures.
- [ ] **Pipeline Robustness:** Implement a more robust execution pipeline for consistent behavior.
- [ ] **Subagents for Verification:** Develop domain-specific subagents to verify analysis results within the final report.
- [ ] **Feature Expansion:** Implement queued "side-quest" features and extended analysis tools.

---

*Glossary:*
* **EDA:** Exploratory Data Analysis
* **MCP:** Model Context Protocol
