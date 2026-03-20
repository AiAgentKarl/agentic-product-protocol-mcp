# Agentic Product Protocol MCP Server

**Klarna-style product discovery for AI shopping agents.**

Makes product catalogs machine-readable so AI agents can search, compare, and purchase products programmatically — no screen scraping, no landing pages.

## The Problem

Today's e-commerce is built for humans: landing pages, image carousels, "Add to Cart" buttons. AI shopping agents can't efficiently navigate this. They need **structured product data** — not HTML.

Klarna introduced the **Agentic Product Protocol** (December 2025) to solve exactly this: a standardized way for merchants to expose their product catalogs to AI agents. Think of it as RSS feeds, but for shopping.

## What This Server Does

This MCP server implements the core ideas of agentic product discovery:

- **Structured search results** — not web pages, but clean JSON with name, price, nutrition, ratings
- **Product comparison** — side-by-side structured comparison across multiple dimensions
- **Feed conversion** — take any product feed (JSON, CSV, Open Food Facts) and normalize it into an agent-friendly schema
- **Schema generation** — convert raw product data into the Agentic Product Protocol format
- **Availability checking** — real-time product status in a machine-readable format

Uses [Open Food Facts](https://world.openfoodfacts.org/) as a demo data source — works with any product feed.

## Installation

```bash
pip install agentic-product-protocol-mcp
```

Or with uvx (no install needed):

```bash
uvx agentic-product-protocol-mcp
```

## Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "product-protocol": {
      "command": "uvx",
      "args": ["agentic-product-protocol-mcp"]
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add product-protocol -- uvx agentic-product-protocol-mcp
```

## Tools

| Tool | Description |
|------|-------------|
| `search_products` | Search products with structured results (name, nutrition, labels, stores) |
| `get_product_details` | Get full product data by barcode/ID |
| `compare_products` | Side-by-side comparison of 2-5 products |
| `convert_feed` | Convert JSON/CSV/OFF feeds into normalized agent schema |
| `generate_product_schema` | Generate Agentic Product Protocol schema from raw data |
| `check_availability` | Check product availability and store information |

## Example Usage

**Search for products:**
> "Search for organic chocolate bars"

**Compare products:**
> "Compare these three chocolate bars: 3017620422003, 7622210449283, 7613034626844"

**Convert a feed:**
> "Convert this Open Food Facts search into agent-friendly format: https://world.openfoodfacts.org/cgi/search.pl?search_terms=protein+bar&page_size=10"

**Generate schema:**
> "Generate an agentic product schema for this product data: {name: 'Widget Pro', price: 29.99, category: 'Electronics'}"

## Why Structured Feeds > Landing Pages

| | Landing Pages | Structured Feeds |
|---|---|---|
| **Parsing** | Screen scraping, fragile | Clean JSON, reliable |
| **Speed** | Load page → parse DOM → extract | Single API call |
| **Accuracy** | Layout changes break everything | Schema-validated |
| **Comparison** | Manual extraction per site | Normalized across sources |
| **Agent UX** | Built for human eyes | Built for agent consumption |

## Data Source

This server uses **Open Food Facts** as its demo data source — a free, open, community-built database of food products from around the world. No API key required.

For production use, connect your own product feeds using the `convert_feed` tool with JSON or CSV format.

## License

MIT
