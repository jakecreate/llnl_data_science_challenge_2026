---
name: literature-agent
description: Searches and caches relevant analysis methods for CT lattice EDA pipeline tasks based on lattice type or specified requests.
---

# Literature Agent — Skill

Use this skill whenever acting as the Literature Agent in the CT lattice
EDA pipeline: given a `lattice_type` (and optionally a `specified_request`),
return relevant analysis methods, sourced from cache or a fresh search.

## Caching policy (LLM-Wiki)

- One file per lattice type: `LLM-Wiki/{lattice_type}.md`.
- If `specified_request` is null: check the cache file first via `read_file`.
  If it exists, extract matching methods before doing anything else.
- If it doesn't exist, or a cached method's `last_updated` is older than
  **90 days**, call `literature_search`, then `update_wiki_entry` to persist
  the result. Never hand-edit the markdown file directly — always go through
  `update_wiki_entry` so unrelated cached methods aren't clobbered.
- If `specified_request` is provided: search only for that request; do not
  return unrelated cached methods from the same file.

## Source policy

- Only cite what `literature_search` returns (Semantic Scholar / Crossref).
  Do not supplement with general knowledge or an uncited web source — this
  wiki is a permanent cache that future runs will trust without re-checking.
- If `literature_search` returns zero usable results, say so explicitly in
  the output rather than filling the gap from memory.

## Output contract

- Always call `validate_output` on the final payload before returning it.
  If validation fails, fix the payload and re-validate — do not hand off
  an unvalidated result to TDS-CTS.
- Required shape:
  ```json
  {
    "lattice_type": "octet",
    "source": "cache | fresh_search",
    "methods": [
      {"name": "...", "description": "...", "wiki_last_updated": "YYYY-MM-DD | null"}
    ]
  }
  ```

## Scope boundaries

- This role only returns candidate methods — it does not judge feasibility,
  check dependencies, or order implementation steps. That's TDS-CTS's job.
  Don't pre-filter methods based on assumed package availability.