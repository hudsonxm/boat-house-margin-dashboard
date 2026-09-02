"""Row and Ride margin dashboard — Streamlit UI.

Reads the three tabs of the Row and Ride margin Google Sheet (INGREDIENT
DATABASE, RECIPE SHEET, MENU ITEMS) and shows a per-menu-item margin report.
The shop edits the sheet; the app picks the changes up on its own (cached, with
a manual "Refresh from sheet" button).

All knowledge of *where* the data comes from is confined to load_source_data()
below. It returns three cleaned DataFrames; every section after it works with
DataFrames only, so the source could be swapped (back to CSV upload, or to a
service-account API) inside that one function without touching anything else.
"""

import base64
import time
from datetime import datetime
from pathlib import Path
from urllib.error import URLError

import streamlit as st
from pandas.errors import ParserError

from src.calculator import build_margin_report
from src.data_loader import (
    google_sheet_csv_url,
    load_ingredient_database,
    load_recipe_sheet,
    load_menu_items,
)

# Backend: the Row and Ride margin workbook, shared "Anyone with the link ->
# Viewer" so its per-tab CSV export is readable without credentials. Keys are
# the tab names exactly as they appear in the sheet.
SPREADSHEET_ID = "1t1L2AvixDlgnFTuZhUqucrXwGY31kvNuUD05slbRelU"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
SHEET_CACHE_TTL = 600  # seconds before an untouched app re-pulls the sheet

# Food cost above this (%) is the "keep an eye on it" line — ~30% is the
# rule-of-thumb target for a juice/smoothie bar; 35% is where margin starts to hurt.
FOOD_COST_WATCH_PCT = 35

# Brand marks (assets/). ICON is the circular badge — the sidebar logo (above
# "Data source") and the browser-tab favicon. HEADER is the full wordmark shown
# at the far right of the title row. Each no-ops gracefully if its file is
# missing, so the app runs either way; swap a Path for a URL string to use a
# hosted image.
ICON = Path(__file__).parent / "assets" / "row-and-ride-logo-circle.png"
HEADER = Path(__file__).parent / "assets" / "boat-house-logo.png"
_icon = str(ICON) if ICON.exists() else None
_header = str(HEADER) if HEADER.exists() else None

st.set_page_config(
    page_title="Row and Ride Margins",
    page_icon=_icon,
    layout="wide",
)

# st.logo() maxes out at size="large" and sits flush against the window top —
# bump its size and pad it down off the edge with CSS.
st.markdown(
    """
    <style>
    [data-testid="stSidebarHeader"] { padding-top: 2.5rem; }
    [data-testid="stLogo"], [data-testid="stSidebarLogo"] {
        height: 3rem !important;
        max-width: 100% !important;
    }
    /* Headroom above the title so the bottom-anchored header logo has somewhere
       to grow into without being clipped by Streamlit's fixed top bar. */
    [data-testid="stMainBlockContainer"] { padding-top: 8.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if _icon:
    st.logo(_icon, size="large")  # top-left, above the sidebar "Data source" header

# The page header (title + row-count line + wordmark logo) renders after
# load_source_data() below — the count line needs the loaded DataFrames, and the
# logo is bottom-aligned to that line, so all three have to be in one block.


# --------------------------------------------------------------------------- #
# Data loading — the only section that knows the data lives in a Google Sheet. #
# Swap the body of load_source_data() to change where the DataFrames come from.#
# --------------------------------------------------------------------------- #


@st.cache_data(ttl=SHEET_CACHE_TTL, show_spinner="Loading data from the Google Sheet…")
def _fetch_sheet(spreadsheet_id: str):
    """Pull + clean + validate all three tabs. Cached, so reruns don't refetch;
    the cache key is spreadsheet_id and it expires after SHEET_CACHE_TTL. Returns
    (ingredient_database, recipe_sheet, menu_items, fetched_at). Exceptions
    propagate to load_source_data() to be shown in the UI (a cache miss re-runs
    this, so a transient network error isn't stuck in the cache)."""
    # Google caches each tab's CSV export for a few minutes; a per-fetch nonce
    # sidesteps that so an edit in the sheet is visible as soon as this reruns
    # (on the SHEET_CACHE_TTL timer, or immediately via "Refresh from sheet").
    bust = f"&_cb={int(time.time())}"

    ingredient_database = load_ingredient_database(
        google_sheet_csv_url(spreadsheet_id, "INGREDIENT DATABASE") + bust
    )
    recipe_sheet = load_recipe_sheet(
        google_sheet_csv_url(spreadsheet_id, "RECIPE SHEET") + bust
    )
    menu_items = load_menu_items(
        google_sheet_csv_url(spreadsheet_id, "MENU ITEMS") + bust
    )
    return ingredient_database, recipe_sheet, menu_items, datetime.now()


def load_source_data():
    """Read the Google Sheet and return the three cleaned DataFrames.

    Returns (ingredient_database, recipe_sheet, menu_items). On a data problem in
    the sheet (missing column, malformed currency cell → ValueError) or an
    unreachable / wrongly-shared sheet (URLError / ParserError), it shows the
    problem and halts the script with st.stop() so nothing downstream runs on
    bad data.
    """
    st.sidebar.header("Data source")
    st.sidebar.caption("Live from the Row and Ride margins Google Sheet.")
    st.sidebar.link_button("Open the sheet", SHEET_EDIT_URL, use_container_width=True)
    if st.sidebar.button("Refresh from sheet", use_container_width=True):
        _fetch_sheet.clear()
        st.rerun()

    try:
        ingredient_database, recipe_sheet, menu_items, fetched_at = _fetch_sheet(
            SPREADSHEET_ID
        )
    except ValueError as error:
        st.error(f"The Google Sheet has a data problem: {error}")
        st.stop()
    except (URLError, ParserError) as error:
        st.error(
            "Couldn't read the Google Sheet. Check that it's shared as "
            "“Anyone with the link → Viewer” and that you're online.\n\n"
            f"{error}"
        )
        st.stop()

    st.sidebar.success(f"Loaded — {fetched_at:%b %d, %I:%M %p}")
    return ingredient_database, recipe_sheet, menu_items


ingredient_database, recipe_sheet, menu_items = load_source_data()

# --------------------------------------------------------------------------- #
# Everything below this line works with DataFrames only.                      #
# --------------------------------------------------------------------------- #

_counts = (
    f"{len(ingredient_database)} ingredients · "
    f"{len(recipe_sheet)} recipe rows · {len(menu_items)} menu items"
)

if _header:
    # One block so the wordmark can bottom-align to the count line: the <h1> +
    # <p> set the height, the <img> is absolutely positioned (right / bottom:0)
    # so growing its height reaches *up* into the padding-top headroom, never
    # down onto the divider. Image inlined as a data URI — st.markdown HTML
    # can't read the assets/ path.
    _header_uri = base64.b64encode(Path(_header).read_bytes()).decode()
    st.markdown(
        f"""
        <div style="position:relative; margin:0.5rem 0 1rem;">
            <h1 style="margin:0; padding:0;">Row and Ride Margins Dashboard</h1>
            <p style="margin:0.25rem 0 0; font-size:0.875rem; opacity:0.6;">{_counts}</p>
            <img src="data:image/png;base64,{_header_uri}"
                 style="position:absolute; right:0; bottom:0; height:11rem;
                        width:auto; pointer-events:none;">
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.title("Row and Ride Margins Dashboard")
    st.caption(_counts)

st.divider()


# --------------------------------------------------------------------------- #
# Margin report                                                              #
# --------------------------------------------------------------------------- #



report = build_margin_report(menu_items, recipe_sheet, ingredient_database)

# Toppings are add-on items (~20 of 66 rows) sold as upcharges, not standalone
# menu items — drop them from the margin view.
report = report[report["Category"] != "Topping"]

# A row is "incomplete" when build_margin_report couldn't price one or more of
# its ingredients. Its cost columns are then a partial sum (missing ingredients
# left out entirely), so the true cost is higher and the margin lower than shown.
incomplete = report["Missing Ingredients"].apply(len) > 0


# --------------------------------------------------------------------------- #
# Overview — headline stats + top-5 lists, shown above the full table.     #
# Computed on fully-priced items only: an incomplete row's cost is understated #
# so it would fake its way to the top of the gross-profit / low-food-cost lists.#
# --------------------------------------------------------------------------- #

st.subheader("Overview")

solid = report[~incomplete]

if solid.empty:
    st.caption("Nothing to summarize — every shown item has an unpriced ingredient.")
else:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Avg. food cost %", f"{solid['Food Cost'].mean():.1f}%")
    k2.metric(
        f"Items over {FOOD_COST_WATCH_PCT}%",
        # Compare the value as displayed (1 dp) so a row the table shows as
        # "35.0%" is counted here too — the raw number can be 34.97.
        int((solid["Food Cost"].round(1) >= FOOD_COST_WATCH_PCT).sum()),
        help=f"Food cost at {FOOD_COST_WATCH_PCT}% or higher, worth a recipe or price look.",
    )
    k3.metric("Avg. gross profit", f"${solid['Gross Profit'].mean():.2f}")
    best = solid.loc[solid["Food Cost"].idxmin()]
    # The food-cost % rides in the metric's delta slot (grey, no arrow) so it
    # sits tight under the item name instead of a full row's gap below it.
    k4.metric(
        "Best margin",
        str(best["Menu Item"]),
        f"{best['Food Cost']:.1f}% food cost",
        delta_color="off",
        delta_arrow="off",
    )

    def _top5(column: str, value_label: str, fmt):
        out = solid.nlargest(5, column)[["Menu Item", column]].copy()
        out[column] = out[column].map(fmt)
        return out.rename(columns={"Menu Item": "Item", column: value_label})

    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("Highest food cost %")
        st.dataframe(
            _top5("Food Cost", "Food cost", lambda v: f"{v:.1f}%"),
            hide_index=True, use_container_width=True,
        )
    with c2:
        st.caption("Highest gross profit")
        st.dataframe(
            _top5("Gross Profit", "Gross profit", lambda v: f"${v:.2f}"),
            hide_index=True, use_container_width=True,
        )
    with c3:
        st.caption("Highest ingredient cost")
        st.dataframe(
            _top5("Total Ingredient Cost", "Ingredient cost", lambda v: f"${v:.2f}"),
            hide_index=True, use_container_width=True,
        )

st.divider()


# --------------------------------------------------------------------------- #
# Full table.                                                                 #
# --------------------------------------------------------------------------- #

st.subheader("All items")

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


# Size the grid to show every row at once instead of Streamlit's default
# ~10-row scroll window: 35px per data row + 35px header + 3px border.
full_height = (len(display) + 1) * 35 + 3

# Food Cost is already in percentage points (e.g. 21.94 -> "21.9%"), so the
# format string appends a literal "%" rather than using a percent NumberColumn
# (which would multiply by 100).
st.dataframe(
    display.style.apply(_shade_incomplete_rows, axis=1),
    hide_index=True,
    use_container_width=True,
    height=min(full_height, 900),
    column_config={
        "Selling Price": st.column_config.NumberColumn("Selling Price", format="$%.2f"),
        "Total Ingredient Cost": st.column_config.NumberColumn(
            "Total Ingredient Cost", format="$%.2f"
        ),
        "Gross Profit": st.column_config.NumberColumn("Gross Profit", format="$%.2f"),
        "Food Cost": st.column_config.NumberColumn("Food Cost", format="%.1f%%"),
    },
)
