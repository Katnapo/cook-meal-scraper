#!/usr/bin/env python3
"""Single-file viewer for COOK microwaveable meals scraper data."""

import csv
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import requests
from flask import Flask, redirect, render_template_string, request, jsonify

app = Flask(__name__)

CSV_PATH = Path(__file__).parent / "cook_microwaveable_meals.csv"
SCRAPER_PATH = Path(__file__).parent / "cook_scraper.py"

CATEGORY_URL = "https://www.cookfood.net/menu/special/microwaveable"
BASE_URL = "https://www.cookfood.net"
REQUEST_TIMEOUT = 30
DELAY = 0.3

_scrape_status = {"running": False, "progress": 0, "total": 0, "message": ""}

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
    pattern = r'ReactDOM\.hydrate\(React\.createElement\(Category\.CategoryContainer,\s*(\{.*?"productSections":\s*\[.*?\]\s*,\s*"BaseUrl".*?\})\s*\)'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        raise ValueError("Could not find CategoryContainer JSON in page")
    return json.loads(match.group(1)).get("productSections", [])


def parse_nutrition_table(html):
    table_pattern = re.compile(r'<table[^>]*>(.*?)</table>', re.DOTALL | re.I)
    tables = table_pattern.findall(html)
    nutrition = {}
    for table_html in tables:
        text = re.sub(r'<[^>]+>', ' ', table_html).lower()
        if any(kw in text for kw in ['energy', 'protein', 'carbohydrate', 'fat', 'nutrition']):
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL | re.I)
            for row in rows:
                cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL | re.I)
                if len(cells) >= 2:
                    name = re.sub(r'<[^>]+>', '', cells[0]).strip().lower()
                    name = re.sub(r'\s+', ' ', name)
                    if name in ('', 'typical values', 'nutritional information'):
                        continue
                    if name.startswith('typical values'):
                        continue
                    val_100g = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    val_portion = re.sub(r'<[^>]+>', '', cells[2]).strip() if len(cells) >= 3 else ""
                    nutrition[name] = {"per_100g": val_100g, "per_portion": val_portion}
            break
    return nutrition


def extract_numeric(val_str):
    if not val_str:
        return None
    match = re.search(r'[\d.]+', val_str.replace(',', ''))
    return float(match.group()) if match else None


def get_nut_value(nutrition, exact_key, serving_weight_g=None):
    for k, v in nutrition.items():
        if k == exact_key or k.startswith(exact_key):
            val = extract_numeric(v.get("per_portion", ""))
            if val is not None:
                return val
            val_100g = extract_numeric(v.get("per_100g", ""))
            if val_100g is not None and serving_weight_g:
                return round(val_100g * serving_weight_g / 100, 1)
            elif val_100g is not None:
                return val_100g
    return None


def get_single_serving_products(products):
    result = []
    for p in products:
        title = p.get("title", "")
        if "meal box" in title.lower():
            continue
        for s in p.get("servings", []):
            serves_text = s.get("servesText", "")
            if re.search(r'Serves\s+1|Pot\s+for\s+One|for\s+[Oo]ne', serves_text):
                result.append((p, s))
                break
            if not re.search(r'Serves\s+\d', serves_text):
                result.append((p, s))
                break
    return result


def run_scraper():
    global _scrape_status
    _scrape_status = {"running": True, "progress": 0, "total": 0, "message": "Starting..."}

    try:
        html = fetch_page(CATEGORY_URL)
        products = extract_products_from_json(html)
        singles = get_single_serving_products(products)
        total = len(singles)
        _scrape_status["total"] = total

        rows = []
        for idx, (prod, serving) in enumerate(singles):
            name = prod.get("title", "Unknown")
            _scrape_status["progress"] = idx + 1
            _scrape_status["message"] = f"Scraping {name}..."

            link = prod.get("link", "")
            product_id = prod.get("productId", prod.get("id", ""))
            price = round(float(serving.get("price", 0)), 2)
            saving = round(float(serving.get("saving", 0)), 2)
            effective_price = price - saving
            if effective_price <= 0:
                continue
            serves_in_grams = float(serving.get("servesInGrams", 0))
            symbols = [s["title"] for s in prod.get("symbols", [])]

            url = f"{BASE_URL}/products/{link}"
            try:
                product_html = fetch_page(url)
                nutrition = parse_nutrition_table(product_html)
            except Exception as e:
                print(f"WARN: {link}: {e}")
                nutrition = {}

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

            if effective_price > 0:
                protein_per_pound = round(protein_g / effective_price, 2) if protein_g else None
                kcal_per_pound = round(energy_kcal / effective_price, 2) if energy_kcal else None
                grams_per_pound = round(serves_in_grams / effective_price, 0) if serves_in_grams else None
            else:
                protein_per_pound = kcal_per_pound = grams_per_pound = None

        rows.append({
            "product_id": product_id, "name": name,
            "link": f"{BASE_URL}/products/{link}",
            "price": effective_price, "original_price": price, "saving": saving,
            "serving_size": serving.get("servesText", ""), "weight_g": serves_in_grams,
            "dietary_symbols": " | ".join(symbols),
            "energy_kcal": energy_kcal, "energy_kj": energy_kj,
            "protein_g": protein_g, "fat_g": fat_g, "saturates_g": saturates_g,
            "carbs_g": carbs_g, "sugar_g": sugar_g, "fibre_g": fibre_g,
            "salt_g": salt_g, "sodium_g": sodium_g,
            "protein_per_pound": protein_per_pound, "kcal_per_pound": kcal_per_pound,
            "grams_per_pound": grams_per_pound,
        })
            time.sleep(DELAY)

        rows.sort(key=lambda r: r["protein_per_pound"] or 0, reverse=True)

        fieldnames = [
            "product_id", "name", "link", "price", "original_price",
            "saving", "serving_size", "weight_g", "dietary_symbols",
            "energy_kcal", "energy_kj", "protein_g", "fat_g", "saturates_g",
            "carbs_g", "sugar_g", "fibre_g", "salt_g", "sodium_g",
            "protein_per_pound", "kcal_per_pound", "grams_per_pound",
        ]
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        _scrape_status["message"] = f"Done - {len(rows)} items saved"
        _scrape_status["running"] = False
        return len(rows)

    except Exception as e:
        _scrape_status["message"] = f"Error: {e}"
        _scrape_status["running"] = False
        raise


def load_csv():
    if not CSV_PATH.exists():
        return []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --- Routes ---

@app.route("/")
def index():
    rows = load_csv()
    return render_template_string(HTML_TEMPLATE, rows=rows, status=_scrape_status)


@app.route("/scrape", methods=["POST"])
def scrape():
    global _scrape_status
    if _scrape_status.get("running"):
        return jsonify({"error": "Scraper already running"}), 409

    _scrape_status = {"running": True, "progress": 0, "total": 0, "message": "Starting..."}

    def _run():
        try:
            run_scraper()
        except Exception as e:
            _scrape_status["message"] = f"Error: {e}"
            _scrape_status["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/status")
def status():
    return jsonify(_scrape_status)


# --- HTML Template ---

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>COOK Microwaveable Meals</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #222; }
header { background: #1a6b4b; color: #fff; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
header h1 { font-size: 1.3rem; font-weight: 600; }
.btn { padding: 8px 18px; border: none; border-radius: 6px; font-size: 0.9rem; cursor: pointer; font-weight: 500; transition: background 0.15s; }
.btn-primary { background: #fff; color: #1a6b4b; }
.btn-primary:hover { background: #e8f5e9; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
#status-bar { padding: 10px 24px; background: #e8f5e9; border-bottom: 1px solid #c8e6c9; font-size: 0.85rem; display: none; align-items: center; gap: 8px; }
#status-bar.visible { display: flex; }
.spinner { width: 18px; height: 18px; border: 3px solid #c8e6c9; border-top-color: #1a6b4b; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.wrapper { max-width: 100%; overflow-x: auto; padding: 16px; }
.info { padding: 0 16px 8px; font-size: 0.85rem; color: #666; }
table { width: 100%; border-collapse: collapse; font-size: 0.82rem; white-space: nowrap; }
thead { position: sticky; top: 0; z-index: 1; }
th { background: #1a6b4b; color: #fff; padding: 10px 12px; text-align: left; cursor: pointer; user-select: none; font-weight: 500; }
th:hover { background: #1e7d57; }
th .sort-icon { margin-left: 4px; opacity: 0.5; font-size: 0.7rem; }
th.sorted-asc .sort-icon, th.sorted-desc .sort-icon { opacity: 1; }
td { padding: 8px 12px; border-bottom: 1px solid #e0e0e0; }
tr:hover td { background: #f0faf4; }
td a { color: #1a6b4b; text-decoration: none; }
td a:hover { text-decoration: underline; }
.col-num { text-align: right; }
.col-symbols { font-size: 0.75rem; color: #555; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
footer { padding: 20px 24px; text-align: center; font-size: 0.78rem; color: #999; }
.metric-hi { color: #1a6b4b; font-weight: 600; }
.metric-md { color: #33691e; }
.metric-lo { color: #888; }
.saving-badge { color: #e65100; font-size: 0.75rem; font-weight: 500; }
</style>
</head>
<body>
<header>
  <h1>COOK Microwaveable Meals</h1>
  <button class="btn btn-primary" id="btn-scrape" onclick="startScrape()">Run Scraper</button>
</header>
<div id="status-bar"><div class="spinner"></div><span id="status-msg"></span></div>
<div class="info" id="row-count">{{ rows|length }} items loaded</div>
<div class="wrapper">
  <table id="data-table">
    <thead>
      <tr>
        <th data-col="name" data-type="str">Dish</th>
        <th data-col="original_price" data-type="num" class="col-num">Price</th>
        <th data-col="weight_g" data-type="num" class="col-num">Weight</th>
        <th data-col="energy_kcal" data-type="num" class="col-num">kcal</th>
        <th data-col="protein_g" data-type="num" class="col-num">Protein</th>
        <th data-col="fat_g" data-type="num" class="col-num">Fat</th>
        <th data-col="carbs_g" data-type="num" class="col-num">Carbs</th>
        <th data-col="fibre_g" data-type="num" class="col-num">Fibre</th>
        <th data-col="salt_g" data-type="num" class="col-num">Salt</th>
        <th data-col="protein_per_pound" data-type="num" class="col-num" data-default-sort="desc">Prot/£</th>
        <th data-col="kcal_per_pound" data-type="num" class="col-num">kcal/£</th>
        <th data-col="grams_per_pound" data-type="num" class="col-num">g/£</th>
        <th data-col="dietary_symbols" data-type="str">Dietary</th>
      </tr>
    </thead>
    <tbody id="table-body">
      {% for r in rows %}
      <tr>
        <td><a href="{{ r.link }}" target="_blank">{{ r.name }}</a></td>
        <td class="col-num">&pound;{{ "%.2f"|format(r.original_price|float) }}{% if r.saving|float > 0 %} <span class="saving-badge">save &pound;{{ "%.2f"|format(r.saving|float) }}</span>{% endif %}</td>
        <td class="col-num">{{ r.weight_g }}</td>
        <td class="col-num">{{ r.energy_kcal or '--' }}</td>
        <td class="col-num">{{ r.protein_g or '--' }}</td>
        <td class="col-num">{{ r.fat_g or '--' }}</td>
        <td class="col-num">{{ r.carbs_g or '--' }}</td>
        <td class="col-num">{{ r.fibre_g or '--' }}</td>
        <td class="col-num">{{ r.salt_g or '--' }}</td>
        <td class="col-num">{{ r.protein_per_pound or '--' }}</td>
        <td class="col-num">{{ r.kcal_per_pound or '--' }}</td>
        <td class="col-num">{{ r.grams_per_pound or '--' }}</td>
        <td class="col-symbols">{{ r.dietary_symbols }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
<footer>COOK Microwaveable Meals Scraper &mdash; data from cookfood.net</footer>

<script>
const ALL_DATA = {{ rows | tojson }};

let sortCol = 'protein_per_pound';
let sortDir = 'desc';

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function renderTable(rows) {
  const tbody = document.getElementById('table-body');
  tbody.innerHTML = rows.map(r => {
    const op = parseFloat(r.original_price) || 0;
    const sv = parseFloat(r.saving) || 0;
    const savingHtml = sv > 0 ? ` <span class="saving-badge">save &pound;${sv.toFixed(2)}</span>` : '';
    return `
    <tr>
      <td><a href="${esc(r.link)}" target="_blank">${esc(r.name)}</a></td>
      <td class="col-num">&pound;${op.toFixed(2)}${savingHtml}</td>
      <td class="col-num">${r.weight_g}</td>
      <td class="col-num">${r.energy_kcal || '--'}</td>
      <td class="col-num">${r.protein_g || '--'}</td>
      <td class="col-num">${r.fat_g || '--'}</td>
      <td class="col-num">${r.carbs_g || '--'}</td>
      <td class="col-num">${r.fibre_g || '--'}</td>
      <td class="col-num">${r.salt_g || '--'}</td>
      <td class="col-num">${r.protein_per_pound || '--'}</td>
      <td class="col-num">${r.kcal_per_pound || '--'}</td>
      <td class="col-num">${r.grams_per_pound || '--'}</td>
      <td class="col-symbols">${esc(r.dietary_symbols)}</td>
    </tr>`;
  }).join('');
}

function sort(col, dir) {
  const th = document.querySelector(`th[data-col="${col}"]`);
  const type = th ? th.dataset.type : 'str';
  const sorted = [...ALL_DATA].sort((a, b) => {
    let va = type === 'num' ? (parseFloat(a[col]) || 0) : (String(a[col] || '').toLowerCase());
    let vb = type === 'num' ? (parseFloat(b[col]) || 0) : (String(b[col] || '').toLowerCase());
    if (va < vb) return dir === 'asc' ? -1 : 1;
    if (va > vb) return dir === 'asc' ? 1 : -1;
    return 0;
  });
  renderTable(sorted);
  document.querySelectorAll('th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
  const targetTh = document.querySelector(`th[data-col="${col}"]`);
  if (targetTh) targetTh.classList.add(dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
  document.getElementById('row-count').textContent = `${sorted.length} items`;
}

document.querySelectorAll('th').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.col;
    if (sortCol === col) {
      sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      sortCol = col;
      sortDir = th.dataset.defaultSort === 'desc' ? 'desc' : 'asc';
    }
    sort(sortCol, sortDir);
  });
  if (th.dataset.col) {
    th.innerHTML += ' <span class="sort-icon">&#9650;&#9660;</span>';
  }
});

// Initial sort
sort('protein_per_pound', 'desc');

// Scraper controls
let pollTimer = null;

function startScrape() {
  const btn = document.getElementById('btn-scrape');
  const bar = document.getElementById('status-bar');
  btn.disabled = true;
  btn.textContent = 'Running...';
  bar.classList.add('visible');
  document.getElementById('status-msg').textContent = 'Starting scraper...';

  fetch('/scrape', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        document.getElementById('status-msg').textContent = 'Error: ' + data.error;
        resetBtn();
        return;
      }
      pollStatus();
    })
    .catch(e => {
      document.getElementById('status-msg').textContent = 'Request failed: ' + e;
      resetBtn();
    });
}

function pollStatus() {
  fetch('/status')
    .then(r => r.json())
    .then(s => {
      const msg = s.progress > 0 ? `${s.message} (${s.progress}/${s.total})` : s.message;
      document.getElementById('status-msg').textContent = msg;
      if (s.running) {
        pollTimer = setTimeout(pollStatus, 500);
      } else {
        resetBtn();
        document.getElementById('status-bar').classList.remove('visible');
        location.reload();
      }
    })
    .catch(() => {
      pollTimer = setTimeout(pollStatus, 1000);
    });
}

function resetBtn() {
  const btn = document.getElementById('btn-scrape');
  btn.disabled = false;
  btn.textContent = 'Run Scraper';
  if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
}
</script>
</body>
</html>"""


def main():
    parser_port = 8080
    print(f"Starting COOK Meal Viewer at http://localhost:{parser_port}")
    print(f"CSV: {CSV_PATH}")
    webbrowser.open(f"http://localhost:{parser_port}")
    app.run(host="127.0.0.1", port=parser_port, debug=False)


if __name__ == "__main__":
    main()
