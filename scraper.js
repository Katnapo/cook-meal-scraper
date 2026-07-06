/**
 * COOK Microwaveable Meals Scraper
 * 
 * HOW TO USE:
 * 1. Go to https://www.cookfood.net/menu/special/microwaveable
 * 2. Press F12 to open DevTools, click the "Console" tab
 * 3. Paste this entire script and press Enter
 * 4. Wait ~45 seconds while it scrapes nutrition data
 * 
 * Runs entirely in your browser. No install, no server, no Python.
 * Rate-limited (300ms between requests) — be polite to the server.
 */

(function() {
'use strict';

const DELAY = 300;
const PRODUCT_URL = 'https://www.cookfood.net/products/';

if (document.getElementById('cook-scraper-overlay')) return;

function $(t, a) { const e = document.createElement(t); if (a) for (const k in a) e[k] = a[k]; return e; }

const overlay = $('div', { id: 'cook-scraper-overlay' });
overlay.innerHTML = `<div style="
  position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.85);z-index:99999;
  display:flex;flex-direction:column;color:#fff;font-family:-apple-system,BlinkMacSystemFont,sans-serif;
  overflow-y:auto;padding:0">
<div style="background:#1a6b4b;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:1">
  <div><strong style="font-size:16px">COOK Meal Scraper</strong><br><span style="font-size:12px;opacity:.8">Scraping nutrition data...</span></div>
  <button id="cook-scraper-close" style="background:#fff;color:#1a6b4b;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;font-weight:600">Close</button>
</div>
<div style="padding:16px;text-align:center" id="cook-scraper-status">
  <div style="margin:40px 0;font-size:14px">Extracting product list...</div>
  <div style="background:#333;height:6px;border-radius:3px;max-width:400px;margin:0 auto">
    <div id="cook-scraper-bar" style="background:#4caf50;height:100%;border-radius:3px;width:0%;transition:width .2s"></div>
  </div>
  <div id="cook-scraper-msg" style="margin-top:12px;font-size:12px;opacity:.7"></div>
</div>
<div id="cook-scraper-results" style="display:none"></div>
</div>`;
document.body.appendChild(overlay);

document.getElementById('cook-scraper-close').onclick = () => overlay.remove();

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function fmtNum(v) { if (v === null || v === undefined || v === '') return '--'; const n = parseFloat(v); return isNaN(n) ? '--' : (Number.isInteger(n) ? String(n) : n.toFixed(1)); }

function extractProducts() {
  const scripts = document.querySelectorAll('script');
  for (const s of scripts) {
    const m = s.textContent.match(/ReactDOM\.hydrate\(React\.createElement\(Category\.CategoryContainer,\s*(\{.*?"productSections"\s*:\s*\[[\s\S]*?\]\s*,\s*"BaseUrl"[\s\S]*?\})\s*\)/);
    if (m) {
      try { return JSON.parse(m[1]).productSections || []; }
      catch(e) { return []; }
    }
  }
  return [];
}

function parseNutrition(html) {
  const m = html.match(/<table[^>]*>([\s\S]*?)<\/table>/i);
  if (!m) return {};
  const rows = m[1].match(/<tr[^>]*>([\s\S]*?)<\/tr>/gi) || [];
  const nut = {};
  for (const row of rows) {
    const cells = row.match(/<t[hd][^>]*>([\s\S]*?)<\/t[hd]>/gi) || [];
    if (cells.length < 2) continue;
    const name = cells[0].replace(/<[^>]+>/g, '').trim().toLowerCase().replace(/\s+/g, ' ');
    if (!name || name === 'typical values' || name.startsWith('typical values')) continue;
    const v100g = cells[1].replace(/<[^>]+>/g, '').trim();
    const vPortion = cells.length >= 3 ? cells[2].replace(/<[^>]+>/g, '').trim() : '';
    nut[name] = { per_100g: v100g, per_portion: vPortion };
  }
  return nut;
}

function extractNum(s) {
  if (!s) return null;
  const m = s.replace(/,/g, '').match(/[\d.]+/);
  return m ? parseFloat(m[0]) : null;
}

function getNut(nut, key, grams) {
  const v = nut[key] || nut[key + ' (g)'] || nut['of which: ' + key + ' (g)'];
  if (!v) return null;
  let val = extractNum(v.per_portion);
  if (val === null && grams) {
    val = extractNum(v.per_100g);
    if (val !== null) val = Math.round(val * grams / 100 * 10) / 10;
  }
  return val;
}

function isSingleServing(p) {
  const title = p.title || '';
  if (/meal box/i.test(title)) return false;
  for (const s of (p.servings || [])) {
    const t = s.servesText || '';
    if (/Serves\s+1|Pot\s+for\s+One|for\s+[Oo]ne/i.test(t)) return { product: p, serving: s };
    if (!/Serves\s+\d/.test(t)) return { product: p, serving: s };
  }
  return null;
}

function renderTable(rows) {
  const container = document.getElementById('cook-scraper-results');
  const status = document.getElementById('cook-scraper-status');
  status.style.display = 'none';
  container.style.display = 'block';

  const style = $('style');
  style.textContent = `
    .cst{border-collapse:collapse;width:100%;font-size:11px;color:#ddd}
    .cst th{background:#1a6b4b;color:#fff;padding:6px 8px;text-align:left;cursor:pointer;user-select:none;position:sticky;top:42px;z-index:1;font-weight:500}
    .cst th:hover{background:#1e7d57}
    .cst th .si{margin-left:3px;opacity:.4;font-size:9px}
    .cst th.sa .si,.cst th.sd .si{opacity:1}
    .cst td{padding:5px 8px;border-bottom:1px solid #333;white-space:nowrap}
    .cst tr:hover td{background:#222}
    .cst .r{text-align:right}
    .cst .save-badge{color:#ff9800;font-size:10px;margin-left:3px}
    .cst a{color:#81c784;text-decoration:none}
    .cst a:hover{text-decoration:underline}
    .cst .sym{color:#888;font-size:10px;max-width:140px;overflow:hidden;text-overflow:ellipsis}
    .cs-toolbar{display:flex;gap:8px;padding:8px 16px;flex-wrap:wrap;align-items:center;background:#222;position:sticky;top:0;z-index:2}
    .cs-toolbar input,.cs-toolbar select{padding:4px 8px;border:1px solid #444;border-radius:4px;background:#111;color:#ddd;font-size:11px}
    .cs-toolbar .cs-count{font-size:11px;color:#888;margin-left:auto}
    .cs-copy-btn{background:#1a6b4b;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px}
    .cs-copy-btn:hover{background:#1e7d57}
    .cs-copy-btn.copied{background:#4caf50}
  `;
  container.appendChild(style);

  container.innerHTML += `
    <div class="cs-toolbar">
      <input type="text" id="cs-search" placeholder="Filter..." oninput="window._csFilter()">
      <select id="cs-focus" onchange="window._csFilter()">
        <option value="all">All</option>
        <option value="hi-protein">Protein ≥25g</option>
        <option value="lo-cal">Calories <400</option>
        <option value="veggie">Vegetarian/Vegan</option>
        <option value="gluten-free">Gluten Free</option>
        <option value="dairy-free">Dairy Free</option>
      </select>
      <span class="cs-count" id="cs-count"></span>
      <button class="cs-copy-btn" onclick="window._csCopy()">Copy as CSV</button>
    </div>
    <table class="cst" id="cs-table">
      <thead><tr>
        <th data-col="name" data-type="str">Dish <span class="si">▲▼</span></th>
        <th data-col="original_price" data-type="num" class="r">Price <span class="si">▲▼</span></th>
        <th data-col="weight_g" data-type="num" class="r">g</th>
        <th data-col="energy_kcal" data-type="num" class="r">kcal</th>
        <th data-col="protein_g" data-type="num" class="r">Prot</th>
        <th data-col="fat_g" data-type="num" class="r">Fat</th>
        <th data-col="carbs_g" data-type="num" class="r">Carbs</th>
        <th data-col="protein_per_pound" data-type="num" class="r" data-ds="desc">Prot/£ <span class="si">▲▼</span></th>
        <th data-col="kcal_per_pound" data-type="num" class="r">kcal/£</th>
        <th data-col="dietary_symbols" data-type="str" class="sym">Dietary</th>
      </tr></thead>
      <tbody id="cs-tbody"></tbody>
    </table>`;

  // Store data globally
  window._csData = rows;
  window._csSortCol = 'protein_per_pound';
  window._csSortDir = 'desc';
  window._csFilter();
}

window._csFilter = function() {
  const q = (document.getElementById('cs-search')?.value || '').toLowerCase();
  const focus = document.getElementById('cs-focus')?.value || 'all';
  let rows = window._csData.filter(r => {
    if (q && !r.name.toLowerCase().includes(q) && !r.dietary_symbols.toLowerCase().includes(q)) return false;
    const ds = r.dietary_symbols.toLowerCase();
    const prot = parseFloat(r.protein_g) || 0;
    const kcal = parseFloat(r.energy_kcal) || 0;
    if (focus === 'hi-protein' && prot < 25) return false;
    if (focus === 'lo-cal' && kcal >= 400) return false;
    if (focus === 'veggie' && !ds.includes('vegetarian') && !ds.includes('vegan')) return false;
    if (focus === 'gluten-free' && !ds.includes('gluten free')) return false;
    if (focus === 'dairy-free' && !ds.includes('dairy free')) return false;
    return true;
  });

  const col = window._csSortCol;
  const dir = window._csSortDir;
  const th = document.querySelector(`#cs-table th[data-col="${col}"]`);
  const type = th?.dataset?.type || 'str';
  rows.sort((a, b) => {
    let va = type === 'num' ? (parseFloat(a[col]) || 0) : String(a[col] || '').toLowerCase();
    let vb = type === 'num' ? (parseFloat(b[col]) || 0) : String(b[col] || '').toLowerCase();
    if (va < vb) return dir === 'asc' ? -1 : 1;
    if (va > vb) return dir === 'asc' ? 1 : -1;
    return 0;
  });

  const tbody = document.getElementById('cs-tbody');
  if (!tbody) return;
  tbody.innerHTML = rows.map(r => {
    const op = parseFloat(r.original_price) || 0;
    const sv = parseFloat(r.saving) || 0;
    const sb = sv > 0 ? ` <span class="save-badge">-£${sv.toFixed(2)}</span>` : '';
    return `<tr>
      <td><a href="${esc(r.link)}" target="_blank">${esc(r.name)}</a></td>
      <td class="r">£${op.toFixed(2)}${sb}</td>
      <td class="r">${fmtNum(r.weight_g)}</td>
      <td class="r">${fmtNum(r.energy_kcal)}</td>
      <td class="r">${fmtNum(r.protein_g)}</td>
      <td class="r">${fmtNum(r.fat_g)}</td>
      <td class="r">${fmtNum(r.carbs_g)}</td>
      <td class="r">${fmtNum(r.protein_per_pound)}</td>
      <td class="r">${fmtNum(r.kcal_per_pound)}</td>
      <td class="sym">${esc(r.dietary_symbols)}</td>
    </tr>`;
  }).join('');
  document.getElementById('cs-count').textContent = `${rows.length} items`;

  document.querySelectorAll('#cs-table th').forEach(h => h.classList.remove('sa', 'sd'));
  const tt = document.querySelector(`#cs-table th[data-col="${col}"]`);
  if (tt) tt.classList.add(dir === 'asc' ? 'sa' : 'sd');
};

// Sort handler
document.addEventListener('click', function(e) {
  const th = e.target.closest('#cs-table th');
  if (!th || !th.dataset.col) return;
  const col = th.dataset.col;
  if (window._csSortCol === col) {
    window._csSortDir = window._csSortDir === 'asc' ? 'desc' : 'asc';
  } else {
    window._csSortCol = col;
    window._csSortDir = th.dataset.ds === 'desc' ? 'desc' : 'asc';
  }
  window._csFilter();
});

// Copy CSV
window._csCopy = function() {
  const data = window._csData;
  if (!data.length) return;
  const keys = ['name','original_price','saving','weight_g','energy_kcal','protein_g','fat_g','carbs_g','protein_per_pound','kcal_per_pound','dietary_symbols','link'];
  let csv = keys.join(',') + '\n';
  csv += data.map(r => keys.map(k => {
    let v = r[k] || '';
    if (v.includes(',') || v.includes('"')) v = '"' + v.replace(/"/g, '""') + '"';
    return v;
  }).join(',')).join('\n');
  navigator.clipboard.writeText(csv).then(() => {
    const btn = document.querySelector('.cs-copy-btn');
    btn.textContent = 'Copied!'; btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy as CSV'; btn.classList.remove('copied'); }, 2000);
  });
};

// --- MAIN ---
async function main() {
  const products = extractProducts();
  if (!products.length) {
    document.getElementById('cook-scraper-msg').textContent = 'Error: Could not find product data. Are you on the microwaveable meals page?';
    return;
  }

  const singles = [];
  for (const p of products) {
    const match = isSingleServing(p);
    if (match) singles.push(match);
  }

  const bar = document.getElementById('cook-scraper-bar');
  const msgEl = document.getElementById('cook-scraper-msg');
  const total = singles.length;
  const results = [];

  for (let i = 0; i < total; i++) {
    const { product, serving } = singles[i];
    const name = product.title || 'Unknown';
    const link = product.link || '';
    const price = parseFloat(serving.price) || 0;
    const saving = parseFloat(serving.saving) || 0;
    const effPrice = price - saving;
    if (effPrice <= 0) continue;

    const grams = parseFloat(serving.servesInGrams) || 0;
    const symbols = (product.symbols || []).map(s => s.title).join(' | ');

    bar.style.width = ((i / total) * 100) + '%';
    msgEl.textContent = `${name} (${i+1}/${total})`;

    let nut = {};
    try {
      const resp = await fetch(PRODUCT_URL + link);
      const html = await resp.text();
      nut = parseNutrition(html);
    } catch(e) {}

    const energyKcal = getNut(nut, 'energy (cal', grams);
    const proteinG = getNut(nut, 'protein', grams);
    const fatG = getNut(nut, 'fat', grams);
    const carbsG = getNut(nut, 'carbohydrate', grams);
    const ppPound = effPrice > 0 && proteinG ? Math.round(proteinG / effPrice * 100) / 100 : null;
    const kcPound = effPrice > 0 && energyKcal ? Math.round(energyKcal / effPrice * 100) / 100 : null;

    results.push({
      name, link: PRODUCT_URL + link,
      original_price: price, saving, weight_g: grams,
      energy_kcal: energyKcal, protein_g: proteinG, fat_g: fatG, carbs_g: carbsG,
      protein_per_pound: ppPound, kcal_per_pound: kcPound,
      dietary_symbols: symbols,
    });

    await new Promise(r => setTimeout(r, DELAY));
  }

  results.sort((a, b) => (b.protein_per_pound || 0) - (a.protein_per_pound || 0));
  bar.style.width = '100%';
  msgEl.textContent = `Done — ${results.length} items scraped`;
  renderTable(results);
}

main().catch(e => {
  document.getElementById('cook-scraper-msg').textContent = 'Error: ' + e.message;
});

})();
