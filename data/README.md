# data/

The running app reads its data from the **live Row and Ride margin Google
Sheet** (three tabs: INGREDIENT DATABASE, RECIPE SHEET, MENU ITEMS), pulled
through a service account (see `app.py` / `src/data_loader.py`). Nothing in this
folder is loaded at runtime.

## `fixtures/`

Frozen input CSVs and expected-output CSVs for the pytest suite
(`tests/test_calculator.py`, `tests/test_data_loader.py`). Four pilot menu items
(Peanut Butter Banana, Cold Brew Bliss, Shark Bite, Acai Mixed Berry Bowl) with
the exact ingredient amounts, IDs, and costs whose margins were hand-checked
against the original Google Sheets margin calculator this project replaces.

These are a July 2026 snapshot, kept unchanged so the tests always answer the
same question: given these exact inputs, does the code still produce the same
outputs? They are not current pricing and are never updated when real costs
change. The Supplier column is intentionally blank.