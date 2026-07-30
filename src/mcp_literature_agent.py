"""
mcp_server.py — FastMCP server exposing the Literature Agent's tools:

  1. literature_search   — scoped search restricted to trusted, citable sources
  2. update_wiki_entry   — atomic, targeted update to LLM-Wiki/{lattice_type}.md
  3. validate_output     — schema validation for the agent's handoff payload

Run:
    pip install fastmcp requests pydantic --break-system-packages
    python mcp_server.py
"""

import re
import datetime as dt
from pathlib import Path
from typing import Optional, Literal

import requests
from pydantic import BaseModel, Field, ValidationError
from fastmcp import FastMCP

mcp = FastMCP("literature-agent-tools")

# Trusted, citable sources only. Deliberately excludes general web search —
# this is what keeps the permanent LLM-Wiki cache from absorbing an
# unvetted blog post that every future run for this lattice type will trust.
SOURCES = {
    "semantic_scholar": "https://api.semanticscholar.org/graph/v1/paper/search",
    "crossref": "https://api.crossref.org/works",
}


# --------------------------------------------------------------------------
# Tool 1: literature_search
# --------------------------------------------------------------------------

@mcp.tool()
def literature_search(
    query: str,
    lattice_type: Optional[str] = None,
    max_results: int = 5,
) -> dict:
    """
    Search only vetted, citable sources (Semantic Scholar + Crossref) for
    analysis methods relevant to a lattice type or specific request.
    Returns paper metadata (title/abstract/DOI), not full text — the agent
    should synthesize a method description from this, not quote verbatim.
    """
    results = []

    try:
        resp = requests.get(
            SOURCES["semantic_scholar"],
            params={
                "query": query,
                "limit": max_results,
                "fields": "title,abstract,year,externalIds,venue",
            },
            timeout=10,
        )
        resp.raise_for_status()
        for paper in resp.json().get("data", []):
            results.append({
                "source": "semantic_scholar",
                "title": paper.get("title"),
                "year": paper.get("year"),
                "venue": paper.get("venue"),
                "abstract": paper.get("abstract"),
                "doi": (paper.get("externalIds") or {}).get("DOI"),
            })
    except requests.RequestException as e:
        results.append({"source": "semantic_scholar", "error": str(e)})

    try:
        resp = requests.get(
            SOURCES["crossref"],
            params={"query": query, "rows": max_results},
            timeout=10,
        )
        resp.raise_for_status()
        for item in resp.json().get("message", {}).get("items", []):
            title_list = item.get("title") or [None]
            venue_list = item.get("container-title") or [None]
            date_parts = item.get("issued", {}).get("date-parts", [[None]])
            results.append({
                "source": "crossref",
                "title": title_list[0],
                "year": date_parts[0][0] if date_parts else None,
                "venue": venue_list[0],
                "doi": item.get("DOI"),
            })
    except requests.RequestException as e:
        results.append({"source": "crossref", "error": str(e)})

    return {
        "query": query,
        "lattice_type": lattice_type,
        "retrieved_at": dt.date.today().isoformat(),
        "results": results,
    }


# --------------------------------------------------------------------------
# Tool 2: update_wiki_entry
# --------------------------------------------------------------------------

def _entry_pattern(method_name: str) -> re.Pattern:
    return re.compile(
        rf"^## {re.escape(method_name)}\n(.*?)(?=^## |\Z)",
        re.DOTALL | re.MULTILINE,
    )


@mcp.tool()
def update_wiki_entry(
    lattice_type: str,
    method_name: str,
    description: str,
    source_doi: Optional[str] = None,
    wiki_dir: str = "LLM-Wiki",
) -> dict:
    """
    Add or update ONE method entry inside LLM-Wiki/{lattice_type}.md,
    leaving every other entry in the file untouched. Prevents the agent
    from hand-editing the whole markdown file and clobbering unrelated
    cached methods for the same lattice type.
    """
    wiki_path = Path(wiki_dir) / f"{lattice_type}.md"
    wiki_path.parent.mkdir(parents=True, exist_ok=True)

    today = dt.date.today().isoformat()
    new_entry = (
        f"## {method_name}\n"
        f"- last_updated: {today}\n"
        f"- source_doi: {source_doi or 'n/a'}\n\n"
        f"{description.strip()}\n\n"
    )

    if not wiki_path.exists():
        wiki_path.write_text(f"# {lattice_type}\n\n{new_entry}")
        return {"status": "created", "path": str(wiki_path), "method": method_name}

    content = wiki_path.read_text()
    pattern = _entry_pattern(method_name)

    if pattern.search(content):
        content = pattern.sub(new_entry, content, count=1)
        action = "updated"
    else:
        content = content.rstrip() + "\n\n" + new_entry
        action = "appended"

    wiki_path.write_text(content)
    return {
        "status": action,
        "path": str(wiki_path),
        "method": method_name,
        "last_updated": today,
    }


# --------------------------------------------------------------------------
# Tool 3: validate_output
# --------------------------------------------------------------------------

class MethodEntry(BaseModel):
    name: str
    description: str
    wiki_last_updated: Optional[str] = None


class LiteratureAgentOutput(BaseModel):
    lattice_type: str
    source: Literal["cache", "fresh_search"]
    methods: list[MethodEntry] = Field(min_length=1)


SCHEMAS = {
    "literature_agent_output": LiteratureAgentOutput,
}


@mcp.tool()
def validate_output(payload: dict, schema_name: str = "literature_agent_output") -> dict:
    """
    Validate a handoff payload against its expected schema before passing it
    downstream to TDS-CTS. Fails fast on a malformed field instead of letting
    it silently propagate into the dependency-check / planning stage.
    """
    schema = SCHEMAS.get(schema_name)
    if schema is None:
        return {"valid": False, "error": f"Unknown schema '{schema_name}'"}

    try:
        schema(**payload)
        return {"valid": True}
    except ValidationError as e:
        return {"valid": False, "errors": e.errors()}


if __name__ == "__main__":
    mcp.run()