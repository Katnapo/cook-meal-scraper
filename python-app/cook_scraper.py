#!/usr/bin/env python3
"""
Scrape every in-stock item from cookfood.net/menu/special/microwaveable.
Extracts: name, price, serving sizes, dietary symbols, nutritional info.
Computes: protein/£, kcal/£ to find best value.
"""

import requests
import re
import json
import csv
import time
from html import unescape
from pathlib import Path

CATEGORY_URL = "https://www.cookfood.net/menu/special/microwaveable"
BASE_URL = "https://www.cookfood.net"
REQUEST_TIMEOUT = 30
DELAY = 0.3  # seconds between product-page requests (be polite)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
})


def fetch_page(url):
    resp = session.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def extract_products_from_json(html):
    """Extract the productSections JSON from the ReactDOM.hydrate call."""
    pattern = r'ReactDOM\.hydrate\(React\.createElement\(Category\.CategoryContainer,\s*(\{.*?"productSections":\s*\[.*?\]\s*,\s*"BaseUrl".*?\})\s*\)'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        raise ValueError("Could not find CategoryContainer JSON in page")

    raw_json = match.group(1)
    data = json.loads(raw_json)
    return data.get("productSections", [])


def parse_nutrition_table(html, serving_weight_g=None):
    """Extract nutritional info from a product detail page HTML table.
    Handles both 3-column (per 100g + per portion) and 2-column (per 100g only) tables.
    If only per-100g is available, scales up by serving_weight_g / 100."""
    table_pattern = re.compile(
        r'<table[^>]*>(.*?)</table>', re.DOTALL | re.IGNORECASE
    )
    tables = table_pattern.findall(html)
    nutrition = {}

    for table_html in tables:
        text = re.sub(r'<[^>]+>', ' ', table_html).lower()
        if any(kw in text for kw in ['energy', 'protein', 'carbohydrate', 'fat', 'nutrition']):
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL | re.IGNORECASE)
            for row in rows:
                cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL | re.IGNORECASE)
                if len(cells) >= 2:
                    name = re.sub(r'<[^>]+>', '', cells[0]).strip().lower()
                    name = re.sub(r'\s+', ' ', name)

                    if name in ('', 'typical values', 'nutritional information'):
                        continue
                    if name.startswith('typical values'):
                        continue

                    val_100g = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    val_portion = ""
                    if len(cells) >= 3:
                        val_portion = re.sub(r'<[^>]+>', '', cells[2]).strip()

                    nutrition[name] = {
                        "per_100g": val_100g,
                        "per_portion": val_portion,
                    }
            break

    return nutrition


def extract_numeric(val_str):
    """Extract a float from a string like '27.1' or '1,419'."""
    if not val_str:
        return None
    cleaned = val_str.replace(',', '')
    match = re.search(r'[\d.]+', cleaned)
    return float(match.group()) if match else None


def get_nut_value(nutrition, exact_key, serving_weight_g=None, fallback_key=None):
    """Get a nutrient value by matching the exact key name in nutrition dict.
    Uses per_portion if available, otherwise scales per_100g by serving weight."""
    for k, v in nutrition.items():
        if k == exact_key or k.startswith(exact_key):
            val = extract_numeric(v.get("per_portion", ""))
            if val is not None:
                return val
            # Fall back to per 100g, scaled by serving weight
            val_100g = extract_numeric(v.get("per_100g", ""))
            if val_100g is not None and serving_weight_g:
                return round(val_100g * serving_weight_g / 100, 1)
            elif val_100g is not None:
                return val_100g
    if fallback_key:
        return get_nut_value(nutrition, fallback_key, serving_weight_g)
    return None


def scrape_product_nutrition(link, serving_weight_g=None):
    """Fetch a single product page and extract nutrition."""
    url = f"{BASE_URL}/products/{link}"
    try:
        html = fetch_page(url)
        return parse_nutrition_table(html, serving_weight_g)
    except Exception as e:
        print(f"  WARNING: Could not fetch nutrition for {link}: {e}")
        return {}


def clean_price(val):
    """Convert price from JSON (e.g., 7.0000) to float."""
    return round(float(val), 2)


def get_single_serving_products(products):
    """Return products that can serve one person: Serves 1, Pot for One, or
    items with no explicit 'Serves N' label (just a weight, implying single).
    Excludes meal boxes (bundles of multiple items)."""
    result = []
    for p in products:
        title = p.get("title", "")
        if "meal box" in title.lower():
            continue
        for s in p.get("servings", []):
            serves_text = s.get("servesText", "")
            # Explicit single-serving
            if re.search(r'Serves\s+1|Pot\s+for\s+One|for\s+[Oo]ne', serves_text):
                result.append((p, s))
                break
            # No explicit "Serves" text at all (e.g. "400g") = single-serving implied
            if not re.search(r'Serves\s+\d', serves_text):
                result.append((p, s))
                break
    return result


def main():
    print(f"Fetching category page: {CATEGORY_URL}")
    html = fetch_page(CATEGORY_URL)

    print("Extracting product data from embedded JSON...")
    products = extract_products_from_json(html)
    print(f"Found {len(products)} total products")

    # Filter to single-serving
    singles = get_single_serving_products(products)
    print(f"Found {len(singles)} products with single-serving option")

    # Scrape nutrition for each
    rows = []
    for idx, (prod, serving) in enumerate(singles):
        name = prod.get("title", "Unknown")
        link = prod.get("link", "")
        product_id = prod.get("productId", prod.get("id", ""))
        price = clean_price(serving.get("price", 0))
        saving = clean_price(serving.get("saving", 0))
        effective_price = price - saving

        # Skip free/non-purchasable items
        if effective_price <= 0:
            continue
        serves_in_grams = float(serving.get("servesInGrams", 0))
        symbols = [s["title"] for s in prod.get("symbols", [])]

        print(f"[{idx+1}/{len(singles)}] {name} (£{effective_price:.2f}) ...")

        nutrition = scrape_product_nutrition(link, serves_in_grams)
        time.sleep(DELAY)

        # Extract key nutrition values using exact key matching
        energy_kj = get_nut_value(nutrition, "energy (kj)", serves_in_grams)
        energy_kcal = get_nut_value(nutrition, "energy (cal)", serves_in_grams)
        protein_g = get_nut_value(nutrition, "protein (g)", serves_in_grams)
        fat_g = get_nut_value(nutrition, "fat (g)", serves_in_grams)
        carbs_g = get_nut_value(nutrition, "carbohydrate (g)", serves_in_grams)
        sugar_g = get_nut_value(nutrition, "of which: sugars (g)", serves_in_grams)
        fibre_g = get_nut_value(nutrition, "fibre (g)", serves_in_grams)
        salt_g = get_nut_value(nutrition, "salt (g)", serves_in_grams)
        sodium_g = get_nut_value(nutrition, "sodium (g)", serves_in_grams)
        saturates_g = get_nut_value(nutrition, "of which are saturates (g)", serves_in_grams)

        # Derived metrics (use effective_price which accounts for savings)
        if effective_price > 0:
            protein_per_pound = round(protein_g / effective_price, 2) if protein_g else None
            kcal_per_pound = round(energy_kcal / effective_price, 2) if energy_kcal else None
            grams_per_pound = round(serves_in_grams / effective_price, 0) if serves_in_grams else None
        else:
            protein_per_pound = kcal_per_pound = grams_per_pound = None

        rows.append({
            "product_id": product_id,
            "name": name,
            "link": f"{BASE_URL}/products/{link}",
            "price": effective_price,
            "original_price": price,
            "saving": saving,
            "serving_size": serving.get("servesText", ""),
            "weight_g": serves_in_grams,
            "dietary_symbols": " | ".join(symbols),
            "energy_kcal": energy_kcal,
            "energy_kj": energy_kj,
            "protein_g": protein_g,
            "fat_g": fat_g,
            "saturates_g": saturates_g,
            "carbs_g": carbs_g,
            "sugar_g": sugar_g,
            "fibre_g": fibre_g,
            "salt_g": salt_g,
            "sodium_g": sodium_g,
            "protein_per_pound": protein_per_pound,
            "kcal_per_pound": kcal_per_pound,
            "grams_per_pound": grams_per_pound,
        })

    # Sort by protein/£ descending
    rows.sort(key=lambda r: r["protein_per_pound"] or 0, reverse=True)

    # Write CSV
    output_file = Path("cook_microwaveable_meals.csv")
    fieldnames = [
        "product_id", "name", "link", "price", "original_price",
        "saving", "serving_size", "weight_g", "dietary_symbols",
        "energy_kcal", "energy_kj", "protein_g", "fat_g", "saturates_g",
        "carbs_g", "sugar_g", "fibre_g", "salt_g", "sodium_g",
        "protein_per_pound", "kcal_per_pound", "grams_per_pound",
    ]
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} items to {output_file}")

    # Print top 10 by protein/£
    print("\n=== TOP 10 BY PROTEIN PER £ ===")
    print(f"{'Name':<45} {'Price':>7} {'Protein':>8} {'Prot/£':>8} {'kcal/£':>8}")
    print("-" * 80)
    for r in rows[:10]:
        print(f"{r['name']:<45} £{r['price']:>5.2f} {r['protein_g'] or '?':>7} {r['protein_per_pound'] or '?':>7} {r['kcal_per_pound'] or '?':>7}")

    # Also print top 10 by kcal/£
    print("\n=== TOP 10 BY KCAL PER £ ===")
    rows_by_kcal = sorted(rows, key=lambda r: r["kcal_per_pound"] or 0, reverse=True)
    print(f"{'Name':<45} {'Price':>7} {'kcal':>7} {'Prot/£':>8} {'kcal/£':>8}")
    print("-" * 80)
    for r in rows_by_kcal[:10]:
        print(f"{r['name']:<45} £{r['price']:>5.2f} {r['energy_kcal'] or '?':>7} {r['protein_per_pound'] or '?':>7} {r['kcal_per_pound'] or '?':>7}")


if __name__ == "__main__":
    main()
