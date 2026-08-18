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

DONE — calculator.py, all six functions implemented with passing pytest tests:
- cost_per_recipe_unit(purchase_cost, purchase_size, purchase_unit, recipe_unit) -> float
- calculate_ingredient_cost(amount_used, cost_per_recipe_unit) -> float
- calculate_total_ingredient_cost(ingredient_costs: list[float]) -> float
- calculate_gross_profit(selling_price, total_ingredient_cost) -> float
- calculate_margin_percent(gross_profit, selling_price) -> float
- calculate_food_cost(margin_percent) -> float

IN PROGRESS — the "glue" function (name TBD: build_ingredient_costs or get_recipe_costs_for_item). Sits between calculate_ingredient_cost and calculate_total_ingredient_cost. Signature not written yet. Should:
1. Take a menu item name + recipe sheet DataFrame + ingredient database DataFrame
2. Filter recipe sheet to that menu item's rows
3. Loop rows (iterrows() is fine — pilot dataset is tiny; vectorize later if ever needed), calling cost_per_recipe_unit then calculate_ingredient_cost per row
4. Intercept None (missing cost data) HERE rather than letting it propagate
5. Return a dict: {"costs": list[float], "missing_ingredients": list[str]}

TODO next: cost_per_recipe_unit needs a guard to actually return None on blank/NaN purchase cost (currently unhandled), plus a test using a blank-cost row from the full database (e.g. Collagen, Matcha).

TODO after that: data_loader.py (CSV loading + validation), then app.py (Streamlit MVP: upload → margin report). Stretch goal: in-app persistent editing saved back to CSV.

Conventions:
- Test-first: write the pytest test against known pilot CSV values before implementing the function body
- Docstrings carry data-source context (which CSV each param comes from, or which function computed it) rather than encoding it in function name prefixes
- Run tests with `python -m pytest` (not bare `pytest`) — PATH/venv resolution issue
- Learning-focused project: prefer being walked through reasoning and design decisions over being handed complete solutions