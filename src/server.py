"""
Agentic Product Protocol MCP Server

Macht Produktkataloge maschinenlesbar für AI Shopping Agents.
Inspiriert von Klarnas Agentic Product Protocol — strukturierte
Produktdaten statt Landing Pages für Agent-Commerce.
"""

from mcp.server.fastmcp import FastMCP

# Server-Instanz
mcp = FastMCP(
    "agentic-product-protocol",
    instructions=(
        "Product discovery for AI shopping agents. "
        "Search products, compare items, convert feeds to agent-friendly formats, "
        "and generate standardized product schemas following the Agentic Product Protocol. "
        "Uses Open Food Facts as demo data source — works with any product feed."
    ),
)

# Tools registrieren
from src.tools.products import register_tools

register_tools(mcp)


def main():
    """Server starten über stdio-Transport."""
    mcp.run()


if __name__ == "__main__":
    main()
