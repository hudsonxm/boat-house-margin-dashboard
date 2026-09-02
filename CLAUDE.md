Project: Row and Ride Margins Dashboard

Building a Python tool to replace a Google Sheets margin calculator for my mom's smoothie/bowl bar (Row and Ride / Boathouse Nutrition). It's also my resume project for co-op search (rising 2nd year, Northeastern).
Goal: Streamlit dashboard where you upload 3 CSVs (ingredient database, recipe sheet, menu items) and it automatically calculates ingredient cost, gross profit, and food cost % per menu item — replacing manual spreadsheet math. (Margin % is still computed inside calculator.py — it's how food cost % is derived — but it is NOT surfaced in the report or UI: the shop only tracks food cost %.)

Data schema (full CSVs live in /data; pinned test fixtures in /data/fixtures):
ingredient_database.csv: Ingredient ID, Ingredient, Category, Purchase Size, Purchase Unit, Purchase Cost, Cost Per Recipe Unit, Recipe Unit, Supplier, Last Updated, Notes. Ingredient ID (e.g. FRZ-BANANAS, PKG-20OZ_LID) is the stable join key. The database is now fully populated — every row has cost data (many rows are supplier-estimated, flagged "EST" in Notes). No more pilot_ingredient_database.csv; the calculator's regression fixtures live in /data/fixtures/ instead.
recipe_sheet.csv: Menu Item, Ingredient ID, Ingredient, Ingredient Category, Amount Used, Recipe Unit, Notes. Joins to ingredient_database on Ingredient ID. Duplicate ingredient rows per menu item were consolidated manually for the pilot (e.g. Shark Bite's two Power Tea Flavors rows merged into one) — the code does NOT dedupe automatically yet.
menu_items.csv: Menu Item, Menu Item Category, Available At, Selling Price, Notes. The old Total Ingredient Cost / Gross Profit / Margin % / Food Cost columns have been removed from the file — they are computed outputs now, not stored.

/data/fixtures/ (pinned regression oracle for test_calculator.py — deliberately frozen, do NOT reconcile with /data):
- ingredient_database.csv, recipe_sheet.csv, menu_items.csv: the 4 original pilot menu items (Peanut Butter Banana, Cold Brew Bliss, Shark Bite, Acai Mixed Berry Bowl) with the exact ingredient amounts, IDs, and prices that produced the hand-calculated margins. These diverge from /data on purpose (e.g. fixture Shark Bite draws 3 fl oz from BEV-ICED_TEA costed via the 16.88 fl oz/bag conversion; live data models brewed tea as its own PRP-BREWED_TEA ingredient. Fixture Acai bowl bakes 4 toppings into the recipe at $12.00; live menu_items prices it $13.90 with toppings as separate line items).
- expected_ingredient_costs.csv: Menu Item, Ingredient ID, Expected Ingredient Cost ($-string) — per-row expected output, computed from unrounded Purchase Cost / Purchase Size.
- expected_margins.csv: Menu Item, Expected Total Ingredient Cost, Expected Gross Profit, Expected Margin %, Expected Food Cost ($/%-strings, display-rounded — assert with tolerance ~1 cent, not exact).

Key architecture decision: The cost/profit/margin/food-cost columns (previously hand-calculated in Sheets) are computed outputs, not inputs — the engine recomputes Cost Per Recipe Unit from Purchase Cost / Purchase Size (rather than trusting the pre-filled column, which goes stale when prices change), multiplies by Amount Used from the recipe sheet, and derives everything else, so updating one ingredient price cascades everywhere automatically. Those columns have now been deleted from menu_items.csv and recipe_sheet.csv entirely; the reference values for comparison live only in /data/fixtures/expected_*.csv.

Known modeling gap (not yet handled): bowls sell at a price that "includes any 4 toppings", but the bowl rows in recipe_sheet.csv contain no toppings — so build_ingredient_costs currently undercounts a served bowl's cost and its margin looks artificially high. Needs a "base + included toppings" story before the bowl numbers are trustworthy.

Unit conversion notes (in cost_per_recipe_unit):
- lbs → oz uses factor 16 (standard unit conversion) — the workhorse conversion; used by all the bulk lbs-purchased items
- bags → fl oz uses factor 16.88 (Row and Ride's estimated fl oz yield per tea bag — a business assumption, NOT a universal conversion). Now only exercised by /data/fixtures/ — the live database tracks Brewed Tea (PRP-BREWED_TEA) as its own prepared ingredient with a hand-entered batch cost, so nothing in /data/recipe_sheet.csv hits this branch. Keep it anyway for the regression fixtures.
- everything else falls through to factor 1 (oz→oz, fl oz→fl oz, each→each, ml→ml, cubes→cubes). Across the whole current dataset, lbs→oz and the fixture-only bags→fl oz are the ONLY real conversions — every other row was entered with Purchase Unit == Recipe Unit.
- FIXED (was a data-entry landmine): Coconut Cubes now has Purchase Unit "cubes" and Recipe Unit "cubes" matching exactly, so it hits the factor-1 path on purpose instead of by accident.

Missing-data policy: When cost data is blank (NaN), cost_per_recipe_unit returns None. The None check happens ONCE, in the glue function — downstream math functions stay dumb and do not each check for None. Missing ingredients (unmatched Ingredient ID, or None cost) are flagged and surfaced in the UI, never silently skipped or treated as $0.00 (which would make margins look artificially good). The full database currently has no blank rows, so this path now guards newly-added-but-unpriced ingredients and mistyped IDs.

Structure:
row_and_ride_dashboard/
├── data/              # full CSVs for local dev
│   └── fixtures/      # pinned 4-item pilot + expected_*.csv oracles for tests
├── src/
│   ├── calculator.py  # pure functions: cost lookup, margin math
│   └── data_loader.py # CSV loading, cleaning, validation
├── app.py             # Streamlit UI (in progress — read-only margin report MVP)
├── tests/
│   ├── test_calculator.py  # pytest: unit tests + end-to-end pipeline tests against /data/fixtures
│   └── test_data_loader.py # pytest: strip_currency/_parse_currency_column/_validate_columns + load_* against /data/fixtures
├── requirements.txt
└── README.md

DONE — calculator.py is complete, all functions implemented with passing pytest tests:
- cost_per_recipe_unit(purchase_cost, purchase_size, purchase_unit, recipe_unit) -> float | None — returns None if purchase_cost or purchase_size is NaN (guarded via pd.isna, once, at the top)
- calculate_ingredient_cost(amount_used, cost_per_recipe_unit) -> float
- build_ingredient_costs(menu_item, recipe_sheet, ingredient_database) -> dict — the glue function. Filters recipe_sheet to menu_item's rows, joins each row to ingredient_database on Ingredient ID (single stable key — replaced the old Ingredient + Category composite join, which was fragile on plural/singular and name-typo mismatches), calls cost_per_recipe_unit then calculate_ingredient_cost, and routes any unmatched ID or None cost into missing_ingredients (as the Ingredient ID string) instead of costs. Returns {"costs": list[float], "missing_ingredients": list[str]}.
- calculate_total_ingredient_cost(ingredient_costs: list[float]) -> float
- calculate_gross_profit(selling_price, total_ingredient_cost) -> float
- calculate_margin_percent(gross_profit, selling_price) -> float
- calculate_food_cost(margin_percent) -> float
- build_margin_report(menu_items, recipe_sheet, ingredient_database) -> pd.DataFrame — the UI glue function. One row per menu item, chaining build_ingredient_costs → calculate_total_ingredient_cost → calculate_gross_profit → calculate_margin_percent → calculate_food_cost. Columns: Menu Item, Category (from menu_items.csv's Menu Item Category), Selling Price, Total Ingredient Cost, Gross Profit, Food Cost, Missing Ingredients (list). Margin % is computed on the way to Food Cost but deliberately NOT a column. Missing-ingredient rows are left with their partial (understated-cost, overstated-margin) numbers intact — build_margin_report does NOT null them out; app.py is responsible for flagging/grey-ing those rows off the non-empty Missing Ingredients list. Takes already-loaded DataFrames (no data_loader import — the loader → calculator dependency stays one-way).

DONE — data_loader.py is complete, all functions implemented with passing pytest tests (tests/test_data_loader.py). Job is loading + cleaning + validating only — no margin/cost math, that boundary stays in calculator.py. Resolved the currency-string landmine above (Purchase Cost, Selling Price):
- strip_currency(series: pd.Series) -> pd.Series — strips "$", ",", "%" and casts to float via pd.to_numeric(errors="coerce"). Round-trips via astype(str) so numeric columns don't crash the .str accessor; NaN survives the round-trip (str(nan) == "nan" coerces back to NaN). Exported for reuse — also what test_calculator.py's pipeline tests use to parse fixtures/expected_*.csv's "$"/"%" strings.
- _parse_currency_column(df, column, csv_name) -> pd.Series — wraps strip_currency, then raises ValueError (listing the original bad values) if a populated cell failed to parse (a real data-entry typo, e.g. "$9.0.0"). Genuine blanks (NaN in, NaN out) pass through untouched — this is what distinguishes "missing" from "malformed."
- _validate_columns(df, required, csv_name) -> None — raises ValueError listing missing required columns, instead of a cryptic KeyError three layers deep in calculator.py.
- load_ingredient_database(source) -> pd.DataFrame — validates {Ingredient ID, Purchase Size, Purchase Unit, Purchase Cost, Recipe Unit}, cleans Purchase Cost.
- load_recipe_sheet(source) -> pd.DataFrame — validates {Menu Item, Ingredient ID, Amount Used}; no cleaning needed, nothing in recipe_sheet.csv is currency-formatted.
- load_menu_items(source) -> pd.DataFrame — validates {Menu Item, Selling Price}, cleans Selling Price.
- `source` can be a local path or a Streamlit-uploaded file object — pd.read_csv handles both the same way.
- Design landed on one function per CSV + shared strip_currency/_parse_currency_column/_validate_columns helpers (the open question from before).

DONE — end-to-end pipeline tests, in test_calculator.py, exercising data_loader.py + calculator.py together against /data/fixtures:
- test_pipeline_ingredient_costs_all_menu_items — loads /data/fixtures/{ingredient_database,recipe_sheet}.csv through data_loader.py, runs all 4 pilot menu items through build_ingredient_costs, and checks each cost against expected_ingredient_costs.csv (parsed via strip_currency). build_ingredient_costs returns bare costs with no Ingredient ID attached, so both sides are sorted by ["Menu Item", "Ingredient ID"] before comparing — an explicit alignment, not a reliance on the two fixture files happening to list ingredients in the same order.
- test_pipeline_margins_all_menu_items — additionally loads menu_items.csv, chains the full pipeline (build_ingredient_costs → calculate_total_ingredient_cost → calculate_gross_profit → calculate_margin_percent → calculate_food_cost) per menu item, and checks totals against expected_margins.csv with ~1-cent/0.01-point tolerance (display-rounded, not exact). Still asserts Margin % since the fixture column exists — the not-in-the-report decision only applies to build_margin_report's output.
- test_build_margin_report_all_menu_items — loads the three fixture CSVs, calls build_margin_report once, and asserts row count + Total Ingredient Cost / Gross Profit / Food Cost / Missing Ingredients per menu item against expected_margins.csv (same tolerance). Margin % is loaded but not asserted (not a report column). Largely supersedes the inline loop in test_pipeline_margins_all_menu_items.

IN PROGRESS — app.py (Streamlit MVP). Plan agreed:
- Scope: read-only margin report. Upload the 3 CSVs (fall back to /data/*.csv when nothing is uploaded, for dev); run through data_loader.py → build_margin_report; render as a table.
- Missing-ingredient rows: surface a per-menu-item st.warning listing the unmatched Ingredient IDs, and visually mark those rows — build_margin_report leaves their numbers in place, so the UI is the only thing stopping an understated cost / inflated margin from looking legit. No missing rows exist in /data today, so this only fires on genuine misuse (mistyped ID, ingredient not yet added).
- Show the bowl-undercount caveat (toppings not in recipe_sheet) somewhere visible near the bowl rows.
- requirements.txt still needs `streamlit` added.
Stretch goal: sidebar widget to override one ingredient's Purchase Cost and watch food cost % recompute (demonstrates the cascade). Further stretch: in-app persistent editing saved back to CSV.

Conventions:
- Test-first: write the pytest test against known pilot CSV values before implementing the function body
- Docstrings carry data-source context (which CSV each param comes from, or which function computed it) rather than encoding it in function name prefixes
- Run tests with `python -m pytest` (not bare `pytest`) — PATH/venv resolution issue
- Learning-focused project: prefer being walked through reasoning and design decisions over being handed complete solutions