# data/

The running app reads its data from the **live Row and Ride margin Google
Sheet** (three tabs: INGREDIENT DATABASE, RECIPE SHEET, MENU ITEMS), pulled
through a service account (see `app.py` / `src/data_loader.py`). Nothing in this
folder is loaded at runtime.

## `fixtures/`

Frozen input CSVs + expected-output CSVs for the pytest suite
(`tests/test_calculator.py`, `tests/test_data_loader.py`). Four pilot menu items
(Peanut Butter Banana, Cold Brew Bliss, Shark Bite, Acai Mixed Berry Bowl) with
the exact ingredient amounts, IDs, and costs whose margins were hand-checked
against the original Google Sheets margin calculator this project replaces.
The Supplier column is intentionally blank.
