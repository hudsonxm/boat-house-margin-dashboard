Project: Row and Ride Margins Dashboard

Building a Python tool to replace a Google Sheets margin calculator for my mom's smoothie/bowl bar (Row and Ride / Boathouse Nutrition). It's also my resume project for co-op search (rising 2nd year, Northeastern).
Goal: Streamlit dashboard where you upload 3 CSVs (ingredient database, recipe sheet, menu items) and it automatically calculates ingredient cost, gross profit, and food cost % per menu item — replacing manual spreadsheet math. (Margin % is still computed inside calculator.py — it's how food cost % is derived — but it is NOT surfaced in the report or UI: the shop only tracks food cost %.)

Data source: the running app reads the live Google Sheet (see app.py — service account). The only tracked data is `data/fixtures/` (frozen pilot test inputs — see below); loose `data/*.csv` is gitignored. Repo is public: no full ingredient-cost export or supplier list belongs in it.

Sheet tab schema (what data_loader validates against):
- INGREDIENT DATABASE: Ingredient ID, Ingredient, Category, Purchase Size, Purchase Unit, Purchase Cost, Cost Per Recipe Unit, Recipe Unit, Supplier, Last Updated, Notes. Ingredient ID (e.g. FRZ-BANANAS, PKG-20OZ_LID) is the stable join key. Cost Per Recipe Unit is a stored-but-ignored column — the engine recomputes it. Many rows are supplier-estimated ("EST" in Notes).
- RECIPE SHEET: Menu Item, Ingredient ID, Ingredient, Ingredient Category, Amount Used, Recipe Unit, Notes. Joins to INGREDIENT DATABASE on Ingredient ID. Duplicate ingredient rows per menu item were consolidated by hand (e.g. Shark Bite's two Power Tea Flavors rows merged) — the code does NOT dedupe.
- MENU ITEMS: Menu Item, Menu Item Category, Available At, Selling Price, Notes. No stored cost/profit/margin columns — those are computed outputs.

data/fixtures/ (pinned regression oracle for the pytest suite — deliberately frozen, do NOT reconcile with the live Sheet):
- ingredient_database.csv, recipe_sheet.csv, menu_items.csv: the 4 pilot menu items (Peanut Butter Banana, Cold Brew Bliss, Shark Bite, Acai Mixed Berry Bowl) with the exact ingredient amounts, IDs, and costs whose margins were hand-checked against the original Google Sheets calculator. Real numbers — but the Supplier column is blanked (don't want vendor names in a public repo). The fixture Shark Bite still draws 3 fl oz from BEV-ICED_TEA (the bags→fl oz path); the fixture Acai bowl bakes 4 toppings into its recipe.
- expected_ingredient_costs.csv: Menu Item, Ingredient ID, Expected Ingredient Cost ($-string) — per-row expected output, computed from unrounded Purchase Cost / Purchase Size.
- expected_margins.csv: Menu Item, Expected Total Ingredient Cost, Expected Gross Profit, Expected Margin %, Expected Food Cost ($/%-strings, display-rounded — pipeline tests assert with ~1-cent / 0.01-point tolerance). Still carries Expected Margin % though the report doesn't surface it.
- test_calculator.py has a couple of inline ingredient-DB DataFrames / cost literals mirroring these fixture values; if a fixture number ever changes, those need updating too.

Key architecture decision: The cost/profit/margin/food-cost columns (previously hand-calculated in Sheets) are computed outputs, not inputs — the engine recomputes Cost Per Recipe Unit from Purchase Cost / Purchase Size (rather than trusting the pre-filled column, which goes stale when prices change), multiplies by Amount Used from the recipe sheet, and derives everything else, so updating one ingredient price cascades everywhere automatically. Those columns have now been deleted from menu_items.csv and recipe_sheet.csv entirely; the reference values for comparison live only in /data/fixtures/expected_*.csv.

Bowl toppings (was a modeling gap, now handled by data): the 7 Beach Bowls sell at $13.90 "includes any 4 toppings" but their recipe rows had no toppings, so served-bowl cost was undercounted and margin looked artificially high. Fix: every Beach Bowl now carries 4 "representative topping" rows in RECIPE SHEET — FSH-STRAWBERRIES 1.5 oz, FSH-BLUEBERRIES 1 oz, FSH-BANANAS 2 oz, SPR-PEANUT_BUTTER 1 oz (the owner's stated standard set; portions reuse the shop's own standalone "Topping:" menu-item sizes, two of which are noted "matches pilot Acai bowl"). Notes column on each: "representative topping - bowls include any 4 and this is the standard set". Adds ~$0.71 cost / ~5 food-cost points per bowl. No double-count: the $13.90 price already includes toppings (revenue side); only the cost side was missing, and the standalone "Topping:" menu items are separate products, not shared rows. It's an assumption — every bowl is costed as if served with this exact set — but far better than $0, and the standard way food-cost sheets handle customizable items. Applied via normal ingredient lines, no special-case code. Lives in the live Google Sheet RECIPE SHEET tab (28 rows, one per bowl x topping — the sheet has 431 recipe rows). Not reflected in data/fixtures/ (whose recipe_sheet is only the 4 pilot items; the fixture Acai bowl already bakes toppings into its recipe).

Unit conversion notes (in cost_per_recipe_unit):
- lbs → oz uses factor 16 (standard unit conversion) — the workhorse conversion; used by all the bulk lbs-purchased items
- bags → fl oz uses factor 16.88 (Row and Ride's estimated fl oz yield per tea bag — a business assumption, NOT a universal conversion). Only exercised by data/fixtures/ + test_cost_per_recipe_unit_iced_tea now — the live sheet tracks Brewed Tea (PRP-BREWED_TEA) as its own prepared ingredient with a hand-entered batch cost, so nothing in the live RECIPE SHEET hits this branch. Keep it for the regression fixtures.
- everything else falls through to factor 1 (oz→oz, fl oz→fl oz, each→each, ml→ml, cubes→cubes). lbs→oz and the fixture-only bags→fl oz are the ONLY real conversions — every other row is entered with Purchase Unit == Recipe Unit.
- FIXED (was a data-entry landmine): Coconut Cubes now has Purchase Unit "cubes" and Recipe Unit "cubes" matching exactly, so it hits the factor-1 path on purpose instead of by accident.

Missing-data policy: When cost data is blank (NaN), cost_per_recipe_unit returns None. The None check happens ONCE, in the glue function — downstream math functions stay dumb and do not each check for None. Missing ingredients (unmatched Ingredient ID, or None cost) are flagged and surfaced in the UI, never silently skipped or treated as $0.00 (which would make margins look artificially good). The live sheet currently has no blank rows, so this path guards newly-added-but-unpriced ingredients and mistyped IDs.

Structure:
row_and_ride_dashboard/
├── data/
│   ├── README.md      # "app reads the live Sheet; data/*.csv is gitignored"
│   └── fixtures/      # frozen 4-item pilot inputs + expected_*.csv oracle (real numbers, Supplier blanked)
├── src/
│   ├── calculator.py  # pure functions: cost lookup, margin math
│   └── data_loader.py # CSV/Sheet loading, cleaning, validation
├── app.py             # Streamlit UI — reads the Google Sheet, renders the margin report
├── .streamlit/
│   └── secrets.toml.example  # service-account key template (real one gitignored)
├── tests/
│   ├── test_calculator.py  # pytest: unit tests + end-to-end pipeline tests vs data/fixtures
│   └── test_data_loader.py # pytest: strip_currency/_parse_currency_column/_validate_columns + load_* vs data/fixtures
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
- load_menu_items(source) -> pd.DataFrame — validates {Menu Item, Menu Item Category, Selling Price}, cleans Selling Price. (Menu Item Category added to the required set because build_margin_report reads it — was a raw KeyError otherwise.)
- (removed) google_sheet_csv_url — the old public-gviz-export URL builder; deleted with its test when app.py moved to a service account. If a gviz path is ever revived: the export URL needs &headers=1 or gviz mis-detects the header-row count on a large tab (collapses column A into one giant row-1 cell → _validate_columns fails).
- `source` can be a local path, a Streamlit-uploaded file object, or a URL string — pd.read_csv handles all three the same way.
- Design landed on one function per CSV + shared strip_currency/_parse_currency_column/_validate_columns helpers (the open question from before).

DONE — end-to-end pipeline tests, in test_calculator.py, exercising data_loader.py + calculator.py together against /data/fixtures:
- test_pipeline_ingredient_costs_all_menu_items — loads /data/fixtures/{ingredient_database,recipe_sheet}.csv through data_loader.py, runs all 4 pilot menu items through build_ingredient_costs, and checks each cost against expected_ingredient_costs.csv (parsed via strip_currency). build_ingredient_costs returns bare costs with no Ingredient ID attached, so both sides are sorted by ["Menu Item", "Ingredient ID"] before comparing — an explicit alignment, not a reliance on the two fixture files happening to list ingredients in the same order.
- test_pipeline_margins_all_menu_items — additionally loads menu_items.csv, chains the full pipeline (build_ingredient_costs → calculate_total_ingredient_cost → calculate_gross_profit → calculate_margin_percent → calculate_food_cost) per menu item, and checks totals against expected_margins.csv with ~1-cent/0.01-point tolerance (display-rounded, not exact). Still asserts Margin % since the fixture column exists — the not-in-the-report decision only applies to build_margin_report's output.
- test_build_margin_report_all_menu_items — loads the three fixture CSVs, calls build_margin_report once, and asserts row count + Total Ingredient Cost / Gross Profit / Food Cost / Missing Ingredients per menu item against expected_margins.csv (same tolerance). Margin % is loaded but not asserted (not a report column). Largely supersedes the inline loop in test_pipeline_margins_all_menu_items.

IN PROGRESS — app.py (Streamlit MVP). Run with `python -m streamlit run app.py` (python -m for the same PATH/venv reason as pytest), opens localhost:8501. No upload step — it reads the Google Sheet on load.

DONE (first pass):
- Backend is the Row and Ride margin Google Sheet (SPREADSHEET_ID constant in app.py; tabs in SHEET_TABS), read via a **Google service account** — key JSON in st.secrets["gcp_service_account"] (local .streamlit/secrets.toml, gitignored; Streamlit Cloud → Settings → Secrets). Sheet is Restricted, shared only with the service account's client_email as Viewer. .streamlit/secrets.toml.example is the committed template; requirements.txt has gspread. Google Cloud side: project + Sheets API enabled + service account + JSON key; opening by key means no Drive API / no Drive scope (SHEET_READONLY_SCOPE only).
- _open_workbook() — @st.cache_resource, one gspread.service_account_from_dict auth per session, returns the opened Spreadsheet handle.
- _fetch_sheet() — @st.cache_data(ttl=SHEET_CACHE_TTL=600s), no args. For each tab: worksheet.get_all_values() → trim (Google's default grid is 26 cols wide, padded ""; cut trailing empty header cols + fully-blank rows) → csv.writer into a StringIO → the existing load_* (reused unchanged — they just need a CSV source). Returns (idb, rs, mi, fetched_at); exceptions propagate (not cached). No cache-buster needed — the Sheets API returns live data, unlike the gviz export. fetched_at is datetime.now(SHOP_TZ=America/New_York) so the "Loaded —" caption reads in shop time, not the UTC that Streamlit Cloud servers run in (requirements.txt carries tzdata for this).
- load_source_data() — still the single seam. Sidebar: "Open the sheet" link_button + "Refresh from sheet" (clears both _fetch_sheet and _open_workbook, then st.rerun) + "Loaded — <time>". Targeted st.error + st.stop for: (KeyError | StreamlitSecretNotFoundError) = no creds, gspread SpreadsheetNotFound = sheet not shared with the SA, WorksheetNotFound = renamed/missing tab, APIError = Sheets API not enabled / quota, ValueError = bad data in the sheet. NOTE: this header/title block renders after load_source_data(), so a creds/permission error shows just the sidebar message with no page title.
- Margin report section: build_margin_report → st.dataframe with column_config (Selling Price / Total Ingredient Cost / Gross Profit as $%.2f, Food Cost as "%.1f%%" — literal percent, value is already in points). Grid height is computed to show every row (no inner scroll) up to a 900px cap.
- Toppings hidden from the report: a plain `report = report[report["Category"] != "Topping"]` right after build_margin_report (~20 of 66 rows, sold as upcharges not standalone items). No UI control — a sidebar multiselect was tried and pulled (visually noisy, and st.dataframe already has built-in column filtering). Applied before the incomplete mask so the warning / shading / auto-height follow the filtered set.
- Page order under the "Margin Report" header: "Quick reads" subheader (stats) → st.divider → "All items" subheader (incomplete warning + full table). report/incomplete/solid are computed once at the top and both sections read them.
- "Quick reads": a 4-tile st.metric row (avg food cost %, count over FOOD_COST_WATCH_PCT=35, avg gross profit, best-margin item — its food-cost % rides in the metric's delta slot with delta_color/delta_arrow="off" so it's grey/no-arrow and sits tight under the name) and three top-5 st.dataframes in st.columns(3) (highest food cost %, highest gross profit, highest ingredient cost). All computed on `solid = report[~incomplete]` — incomplete rows have understated cost and would fake their way to the top of the low-food-cost / high-profit lists. Stat tiles not charts (dataviz skill: "single headline" → not a chart), so no palette work. The over-35% tile compares `Food Cost.round(1) >= FOOD_COST_WATCH_PCT` (not the raw value) so a row the table displays as "35.0%" — e.g. Cold Brew Bliss at a true 34.97% — is counted in the tile too.
- Missing-ingredient handling: incomplete mask = Missing Ingredients list non-empty; st.warning above the table listing affected menu items + unpriced IDs; amber Styler row wash (rgba(255,171,0,0.18), theme-safe) on incomplete rows; Missing Ingredients rendered as comma-joined string ("" not []) via a display copy.
- requirements.txt now has streamlit.
- Branding: two assets/ files — row-and-ride-logo-circle.png (ICON: st.logo sidebar badge + browser-tab favicon via page_icon) and boat-house-logo.png (HEADER: wordmark at far right of the title row). Both guarded by Path.exists() so the app runs without them; swap a Path for a URL string to use a hosted image. Layout quirks handled with a CSS <style> block: st.logo enlarged past size="large" (height 3rem) and padded off the window top; the header wordmark is an <img> inlined as a base64 data URI (st.markdown HTML can't read assets/), position:absolute bottom-anchored (the <h1> plus a muted <p> row-count line share the block, so the logo bottom sits level with the count line) and pinned right so growing it pushes *up* into headroom, not down onto the content below. This header block renders AFTER load_source_data() because the count line needs the loaded DataFrames — so a load error shows just the sidebar message with no title. Two coupled knobs: img height:11rem and [data-testid="stMainBlockContainer"] padding-top (~8.5rem) — every +1rem of logo needs ~+1rem more padding-top or Streamlit's fixed top bar clips the logo. Currently tuned and looks right; leave the two values in sync if changing.

WHAT'S LEFT:
To make it usable:
DONE since first pass:
- /data upload flow replaced by the Google Sheet backend (above).
- Menu Item Category now in load_menu_items' required set (#3).
- Non-ValueError failures: load_source_data has targeted st.error branches for every credential / permission / tab / API failure mode (see the load_source_data bullet above) — no tracebacks (#4).
- Auth switched from "anyone with the link" gviz export to a service account (for Streamlit Cloud deploy) — sheet is now Restricted.
- Bowl-undercount (#2): fixed in the data, not the code — 28 representative topping rows added to the live Google Sheet RECIPE SHEET tab (see "Bowl toppings" note up top). No local CSV involved.
Polish:
- README.md is empty — for the resume-project angle it needs what/why/screenshot/run steps.
- No tests around the display layer. Streamlit is awkward to test, but the missing-ingredient formatting (list → comma string, incomplete mask) could move to a small helper with a unit test.
- The old module-level st.success("Loaded N…") banner is now a muted <p> row-count line folded into the header block (N ingredients · N recipe rows · N menu items).

Stretch goal: sidebar widget to override one ingredient's Purchase Cost and watch food cost % recompute (demonstrates the cascade). Food-cost threshold highlighting (flag items above a target %). Further stretch: in-app persistent editing saved back to CSV.

Conventions:
- Test-first: write the pytest test against known pilot CSV values before implementing the function body
- Docstrings carry data-source context (which CSV each param comes from, or which function computed it) rather than encoding it in function name prefixes
- Run tests with `python -m pytest` (not bare `pytest`) — PATH/venv resolution issue
- Learning-focused project: prefer being walked through reasoning and design decisions over being handed complete solutions