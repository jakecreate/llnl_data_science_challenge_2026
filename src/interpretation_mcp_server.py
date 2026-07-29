from fastmcp import FastMCP

from interpretation_tools import load_interpretation_batch, write_characterization_outputs


# INTERPRETATION-ONLY MCP SERVER:
# This file is intentionally separate from mcp_server.py so the interpretation
# agent can work without changing the team's segmentation/visualization server.
mcp = FastMCP("CT Interpretation")


@mcp.tool()
def load_batch(run_id: str, offset: int = 0, limit: int = 20) -> dict:
    """Load a page of flagged struts for interpretation."""
    return load_interpretation_batch(run_id, offset, limit)


@mcp.tool()
def write_outputs(run_id: str, rows: list[dict]) -> dict:
    """Validate and write characterization.csv + characterization.md."""
    return write_characterization_outputs(run_id, rows)


if __name__ == "__main__":
    # CODEX MCP STARTUP FIX:
    # FastMCP's banner checks a user-level update cache that Codex's sandbox
    # cannot read. Disabling the banner lets the stdio MCP connection start.
    mcp.run(show_banner=False)
