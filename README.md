# Boat House Margins Dashboard

A margins dashboard for a smoothie and bowl bar, replacing a hand-maintained Google Sheets cost calculator.

![Dashboard](assets/screenshot.png)

## Why

Boat House's menu margins lived in a spreadsheet where every ingredient cost, recipe cost, and food-cost % was worked out by hand. Changing one ingredient's purchase price meant re-checking the math on every menu item that used it. This tool reads the same source data and recomputes the entire margin report automatically, so a price change propagates everywhere the moment the sheet is saved.

## How it works

The live data is three Google Sheet tabs: an ingredient database (purchase sizes and costs), a recipe sheet (ingredient amounts per menu item), and a menu list (selling prices). On load, the app:

1. pulls each tab through a read-only service account and validates the required columns, raising a clear error rather than a deep `KeyError` if the shape is wrong;
2. parses currency strings (`$3.20`, `65%`) into numbers, distinguishing a genuine blank from a malformed value;
3. recomputes each ingredient's **cost per recipe unit** from purchase cost ÷ purchase size — *not* read from the sheet's stored column, which goes stale the moment a price changes;
4. multiplies by the amount used in each recipe, rolls the line costs up per menu item, and derives gross profit, margin %, and food cost %.

The output is a sortable table plus a few headline stats (average food cost %, items over a watch threshold, top items by cost and by profit).

## Design decisions

- **Missing cost data returns `None`, never `$0`.** An unpriced or unmatched ingredient is collected and surfaced in the UI — a silent zero would make a margin look healthier than it is.
- **Unit conversions are isolated and commented.** Only two exist: `lbs → oz` (×16) and a business-specific `tea bags → fl oz` yield assumption; everything else is same-unit. Each is a labelled branch in one function, not arithmetic scattered through the code.
- **The core math is pure.** `cost_per_recipe_unit`, `calculate_gross_profit`, and the rest take plain numbers and return plain numbers — no pandas, no file I/O — so they're tested directly against known values.

## Testing

A `pytest` suite covers the pure functions and the full pipeline end to end. The pipeline tests assert against the exact figures from the original hand-maintained Google Sheet, so the port is provably faithful to what the shop was already using. The fixtures are frozen snapshots — they don't move when live prices change, so a failing test means the code changed, not the data.

```
python -m pytest
```

## Stack

Python · pandas · Streamlit · gspread · pytest

## Running locally

```
git clone <repo>
cd boat-house-margin-dashboard
pip install -r requirements.txt
python -m streamlit run app.py
```

The Google Sheet is read through a service account. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in a service-account key JSON under `[gcp_service_account]`; the target sheet must be shared with that account as a viewer. Without it the app still starts and explains what's missing.

## Deployment

The live app is private, it reads a real business's ingredient costs and vendor data.
