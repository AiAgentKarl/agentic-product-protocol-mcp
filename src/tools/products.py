"""
Produkt-Tools für AI Shopping Agents

Alle MCP-Tools für Produktsuche, Vergleich, Feed-Konvertierung
und Schema-Generierung nach dem Agentic Product Protocol.
"""

import json
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from src.clients.products import (
    fetch_csv_feed,
    fetch_json_feed,
    get_off_product,
    normalize_generic_product,
    search_off_products,
)


def register_tools(mcp: FastMCP):
    """Alle Produkt-Tools beim MCP-Server registrieren."""

    @mcp.tool()
    async def search_products(
        query: str,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search products with agent-friendly structured results.

        Returns normalized product data including name, categories,
        nutrition scores, labels, and availability information.
        Uses Open Food Facts as demo data source.

        Args:
            query: Search term (e.g. "organic chocolate", "vegan protein")
            category: Optional category filter (e.g. "chocolates", "beverages")
            max_price: Optional maximum price filter (not available for OFF data)
            limit: Number of results to return (default 10, max 50)
        """
        try:
            limit = min(max(1, limit), 50)
            products = await search_off_products(
                query=query,
                category=category,
                page_size=limit,
            )

            if not products:
                return {
                    "query": query,
                    "total_results": 0,
                    "products": [],
                    "message": "Keine Produkte gefunden. Versuche einen anderen Suchbegriff.",
                }

            # Kompakte Übersicht für Agent-Konsum
            results = []
            for p in products[:limit]:
                result = {
                    "id": p["id"],
                    "name": p["name"],
                    "brand": p["brand"],
                    "categories": p["categories"],
                    "quantity": p["quantity"],
                    "nutriscore": p["nutriscore"].upper() if p["nutriscore"] else None,
                    "ecoscore": p["ecoscore"].upper() if p["ecoscore"] else None,
                    "labels": p["labels"],
                    "stores": p["stores"],
                }
                results.append(result)

            return {
                "query": query,
                "category_filter": category,
                "total_results": len(results),
                "products": results,
                "data_source": "Open Food Facts (demo)",
                "note": "Prices not available in OFF — use convert_feed for priced catalogs.",
            }

        except Exception as e:
            return {"error": f"Produktsuche fehlgeschlagen: {str(e)}"}

    @mcp.tool()
    async def get_product_details(product_id: str) -> dict[str, Any]:
        """Get full structured product data by ID (barcode).

        Returns complete product information including nutrition facts,
        ingredients, allergens, certifications, and environmental scores.

        Args:
            product_id: Product barcode/EAN (e.g. "3017620422003" for Nutella)
        """
        try:
            product = await get_off_product(product_id)

            if not product:
                return {
                    "product_id": product_id,
                    "found": False,
                    "message": "Produkt nicht gefunden. Prüfe die Barcode/ID.",
                }

            return {
                "found": True,
                "product": product,
            }

        except Exception as e:
            return {"error": f"Produktdetails fehlgeschlagen: {str(e)}"}

    @mcp.tool()
    async def compare_products(product_ids: list[str]) -> dict[str, Any]:
        """Side-by-side product comparison for AI agents.

        Compares multiple products across key dimensions:
        nutrition, labels, environmental impact, and ingredients.

        Args:
            product_ids: List of product barcodes to compare (2-5 products)
        """
        if len(product_ids) < 2:
            return {"error": "Mindestens 2 Produkte zum Vergleich nötig."}
        if len(product_ids) > 5:
            return {"error": "Maximal 5 Produkte gleichzeitig vergleichen."}

        try:
            products = []
            not_found = []

            for pid in product_ids:
                product = await get_off_product(pid)
                if product:
                    products.append(product)
                else:
                    not_found.append(pid)

            if len(products) < 2:
                return {
                    "error": "Nicht genug Produkte gefunden für Vergleich.",
                    "not_found": not_found,
                }

            # Vergleichstabelle aufbauen
            comparison = {
                "products_compared": len(products),
                "not_found": not_found,
                "comparison": [],
            }

            for p in products:
                entry = {
                    "id": p["id"],
                    "name": p["name"],
                    "brand": p["brand"],
                    "quantity": p["quantity"],
                    "nutriscore": p["nutriscore"].upper() if p["nutriscore"] else "N/A",
                    "ecoscore": p["ecoscore"].upper() if p["ecoscore"] else "N/A",
                    "nova_group": p["nova_group"] or "N/A",
                    "labels": p["labels"],
                    "allergens": p["allergens"],
                    "nutrition_per_100g": p["nutrition_per_100g"],
                }
                comparison["comparison"].append(entry)

            # Zusammenfassung: Bestes Produkt pro Dimension
            summary = {}

            # Bester Nutriscore
            scored = [(p["name"], p["nutriscore"]) for p in products if p["nutriscore"]]
            if scored:
                best = min(scored, key=lambda x: x[1])
                summary["best_nutriscore"] = {"product": best[0], "score": best[1].upper()}

            # Bester Ecoscore
            eco_scored = [(p["name"], p["ecoscore"]) for p in products if p["ecoscore"]]
            if eco_scored:
                best = min(eco_scored, key=lambda x: x[1])
                summary["best_ecoscore"] = {"product": best[0], "score": best[1].upper()}

            # Wenigste Allergene
            allergen_count = [(p["name"], len(p["allergens"])) for p in products]
            best = min(allergen_count, key=lambda x: x[1])
            summary["fewest_allergens"] = {
                "product": best[0],
                "count": best[1],
            }

            # Meiste Labels/Zertifizierungen
            label_count = [(p["name"], len(p["labels"])) for p in products]
            best = max(label_count, key=lambda x: x[1])
            summary["most_certifications"] = {
                "product": best[0],
                "count": best[1],
            }

            comparison["summary"] = summary

            return comparison

        except Exception as e:
            return {"error": f"Produktvergleich fehlgeschlagen: {str(e)}"}

    @mcp.tool()
    async def convert_feed(
        feed_url: str,
        format: str = "openfoodfacts",
    ) -> dict[str, Any]:
        """Convert a product feed URL into agent-friendly normalized schema.

        Takes any product feed (JSON, CSV, Open Food Facts) and converts it
        into a standardized format that AI agents can easily consume.

        Args:
            feed_url: URL to the product feed (JSON or CSV)
            format: Feed format — "openfoodfacts" (OFF search URL),
                    "json" (generic JSON), or "csv" (CSV file)
        """
        try:
            if format == "openfoodfacts":
                # OFF-Such-URL direkt nutzen
                if "openfoodfacts.org" in feed_url:
                    # Suchbegriff aus URL extrahieren oder direkt fetchen
                    from src.clients.products import HEADERS, TIMEOUT
                    import httpx

                    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
                        # JSON-Parameter anhängen falls nicht vorhanden
                        url = feed_url
                        if "json=1" not in url:
                            separator = "&" if "?" in url else "?"
                            url = f"{url}{separator}json=1"
                        resp = await client.get(url)
                        resp.raise_for_status()
                        data = resp.json()

                    from src.clients.products import _normalize_off_product
                    raw_products = data.get("products", [])
                    products = [
                        _normalize_off_product(p)
                        for p in raw_products
                        if p.get("product_name")
                    ]
                else:
                    return {"error": "Für 'openfoodfacts' Format muss die URL von openfoodfacts.org sein."}

            elif format == "json":
                raw_products = await fetch_json_feed(feed_url)
                products = [normalize_generic_product(p) for p in raw_products]

            elif format == "csv":
                raw_products = await fetch_csv_feed(feed_url)
                products = [normalize_generic_product(p) for p in raw_products]

            else:
                return {"error": f"Unbekanntes Format: {format}. Nutze 'openfoodfacts', 'json' oder 'csv'."}

            return {
                "feed_url": feed_url,
                "format": format,
                "total_products": len(products),
                "products": products[:50],  # Max 50 pro Abruf
                "truncated": len(products) > 50,
                "schema_version": "agentic-product-protocol/0.1",
            }

        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP-Fehler beim Abrufen des Feeds: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"Feed-Konvertierung fehlgeschlagen: {str(e)}"}

    @mcp.tool()
    async def generate_product_schema(product_data: dict[str, Any]) -> dict[str, Any]:
        """Generate a standardized agent-readable product listing.

        Takes raw product data and generates a structured schema following
        the Agentic Product Protocol concept — making products machine-readable
        for AI shopping agents.

        The output schema includes:
        - Unique identification
        - Structured attributes (name, brand, category)
        - Pricing with currency
        - Availability status
        - Specifications and nutrition
        - Agent action hints (comparable, purchasable)

        Args:
            product_data: Raw product data dict with fields like
                         name, price, description, category, etc.
        """
        try:
            # Zuerst generisch normalisieren
            normalized = normalize_generic_product(product_data)

            # Agentic Product Protocol Schema generieren
            schema = {
                "@context": "https://agentic-product-protocol.org/v0.1",
                "@type": "AgentProduct",
                "protocol_version": "0.1.0",

                # Identifikation
                "identifier": {
                    "id": normalized["id"] or "unknown",
                    "source": normalized.get("source", "custom"),
                },

                # Kerndaten
                "product": {
                    "name": normalized["name"],
                    "description": normalized.get("description", ""),
                    "category": normalized.get("category", ""),
                    "image_url": normalized.get("image_url", ""),
                },

                # Preis & Verfügbarkeit
                "commerce": {
                    "price": normalized.get("price"),
                    "currency": normalized.get("currency", ""),
                    "available": normalized.get("available", True),
                    "purchase_url": product_data.get("url", product_data.get("link", "")),
                },

                # Bewertung
                "rating": {
                    "score": normalized.get("rating"),
                    "scale": "1-5" if normalized.get("rating") else None,
                },

                # Agent-Hinweise
                "agent_hints": {
                    "comparable": True,
                    "purchasable": bool(normalized.get("price")),
                    "has_nutrition_data": bool(product_data.get("nutrition_per_100g")),
                    "data_completeness": _calculate_completeness(normalized),
                },

                # Zusätzliche Rohdaten
                "extended_attributes": normalized.get("raw_fields", {}),
            }

            return {
                "schema": schema,
                "validation": {
                    "valid": bool(normalized["name"]),
                    "warnings": _get_schema_warnings(normalized),
                },
            }

        except Exception as e:
            return {"error": f"Schema-Generierung fehlgeschlagen: {str(e)}"}

    @mcp.tool()
    async def check_availability(product_id: str) -> dict[str, Any]:
        """Check real-time product availability and pricing.

        Fetches current product data and returns availability status,
        store information, and last-updated timestamp.

        Note: Open Food Facts is a community database — availability
        reflects reported store data, not real-time inventory.

        Args:
            product_id: Product barcode/EAN to check
        """
        try:
            product = await get_off_product(product_id)

            if not product:
                return {
                    "product_id": product_id,
                    "found": False,
                    "available": False,
                    "message": "Produkt nicht in der Datenbank gefunden.",
                }

            # Stores parsen (kommasepariert in OFF)
            stores_raw = product.get("stores", "")
            stores = [s.strip() for s in stores_raw.split(",") if s.strip()]

            # Verfügbarkeitsinfo zusammenbauen
            return {
                "product_id": product_id,
                "found": True,
                "name": product["name"],
                "brand": product["brand"],
                "available": bool(stores),
                "stores": stores,
                "quantity": product["quantity"],
                "countries": product["countries"],
                "data_source": "Open Food Facts (community-reported)",
                "note": (
                    "Verfügbarkeit basiert auf Community-Daten. "
                    "Für Echtzeit-Inventar einen Händler-Feed nutzen."
                ),
            }

        except Exception as e:
            return {"error": f"Verfügbarkeitsprüfung fehlgeschlagen: {str(e)}"}


def _calculate_completeness(product: dict[str, Any]) -> str:
    """Datenvollständigkeit eines Produkts bewerten."""
    fields = ["name", "description", "price", "category", "image_url", "rating"]
    filled = sum(1 for f in fields if product.get(f))
    ratio = filled / len(fields)

    if ratio >= 0.8:
        return "high"
    elif ratio >= 0.5:
        return "medium"
    else:
        return "low"


def _get_schema_warnings(product: dict[str, Any]) -> list[str]:
    """Warnungen für unvollständige Produktdaten generieren."""
    warnings = []

    if not product.get("name"):
        warnings.append("Kein Produktname — Schema ist ungültig für Agents.")
    if not product.get("price"):
        warnings.append("Kein Preis — Produkt ist nicht kaufbar für Agents.")
    if not product.get("description"):
        warnings.append("Keine Beschreibung — reduziert Agent-Verständnis.")
    if not product.get("image_url"):
        warnings.append("Kein Bild — reduziert Nutzer-Präsentation.")
    if not product.get("category"):
        warnings.append("Keine Kategorie — erschwert Agent-Filterung.")

    return warnings
