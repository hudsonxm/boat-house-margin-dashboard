"""Row and Ride margin dashboard — Streamlit UI.

Upload the three CSVs (ingredient database, recipe sheet, menu items) and get a
per-menu-item margin report.

All knowledge of *where* the data comes from is confined to load_source_data()
below. It returns three cleaned DataFrames; every section after it works with
DataFrames only, so another source (e.g. a Google Sheets import) can be added
inside that one function without touching the report or display code.
"""

import streamlit as st

from src.calculator import build_margin_report
from src.data_loader import (
    load_ingredient_database,
    load_recipe_sheet,
    load_menu_items,
)

st.set_page_config(page_title="Row and Ride Margins", layout="wide")
st.title("Row and Ride Margin Dashboard")


# --------------------------------------------------------------------------- #
# Data loading — the only section that knows the data is CSV uploads.         #
# Swap the body of load_source_data() to add another source later.            #
# --------------------------------------------------------------------------- #


def load_source_data():
    """Render the sidebar uploaders and return the three cleaned DataFrames.

    Returns (ingredient_database, recipe_sheet, menu_items) once all three files
    are uploaded and parse cleanly. Until then — or if any loader raises
    ValueError (missing required column, malformed currency cell) — it reports
    the situation and halts the script with st.stop(), so nothing downstream
    ever runs on partial data.
    """
    st.sidebar.header("Data source")
    st.sidebar.caption("Upload the three CSVs exported from the margin spreadsheet.")

    # (label, uploaded file, loader) — one entry per CSV.
    sources = [
        (
            "Ingredient database",
            st.sidebar.file_uploader(
                "Ingredient database CSV", type="csv", key="ingredient_database"
            ),
            load_ingredient_database,
        ),
        (
            "Recipe sheet",
            st.sidebar.file_uploader(
                "Recipe sheet CSV", type="csv", key="recipe_sheet"
            ),
            load_recipe_sheet,
        ),
        (
            "Menu items",
            st.sidebar.file_uploader("Menu items CSV", type="csv", key="menu_items"),
            load_menu_items,
        ),
    ]

    not_yet_uploaded = [label for label, file, _ in sources if file is None]
    if not_yet_uploaded:
        st.info("Waiting on: " + ", ".join(not_yet_uploaded) + ".")
        st.stop()

    frames = []
    for label, file, loader in sources:
        try:
            frames.append(loader(file))
        except ValueError as error:
            st.error(f"**{label}** could not be loaded: {error}")
            st.stop()

    st.sidebar.success("All three CSVs loaded.")
    return tuple(frames)


ingredient_database, recipe_sheet, menu_items = load_source_data()

# --------------------------------------------------------------------------- #
# Everything below this line works with DataFrames only.                      #
# --------------------------------------------------------------------------- #

st.success(
    f"Loaded {len(ingredient_database)} ingredients, "
    f"{len(recipe_sheet)} recipe rows, and {len(menu_items)} menu items."
)


# --------------------------------------------------------------------------- #
# Margin report                                                              #
# --------------------------------------------------------------------------- #

st.header("Margin report")

report = build_margin_report(menu_items, recipe_sheet, ingredient_database)

# A row is "incomplete" when build_margin_report couldn't price one or more of
# its ingredients. Its cost columns are then a partial sum (missing ingredients
# left out entirely), so the true cost is higher and the margin lower than shown.
incomplete = report["Missing Ingredients"].apply(len) > 0

if incomplete.any():
    affected = "\n".join(
        f"- **{row['Menu Item']}**: {', '.join(row['Missing Ingredients'])}"
        for _, row in report[incomplete].iterrows()
    )
    st.warning(
        f"{int(incomplete.sum())} menu item(s) have ingredients that couldn't be "
        "priced. Their Total Ingredient Cost, Gross Profit and Food Cost below are "
        "**partial** — the missing ingredients are left out, so the real cost is "
        "higher than shown:\n\n" + affected
    )

# Display copy: turn the Missing Ingredients list into a reader-friendly
# comma-joined string ("" when nothing is missing, never "[]").
display = report.copy()
display["Missing Ingredients"] = display["Missing Ingredients"].apply(", ".join)


def _shade_incomplete_rows(row):
    """Amber wash across any row whose numbers are a partial sum, so a partial
    figure never sits in the table looking as solid as a complete one."""
    wash = "background-color: rgba(255, 171, 0, 0.18)" if row["Missing Ingredients"] else ""
    return [wash] * len(row)


# Food Cost is already in percentage points (e.g. 21.94 -> "21.9%"), so the
# format string appends a literal "%" rather than using a percent NumberColumn
# (which would multiply by 100).
st.dataframe(
    display.style.apply(_shade_incomplete_rows, axis=1),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Selling Price": st.column_config.NumberColumn("Selling Price", format="$%.2f"),
        "Total Ingredient Cost": st.column_config.NumberColumn(
            "Total Ingredient Cost", format="$%.2f"
        ),
        "Gross Profit": st.column_config.NumberColumn("Gross Profit", format="$%.2f"),
        "Food Cost": st.column_config.NumberColumn("Food Cost", format="%.1f%%"),
    },
)
