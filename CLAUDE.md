Project: Row and Ride Margins Dashboard

Building a Python tool to replace a Google Sheets margin calculator for my mom's smoothie/bowl bar (Row and Ride / Boathouse Nutrition). It's also my resume project for co-op search (rising 2nd year, Northeastern).
Goal: Streamlit dashboard where you upload 3 CSVs (ingredient database, recipe sheet, menu items) and it automatically calculates ingredient cost, gross profit, margin %, and food cost % per menu item — replacing manual spreadsheet math.

Data schema (pilot CSVs already exist in /data):
ingredient_database.csv: Ingredient, Category, Purchase Size, Purchase Unit, Purchase Cost, Cost Per Recipe Unit, Recipe Unit, Supplier, Last Updated, Notes. Full database is sparse (many blank cost rows). pilot_ingredient_database.csv is a separate copy containing only rows with complete cost data — used as the test fixture for calculator logic.
recipe_sheet.csv: Menu Item, Ingredient, Ingredient Category, Amount Used, Recipe Unit, Ingredient Cost, Notes. Duplicate ingredient rows per menu item were consolidated manually for the pilot (e.g. Shark Bite's two Power Tea Flavors rows merged into one) — the code does NOT dedupe automatically yet.
menu_items.csv: Menu Item, Menu Item Category, Selling Price, Total Ingredient Cost, Gross Profit, Margin %, Food Cost, Notes.

Key architecture decision: The cost/profit/margin/food-cost columns in menu_items.csv and the Ingredient Cost column in recipe_sheet.csv were previously hand-calculated in Sheets. In the Python tool these become computed outputs, not inputs — the engine recomputes Cost Per Recipe Unit from Purchase Cost / Purchase Size (rather than trusting the pre-filled column, which goes stale when prices change), multiplies by Amount Used from the recipe sheet, and derives everything else, so updating one ingredient price cascades everywhere automatically.

Unit conversion notes (in cost_per_recipe_unit):
- lbs → oz uses factor 16 (standard unit conversion)
- bags → fl oz uses factor 16.88 (Row and Ride's estimated fl oz yield per tea bag — a business assumption, NOT a universal conversion)
- everything else falls through to factor 1 (oz→oz, fl oz→fl oz, each→each, ml→ml)
- Known data-entry landmine: Coconut Cubes has Purchase Unit "cubes" vs Recipe Unit "cube" (plural/singular mismatch). Currently correct by accident via the factor-1 fallback. Units meant to be identical should match exactly.

Missing-data policy: When cost data is blank, cost_per_recipe_unit returns None. The None check happens ONCE, in the glue function — downstream math functions stay dumb and do not each check for None. Missing ingredients are flagged and surfaced in the UI, never silently skipped or treated as $0.00 (which would make margins look artificially good).

Structure:
row_and_ride_dashboard/
├── data/              # pilot CSVs for local dev + test fixtures
├── src/
│   ├── calculator.py  # pure functions: cost lookup, margin math
│   └── data_loader.py # CSV validation/cleaning (not started)
├── app.py             # Streamlit UI (not started)
├── tests/
│   └── test_calculator.py  # pytest, validated against the 4 known pilot menu items
├── requirements.txt
└── README.md

DONE — calculator.py is complete, all functions implemented with passing pytest tests:
- cost_per_recipe_unit(purchase_cost, purchase_size, purchase_unit, recipe_unit) -> float | None — returns None if purchase_cost or purchase_size is NaN (guarded via pd.isna, once, at the top)
- calculate_ingredient_cost(amount_used, cost_per_recipe_unit) -> float
- build_ingredient_costs(menu_item, recipe_sheet, ingredient_database) -> dict — the glue function. Filters recipe_sheet to menu_item's rows, joins each row to ingredient_database on Ingredient + Category (recipe_sheet calls this column "Ingredient Category", ingredient_database calls it "Category" — don't typo this again), calls cost_per_recipe_unit then calculate_ingredient_cost, and routes any unmatched ingredient or None cost into missing_ingredients instead of costs. Returns {"costs": list[float], "missing_ingredients": list[str]}.
- calculate_total_ingredient_cost(ingredient_costs: list[float]) -> float
- calculate_gross_profit(selling_price, total_ingredient_cost) -> float
- calculate_margin_percent(gross_profit, selling_price) -> float
- calculate_food_cost(margin_percent) -> float

Known landmine NOT yet fixed (deliberately deferred to data_loader.py): Purchase Cost (and recipe_sheet's Ingredient Cost) are stored as currency strings like "$32.93" in the raw CSVs. pd.read_csv loads these as strings, so build_ingredient_costs's float(row_data["Purchase Cost"]) will raise ValueError until data_loader.py strips the "$" and casts to float before handing DataFrames to calculator.py. calculator.py intentionally does no currency cleaning itself — that's data_loader.py's job, not calculator.py's.

test_calculator.py's build_ingredient_costs tests use hand-constructed, already-clean DataFrames rather than pd.read_csv on the pilot CSVs — they're unit tests of the join/missing-data logic, isolated from data_loader.py's (not-yet-written) cleaning. TODO once data_loader.py exists: add a separate end-to-end test that loads the real pilot CSVs through it and runs every pilot menu item through the full calculator.py pipeline, checking totals against the known hand-calculated margins.

TODO next: data_loader.py (CSV loading + validation), then app.py (Streamlit MVP: upload → margin report). Stretch goal: in-app persistent editing saved back to CSV.

data_loader.py spec (NOT STARTED):
Job is loading + cleaning + validating only — no margin/cost math, that boundary stays in calculator.py.
1. Load the 3 CSVs — from a local path for dev/testing, from a Streamlit-uploaded file object in the app (pd.read_csv handles both the same way).
2. Clean currency/percent-formatted columns (strip "$" and "%", cast to float):
   - ingredient_database.csv: Purchase Cost is "$28.82"-style strings (Purchase Size is already clean numeric).
   - menu_items.csv: Selling Price is "$12.00"-style — this is the only menu_items column calculator.py needs as an input.
   - menu_items.csv's Total Ingredient Cost/Gross Profit/Margin %/Food Cost and recipe_sheet.csv's Ingredient Cost are the old hand-calculated columns the architecture decision already says become computed outputs — cleaning them is optional/for-comparison-later, not required for the pipeline to run.
3. Leave genuinely blank cells as NaN (pandas' default) — don't fill or guess, per the missing-data policy. The only real work is not breaking on a column that mixes NaN and "$X.XX" strings.
4. Validate required columns are present per CSV (e.g. ingredient_database needs Ingredient, Category, Purchase Size, Purchase Unit, Purchase Cost, Recipe Unit) and raise/report something clear on schema drift, rather than a cryptic KeyError three layers deep in calculator.py.
Open design question: one function per CSV (load_ingredient_database(path), load_recipe_sheet(path), load_menu_items(path), each doing read+clean+validate for its own schema) vs. one generic loader plus a shared strip_currency(series) helper reused across all three. Leaning toward one-function-per-CSV + shared helper since each file's cleaning needs differ, but not decided.

Conventions:
- Test-first: write the pytest test against known pilot CSV values before implementing the function body
- Docstrings carry data-source context (which CSV each param comes from, or which function computed it) rather than encoding it in function name prefixes
- Run tests with `python -m pytest` (not bare `pytest`) — PATH/venv resolution issue
- Learning-focused project: prefer being walked through reasoning and design decisions over being handed complete solutions