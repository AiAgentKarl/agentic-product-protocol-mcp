"""
Produkt-API-Client

Async HTTP-Client für Produktdaten aus verschiedenen Quellen.
Primäre Demo-Quelle: Open Food Facts API.
Unterstützt auch generische JSON/CSV-Feeds.
"""

import csv
import io
import json
from typing import Any, Optional

import httpx

# Open Food Facts API Basis-URL
OFF_BASE_URL = "https://world.openfoodfacts.org"

# Timeout für HTTP-Requests
TIMEOUT = httpx.Timeout(15.0, connect=10.0)

# User-Agent (Open Food Facts erfordert das)
HEADERS = {
    "User-Agent": "AgenticProductProtocol/0.1.0 (AI Shopping Agent MCP Server)",
}


async def search_off_products(
    query: str,
    category: Optional[str] = None,
    page_size: int = 10,
) -> list[dict[str, Any]]:
    """
    Produkte in Open Food Facts suchen.

    Args:
        query: Suchbegriff (z.B. "chocolate", "organic milk")
        category: Optional Kategorie-Filter
        page_size: Anzahl Ergebnisse (max 100)

    Returns:
        Liste normalisierter Produktdaten
    """
    params: dict[str, Any] = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": min(page_size, 100),
        "fields": (
            "code,product_name,brands,categories_tags,image_url,"
            "nutriscore_grade,ecoscore_grade,nova_group,"
            "nutriments,quantity,stores,countries_tags,"
            "ingredients_text,labels_tags,allergens_tags"
        ),
    }

    if category:
        params["tagtype_0"] = "categories"
        params["tag_contains_0"] = "contains"
        params["tag_0"] = category

    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        resp = await client.get(f"{OFF_BASE_URL}/cgi/search.pl", params=params)
        resp.raise_for_status()
        data = resp.json()

    products = data.get("products", [])
    return [_normalize_off_product(p) for p in products if p.get("product_name")]


async def get_off_product(barcode: str) -> Optional[dict[str, Any]]:
    """
    Einzelnes Produkt über Barcode/ID abrufen.

    Args:
        barcode: EAN/UPC Barcode oder Open Food Facts Code

    Returns:
        Normalisiertes Produktdaten-Dict oder None
    """
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        resp = await client.get(f"{OFF_BASE_URL}/api/v2/product/{barcode}")
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != 1:
        return None

    product = data.get("product", {})
    return _normalize_off_product(product)


async def fetch_json_feed(feed_url: str) -> list[dict[str, Any]]:
    """
    Generischen JSON-Produktfeed abrufen und parsen.

    Unterstützt:
    - Array von Produkten: [{"name": ...}, ...]
    - Objekt mit products-Key: {"products": [...]}

    Args:
        feed_url: URL zum JSON-Feed

    Returns:
        Liste von Produkt-Dicts (roh, nicht normalisiert)
    """
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        resp = await client.get(feed_url)
        resp.raise_for_status()
        data = resp.json()

    # Verschiedene JSON-Strukturen erkennen
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        # Häufige Keys für Produkt-Arrays
        for key in ["products", "items", "results", "data", "entries"]:
            if key in data and isinstance(data[key], list):
                return data[key]
        # Einzelnes Produkt
        return [data]

    return []


async def fetch_csv_feed(feed_url: str) -> list[dict[str, Any]]:
    """
    CSV-Produktfeed abrufen und parsen.

    Args:
        feed_url: URL zum CSV-Feed

    Returns:
        Liste von Produkt-Dicts (Spaltenname → Wert)
    """
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        resp = await client.get(feed_url)
        resp.raise_for_status()
        text = resp.text

    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _normalize_off_product(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Open Food Facts Produkt in einheitliches Schema umwandeln.

    Mappt die OFF-Felder auf unser Agent-friendly Format.
    """
    nutriments = raw.get("nutriments", {})

    # Nährwerte extrahieren (pro 100g)
    nutrition = {}
    for key in ["energy-kcal_100g", "fat_100g", "sugars_100g",
                 "proteins_100g", "salt_100g", "fiber_100g"]:
        val = nutriments.get(key)
        if val is not None:
            clean_key = key.replace("_100g", "").replace("-", "_")
            nutrition[clean_key] = val

    # Kategorien bereinigen (en:chocolate → chocolate)
    categories = [
        c.split(":")[-1].replace("-", " ")
        for c in raw.get("categories_tags", [])
    ]

    # Labels (Bio, Vegan, etc.)
    labels = [
        l.split(":")[-1].replace("-", " ")
        for l in raw.get("labels_tags", [])
    ]

    # Allergene
    allergens = [
        a.split(":")[-1].replace("-", " ")
        for a in raw.get("allergens_tags", [])
    ]

    return {
        "id": raw.get("code", ""),
        "name": raw.get("product_name", "Unknown"),
        "brand": raw.get("brands", ""),
        "categories": categories[:5],
        "image_url": raw.get("image_url", ""),
        "quantity": raw.get("quantity", ""),
        "stores": raw.get("stores", ""),
        "nutrition_per_100g": nutrition,
        "nutriscore": raw.get("nutriscore_grade", ""),
        "ecoscore": raw.get("ecoscore_grade", ""),
        "nova_group": raw.get("nova_group"),
        "labels": labels[:10],
        "allergens": allergens,
        "ingredients": raw.get("ingredients_text", ""),
        "countries": [
            c.split(":")[-1]
            for c in raw.get("countries_tags", [])
        ][:5],
        "source": "openfoodfacts",
    }


def normalize_generic_product(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Generisches Produkt-Dict in unser Schema normalisieren.

    Versucht gängige Feldnamen zu erkennen und zu mappen.
    """
    # Name finden
    name = ""
    for key in ["name", "product_name", "title", "item_name", "productName"]:
        if key in raw and raw[key]:
            name = str(raw[key])
            break

    # Preis finden
    price = None
    for key in ["price", "current_price", "sale_price", "unitPrice", "cost"]:
        if key in raw:
            try:
                price = float(raw[key])
            except (ValueError, TypeError):
                pass
            break

    # Währung finden
    currency = ""
    for key in ["currency", "price_currency", "currencyCode"]:
        if key in raw and raw[key]:
            currency = str(raw[key])
            break

    # ID finden
    product_id = ""
    for key in ["id", "product_id", "sku", "barcode", "code", "item_id", "asin"]:
        if key in raw and raw[key]:
            product_id = str(raw[key])
            break

    # Beschreibung
    description = ""
    for key in ["description", "short_description", "summary", "desc"]:
        if key in raw and raw[key]:
            description = str(raw[key])
            break

    # Kategorie
    category = ""
    for key in ["category", "categories", "product_type", "type"]:
        if key in raw and raw[key]:
            val = raw[key]
            if isinstance(val, list):
                category = ", ".join(str(v) for v in val[:5])
            else:
                category = str(val)
            break

    # Bild
    image = ""
    for key in ["image", "image_url", "thumbnail", "picture", "img", "imageUrl"]:
        if key in raw and raw[key]:
            image = str(raw[key])
            break

    # Verfügbarkeit
    available = True
    for key in ["available", "in_stock", "availability", "inStock"]:
        if key in raw:
            val = raw[key]
            if isinstance(val, bool):
                available = val
            elif isinstance(val, str):
                available = val.lower() in ("true", "yes", "in stock", "available", "1")
            break

    # Rating
    rating = None
    for key in ["rating", "average_rating", "score", "stars"]:
        if key in raw:
            try:
                rating = float(raw[key])
            except (ValueError, TypeError):
                pass
            break

    return {
        "id": product_id,
        "name": name,
        "description": description,
        "price": price,
        "currency": currency,
        "category": category,
        "image_url": image,
        "available": available,
        "rating": rating,
        "source": "feed",
        "raw_fields": {
            k: v for k, v in raw.items()
            if k not in ("id", "name", "price", "description", "image")
        },
    }
