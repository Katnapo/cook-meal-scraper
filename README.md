# COOK Microwaveable Meal Scraper

A weekend project to find the best protein-per-pound and calorie-per-pound value on [COOK](https://www.cookfood.net)'s microwaveable meals. Built as a test drive of DeepSeek via opencode.

When I haven't meal-prepped for the week and London food prices are insane, this helps me pick the most efficient frozen ready meals.

**[Live static viewer &rarr;](https://katnapo.github.io/cook-meal-scraper/)** — no install needed, just opens in your browser.

## What it does

- Scrapes 136 products from the COOK microwaveable meals page
- Pulls price, serving size, dietary symbols, and full nutritional data per portion
- Computes protein/£, kcal/£, and g/£ metrics
- Sortable/filterable web table to find the best value at a glance

## Quick start (local)

```bash
git clone https://github.com/Katnapo/cook-meal-scraper.git
cd cook-meal-scraper/python-app
pip install flask requests
python cook_viewer.py
```

Opens `http://localhost:8080` in your browser. Click **Run Scraper** to pull fresh data from the live site (~45 seconds). Click any column header to sort.

## Repo structure

```
cook-meal-scraper/
├── index.html          # Static page (hosted on GitHub Pages)
├── generate_index.py   # Rebuilds index.html from latest CSV
├── README.md
└── python-app/         # Python Flask app + standalone scraper
    ├── cook_scraper.py
    ├── cook_viewer.py
    ├── run_cook_viewer.bat
    └── cook_microwaveable_meals.csv
```

## Disclaimer

Scraping is at your own risk. This tool makes anonymous HTTP requests to a public website with a polite 0.3s delay between pages. Do not abuse it. All product names and nutritional data are the property of COOK — this is an independent tool, not affiliated with or endorsed by COOK.
