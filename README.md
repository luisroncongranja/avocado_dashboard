# Avocado Market Dashboard

A Dash app exploring US avocado prices and sales volume (2015-2023),
built on the Hass Avocado Board dataset.

## Features (v1)

- Filters: date range, avocado type (conventional/organic), region
  multi-select, and region scope (metro areas vs. national/regional
  aggregates, since this dataset mixes both).
- KPI cards: average price, total volume, total bags, regions in view.
- Charts: price trend over time, volume trend over time, top 10 regions
  by volume, bag-size mix (small/large/XL).

## Run locally

```bash
cd avocado_dashboard
pip install -r requirements.txt
python app.py
```

Then open http://localhost:8050.

## Deploy to Render

This folder is set up as a standalone Render web service:

- `render.yaml` — Render blueprint (build: `pip install -r requirements.txt`,
  start: `gunicorn app:server`).
- `Procfile` — fallback if you create the service manually instead of via
  the blueprint.
- `requirements.txt` — pinned dependencies (Dash, Plotly, Pandas, Gunicorn).
- `data/avocado.csv` — a local copy of the dataset so the service is
  self-contained (no external file dependency at deploy time).

Steps:

1. Push this repo to GitHub.
2. In Render, "New +" -> "Blueprint", point it at the repo/`render.yaml`
   (or "New +" -> "Web Service" and set the build/start commands above,
   with the root directory set to `avocado_dashboard`).
3. Deploy — Render will install requirements and run `gunicorn app:server`.
