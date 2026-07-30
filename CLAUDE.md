Project: Row and Ride Margins Dashboard

Building a Python tool to replace a Google Sheets margin calculator for my mom's smoothie/bowl bar (Row and Ride / Boathouse Nutrition). It's also my resume project for co-op search (rising 2nd year, Northeastern).
Goal: Streamlit dashboard where you upload 3 CSVs (ingredient database, recipe sheet, menu items) and it automatically calculates ingredient cost, gross profit, margin %, and food cost % per menu item — replacing manual spreadsheet math.

Data schema (pilot CSVs already exist in /data):
ingredient_database.csv: Ingredient, Category, Purchase Size, Purchase Unit, Purchase Cost, Cost Per Recipe Unit, Recipe Unit, Supplier, Last Updated, Notes. Full database is sparse (many blank cost rows) — pilot subset has complete data for the 4 test menu items.
recipe_sheet.csv: Menu Item, Ingredient, Ingredient Category, Amount Used, Recipe Unit, Ingredient Cost, Notes. Note: some menu items have duplicate ingredient rows (e.g. same ingredient added twice) that need to be summed, not overwritten.
menu_items.csv: Menu Item, Menu Item Category, Selling Price, Total Ingredient Cost, Gross Profit, Margin %, Food Cost, Notes.

Key architecture decision: The cost/profit/margin/food-cost columns in menu_items.csv and the Ingredient Cost column in recipe_sheet.csv were previously hand-calculated in Sheets. In the Python tool these become computed outputs, not inputs — the engine looks up Cost Per Recipe Unit from the ingredient database, multiplies by Amount Used from the recipe sheet, and derives everything else, so updating one ingredient price cascades everywhere automatically.

Planned structure:
row_and_ride_dashboard/
├── data/              # pilot CSVs for local dev
├── src/
│   ├── calculator.py  # pure functions: cost lookup, margin math (DataFrames, no classes yet)
│   └── data_loader.py # CSV validation/cleaning, handles missing-cost ingredients gracefully
├── app.py             # Streamlit UI
├── tests/
│   └── test_calculator.py  # pytest, validated against the 4 known pilot menu items
├── requirements.txt
└── README.md

Current step: Writing calculator.py first, tested against the 4 pilot menu items (whose correct margins are already known from the old hand-calculated sheet), before touching any UI code.
Plan after MVP: Once upload-and-calculate works, expand to the full sparse ingredient database, then add in-app persistent editing (add/edit ingredients & recipes through the UI, saved back to CSV) as a stretch goal.