#!/usr/bin/env python3
"""Generate a static index.html from the CSV data."""

import csv
import json
from pathlib import Path

CSV_PATH = Path(__file__).parent / "python-app" / "cook_microwaveable_meals.csv"
SCRAPER_JS_PATH = Path(__file__).parent / "scraper.js"
OUT_PATH = Path(__file__).parent / "index.html"

with open(CSV_PATH, "r") as f:
    rows = list(csv.DictReader(f))

with open(SCRAPER_JS_PATH, "r", encoding="utf-8") as f:
    scraper_js = f.read()

data_json = json.dumps(rows, indent=None)
scraper_js_json = json.dumps(scraper_js)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>COOK Microwaveable Meals — Best Protein &amp; Calorie Value</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;color:#222}}
header{{background:#1a6b4b;color:#fff;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px}}
header h1{{font-size:1.2rem;font-weight:600}}
header p{{font-size:.78rem;opacity:.85}}
.toolbar{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 16px;background:#fff;border-bottom:1px solid #e0e0e0}}
.toolbar input{{padding:6px 12px;border:1px solid #ccc;border-radius:6px;font-size:.82rem;min-width:200px}}
.toolbar select{{padding:6px 10px;border:1px solid #ccc;border-radius:6px;font-size:.82rem}}
.toolbar .count{{font-size:.8rem;color:#666;margin-left:auto}}
.wrapper{{max-width:100%;overflow-x:auto;padding:8px 0}}
table{{width:100%;border-collapse:collapse;font-size:.78rem;white-space:nowrap}}
thead{{position:sticky;top:0;z-index:2}}
th{{background:#1a6b4b;color:#fff;padding:8px 10px;text-align:left;cursor:pointer;user-select:none;font-weight:500;position:relative}}
th:hover{{background:#1e7d57}}
th .si{{margin-left:3px;opacity:.4;font-size:.65rem}}
th.sa .si,th.sd .si{{opacity:1}}
td{{padding:7px 10px;border-bottom:1px solid #e8e8e8}}
tr:hover td{{background:#f0faf4}}
td a{{color:#1a6b4b;text-decoration:none}}
td a:hover{{text-decoration:underline}}
.r{{text-align:right}}
.sym{{font-size:.7rem;color:#777;max-width:160px;overflow:hidden;text-overflow:ellipsis}}
.save-badge{{color:#e65100;font-size:.72rem;font-weight:500;margin-left:4px}}
.hl{{background:#e8f5e9}}
footer{{padding:16px 20px;text-align:center;font-size:.72rem;color:#999}}
footer a{{color:#1a6b4b}}
.note{{background:#fff3e0;border:1px solid #ffe0b2;border-radius:6px;padding:10px 16px;margin:12px 16px;font-size:.78rem;color:#e65100}}
.note code{{background:#fbe9e7;padding:1px 5px;border-radius:3px;font-size:.75rem}}
.run-box{{background:#fff;border:1px solid #ddd;border-radius:6px;padding:14px 16px;margin:12px 16px;font-size:.78rem}}
.run-box h3{{font-size:.85rem;margin-bottom:6px;color:#1a6b4b}}
.run-box .cmd{{background:#1e1e1e;color:#d4d4d4;padding:10px 14px;border-radius:4px;font-family:Consolas,'Courier New',monospace;font-size:.78rem;display:flex;align-items:center;gap:10px;overflow-x:auto}}
.run-box .cmd code{{white-space:pre;user-select:all}}
.run-box .copy-btn{{padding:4px 12px;background:#1a6b4b;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:.75rem;white-space:nowrap;flex-shrink:0}}
.run-box .copy-btn:hover{{background:#1e7d57}}
.run-box .copy-btn.copied{{background:#4caf50}}
.run-box ul{{margin:6px 0 0 18px;font-size:.75rem;color:#666;line-height:1.5}}
th .filter-icon{{position:absolute;right:4px;top:50%;transform:translateY(-50%);opacity:.3;cursor:pointer;font-size:.7rem}}
th .filter-icon:hover{{opacity:.8}}
.no-results{{text-align:center;padding:40px;color:#999;font-size:.9rem}}
.tab-group{{display:flex;gap:2px}}
.tab{{padding:6px 14px;border:1px solid #ccc;border-radius:6px 6px 0 0;background:#f0f0f0;cursor:pointer;font-size:.8rem;border-bottom:none;margin-bottom:-1px}}
.tab.active{{background:#fff;font-weight:600;border-color:#ccc #ccc #fff}}
</style>
</head>
<body>
<header>
  <div><h1>COOK Microwaveable Meals</h1><p>Best protein &amp; calorie value per pound</p></div>
  <a href="https://github.com/Katnapo/cook-meal-scraper" style="color:#fff;font-size:.78rem;opacity:.8">GitHub</a>
</header>
<div class="note">
  <strong>Static snapshot</strong> &mdash; data scraped from cookfood.net. Prices include listed discounts. Not affiliated with COOK.
</div>
<div class="run-box">
  <h3>Scrape fresh data (paste into browser console)</h3>
  <p style="font-size:.75rem;color:#666;margin-bottom:8px">
    1. Open <a href="https://www.cookfood.net/menu/special/microwaveable" target="_blank">cookfood.net/menu/special/microwaveable</a><br>
    2. Press <strong>F12</strong> &rarr; Console tab<br>
    3. Paste the script below &rarr; Enter<br>
    4. Wait ~45 seconds for results
  </p>
  <div class="cmd">
    <code id="browser-snippet" style="white-space:pre-wrap;max-height:120px;overflow-y:auto">Loading snippet...</code>
    <button class="copy-btn" onclick="copyCmd(this)" id="browser-copy-btn">Copy</button>
  </div>
  <p style="font-size:.7rem;color:#999;margin-top:6px">Runs entirely in your browser with no install. Rate-limited (300ms between requests). Use at your own risk.</p>
</div>
<div class="toolbar">
  <input type="text" id="search" placeholder="Filter dishes..." oninput="doFilter()">
  <select id="metric-focus" onchange="doFilter()">
    <option value="all">All items</option>
    <option value="hi-protein">High protein (&ge;25g)</option>
    <option value="lo-cal">Low calorie (&lt;400kcal)</option>
    <option value="veggie">Vegetarian/Vegan</option>
    <option value="gluten-free">Gluten Free</option>
    <option value="dairy-free">Dairy Free</option>
  </select>
  <span class="count" id="row-count"></span>
</div>
<div class="wrapper">
  <table id="tbl">
    <thead>
      <tr>
        <th data-col="name" data-type="str">Dish <span class="si">&#9650;&#9660;</span></th>
        <th data-col="original_price" data-type="num" class="r">Price <span class="si">&#9650;&#9660;</span></th>
        <th data-col="weight_g" data-type="num" class="r">g <span class="si">&#9650;&#9660;</span></th>
        <th data-col="energy_kcal" data-type="num" class="r">kcal <span class="si">&#9650;&#9660;</span></th>
        <th data-col="protein_g" data-type="num" class="r">Prot <span class="si">&#9650;&#9660;</span></th>
        <th data-col="fat_g" data-type="num" class="r">Fat <span class="si">&#9650;&#9660;</span></th>
        <th data-col="carbs_g" data-type="num" class="r">Carbs <span class="si">&#9650;&#9660;</span></th>
        <th data-col="fibre_g" data-type="num" class="r">Fibre <span class="si">&#9650;&#9660;</span></th>
        <th data-col="salt_g" data-type="num" class="r">Salt <span class="si">&#9650;&#9660;</span></th>
        <th data-col="protein_per_pound" data-type="num" class="r" data-ds="desc">Prot/£ <span class="si">&#9650;&#9660;</span></th>
        <th data-col="kcal_per_pound" data-type="num" class="r">kcal/£ <span class="si">&#9650;&#9660;</span></th>
        <th data-col="grams_per_pound" data-type="num" class="r">g/£ <span class="si">&#9650;&#9660;</span></th>
        <th data-col="dietary_symbols" data-type="str" class="sym">Dietary</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div class="no-results" id="no-results" style="display:none">No matching dishes</div>
</div>
<footer>
  Data scraped from <a href="https://www.cookfood.net/menu/special/microwaveable" target="_blank">cookfood.net</a>.
  Product names &amp; nutritional data are property of COOK.
  Per-pound metrics are computed.
</footer>

<script>
const ALL = {data_json};

let sortCol = 'protein_per_pound';
let sortDir = 'desc';
let filtered = [...ALL];

function esc(s){{ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}

function fmtNum(v){{ if(v===null||v===undefined||v==='')return '--'; let n=parseFloat(v); return isNaN(n)?'--':(Number.isInteger(n)?n:n.toFixed(1)); }}

function render(rows){{
  const tbody = document.getElementById('tbody');
  const nores = document.getElementById('no-results');
  if(rows.length===0){{ tbody.innerHTML=''; nores.style.display='block'; return; }}
  nores.style.display='none';
  tbody.innerHTML = rows.map(r => {{
    const op = parseFloat(r.original_price)||0;
    const sv = parseFloat(r.saving)||0;
    const sb = sv>0?` <span class="save-badge" title="You save &pound;${{sv.toFixed(2)}}">-&pound;${{sv.toFixed(2)}}</span>`:'';
    return `<tr>
      <td><a href="${{esc(r.link)}}" target="_blank" rel="noopener">${{esc(r.name)}}</a></td>
      <td class="r">&pound;${{op.toFixed(2)}}${{sb}}</td>
      <td class="r">${{fmtNum(r.weight_g)}}</td>
      <td class="r">${{fmtNum(r.energy_kcal)}}</td>
      <td class="r">${{fmtNum(r.protein_g)}}</td>
      <td class="r">${{fmtNum(r.fat_g)}}</td>
      <td class="r">${{fmtNum(r.carbs_g)}}</td>
      <td class="r">${{fmtNum(r.fibre_g)}}</td>
      <td class="r">${{fmtNum(r.salt_g)}}</td>
      <td class="r">${{fmtNum(r.protein_per_pound)}}</td>
      <td class="r">${{fmtNum(r.kcal_per_pound)}}</td>
      <td class="r">${{fmtNum(r.grams_per_pound)}}</td>
      <td class="sym">${{esc(r.dietary_symbols)}}</td>
    </tr>`;
  }}).join('');
  document.getElementById('row-count').textContent = `${{rows.length}} items`;
}}

function doSort(col,dir){{
  sortCol=col; sortDir=dir;
  const th = document.querySelector(`th[data-col="${{col}}"]`);
  const type = th?th.dataset.type:'str';
  filtered.sort((a,b)=>{{
    let va = type==='num' ? (parseFloat(a[col])||0) : (String(a[col]||'').toLowerCase());
    let vb = type==='num' ? (parseFloat(b[col])||0) : (String(b[col]||'').toLowerCase());
    if(va<vb) return dir==='asc'?-1:1;
    if(va>vb) return dir==='asc'?1:-1;
    return 0;
  }});
  render(filtered);
  document.querySelectorAll('th').forEach(h=>h.classList.remove('sa','sd'));
  const tt = document.querySelector(`th[data-col="${{col}}"]`);
  if(tt) tt.classList.add(dir==='asc'?'sa':'sd');
}}

function doFilter(){{
  const q = document.getElementById('search').value.toLowerCase();
  const focus = document.getElementById('metric-focus').value;
  filtered = ALL.filter(r => {{
    if(q && !r.name.toLowerCase().includes(q) && !r.dietary_symbols.toLowerCase().includes(q)) return false;
    const ds = r.dietary_symbols.toLowerCase();
    const prot = parseFloat(r.protein_g)||0;
    const kcal = parseFloat(r.energy_kcal)||0;
    if(focus==='hi-protein' && prot<25) return false;
    if(focus==='lo-cal' && kcal>=400) return false;
    if(focus==='veggie' && !ds.includes('vegetarian') && !ds.includes('vegan')) return false;
    if(focus==='gluten-free' && !ds.includes('gluten free')) return false;
    if(focus==='dairy-free' && !ds.includes('dairy free')) return false;
    return true;
  }});
  doSort(sortCol, sortDir);
}}

document.querySelectorAll('th').forEach(th => {{
  th.addEventListener('click', () => {{
    const col = th.dataset.col;
    if(sortCol===col) sortDir = sortDir==='asc'?'desc':'asc';
    else {{ sortCol=col; sortDir=th.dataset.ds==='desc'?'desc':'asc'; }}
    doSort(sortCol,sortDir);
  }});
}});

doSort('protein_per_pound','desc');

function copyCmd(btn){{
  const code = btn.parentElement.querySelector('code').textContent;
  navigator.clipboard.writeText(code).then(()=>{{
    btn.textContent='Copied!'; btn.classList.add('copied');
    setTimeout(()=>{{ btn.textContent='Copy'; btn.classList.remove('copied'); }},2000);
  }});
}}

// Inject browser scraper snippet
document.addEventListener('DOMContentLoaded', () => {{
  const el = document.getElementById('browser-snippet');
  if (el) el.textContent = {scraper_js_json};
}});
</script>
</body>
</html>"""

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Generated {OUT_PATH} ({len(html)} bytes, {len(rows)} items)")
