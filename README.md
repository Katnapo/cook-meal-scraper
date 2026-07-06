# COOK Microwaveable Meal Scraper

Find the best protein-per-pound and calorie-per-pound value on [COOK](https://www.cookfood.net)'s microwaveable meals. Built as a test drive of DeepSeek via opencode.

When I haven't meal-prepped for the week and London food prices are insane, this helps me pick the most efficient frozen ready meals.

**[Live viewer &rarr;](https://katnapo.github.io/cook-meal-scraper/)** — pre-scraped data, sortable/filterable table, no install needed.

## Quickest way (browser console)

1. Open [cookfood.net/menu/special/microwaveable](https://www.cookfood.net/menu/special/microwaveable)
2. Press **F12** → **Console** tab
3. Paste the contents of [`scraper.js`](scraper.js) and press Enter
4. Wait ~45 seconds for results. A sortable overlay appears with all 119 single-serving meals.

No install, no Python, no clone. Runs entirely in your browser.

## Python app (local server)

```bash
git clone https://github.com/Katnapo/cook-meal-scraper.git
cd cook-meal-scraper/python-app
pip install flask requests
python cook_viewer.py
```

Opens `http://localhost:8080` with a sortable table + live "Run Scraper" button.

## What it scrapes

- 136 products from the COOK microwaveable meals page
- Price, serving size, dietary symbols, full nutrition per portion
- Computes protein/£, kcal/£, and g/£ metrics
- Filters to single-serving items only

## Repo structure

```
├── index.html           # Static site (GitHub Pages)
├── scraper.js           # Browser-console scraper (paste into F12 → Console)
├── generate_index.py    # Rebuilds index.html from CSV
├── README.md
└── python-app/          # Python Flask app + standalone scraper
    ├── cook_scraper.py
    ├── cook_viewer.py
    ├── run_cook_viewer.bat
    └── cook_microwaveable_meals.csv
```

## Disclaimer

Scraping is at your own risk. This tool makes HTTP requests from your browser or machine to a public website with a polite delay. Do not abuse it. Not affiliated with or endorsed by COOK — all product names and nutritional data are the property of COOK.
