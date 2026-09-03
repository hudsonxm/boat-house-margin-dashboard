"""Boat House margin dashboard — Streamlit UI.

Reads the three tabs of the Boat House margin Google Sheet (INGREDIENT
DATABASE, RECIPE SHEET, MENU ITEMS) and shows a per-menu-item margin report.
The shop edits the sheet; the app picks the changes up on its own (cached, with
a manual "Refresh from sheet" button).

All knowledge of *where* the data comes from is confined to load_source_data()
below. It returns three cleaned DataFrames; every section after it works with
DataFrames only, so the source could be swapped (back to CSV upload, or to a
service-account API) inside that one function without touching anything else.
"""

import base64
import csv
import io
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from src.calculator import build_margin_report
from src.data_loader import (
    load_ingredient_database,
    load_recipe_sheet,
    load_menu_items,
)

# Backend: the Boat House margin workbook. Read through a Google service
# account whose key JSON lives in st.secrets["gcp_service_account"] (local
# .streamlit/secrets.toml + Streamlit Cloud Secrets); the sheet itself stays
# Restricted, shared only with that account's client_email as Viewer.
SPREADSHEET_ID = "1t1L2AvixDlgnFTuZhUqucrXwGY31kvNuUD05slbRelU"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
SHEET_TABS = ("INGREDIENT DATABASE", "RECIPE SHEET", "MENU ITEMS")  # exact tab names
SHEET_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
SHEET_CACHE_TTL = 600  # seconds before an untouched app re-pulls the sheet

# Streamlit Cloud runs in UTC; stamp the "Loaded —" time in the shop's zone
# instead (handles EST/EDT automatically). Needs the tzdata package on Windows.
SHOP_TZ = ZoneInfo("America/New_York")

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
    page_title="Boat House Margins",
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


@st.cache_resource(show_spinner=False)
def _open_workbook():
    """Authorize a gspread client from st.secrets and open the workbook once per
    session (one auth handshake, reused across reruns). Raises KeyError if the
    `gcp_service_account` secret is absent; gspread auth/permission errors bubble
    up to load_source_data()."""
    client = gspread.service_account_from_dict(
        dict(st.secrets["gcp_service_account"]),
        scopes=[SHEET_READONLY_SCOPE],
    )
    return client.open_by_key(SPREADSHEET_ID)


@st.cache_data(ttl=SHEET_CACHE_TTL, show_spinner="Loading data from the Google Sheet…")
def _fetch_sheet():
    """Read + clean + validate all three tabs via the service account. Cached, so
    reruns don't refetch; expires after SHEET_CACHE_TTL, or clear it with the
    "Refresh from sheet" button. Each worksheet's cell grid is re-serialized to
    CSV in memory so the existing load_* functions (which expect a CSV source)
    are reused unchanged. Returns (idb, recipe, menu, fetched_at); exceptions
    propagate to load_source_data() (a cache miss re-runs this, so a transient
    failure isn't stuck in the cache)."""
    workbook = _open_workbook()
    loaders = (load_ingredient_database, load_recipe_sheet, load_menu_items)

    frames = []
    for tab, loader in zip(SHEET_TABS, loaders):
        rows = workbook.worksheet(tab).get_all_values()
        # get_all_values() returns the sheet's whole default grid (26 cols wide,
        # padded with ""). Trim trailing empty header columns, then drop fully
        # blank rows, so the DataFrame isn't carrying "Unnamed" columns / NaN rows.
        header = list(rows[0])
        while header and not header[-1].strip():
            header.pop()
        width = len(header)
        grid = [header] + [
            row[:width] for row in rows[1:] if any(cell.strip() for cell in row[:width])
        ]

        buffer = io.StringIO()
        csv.writer(buffer).writerows(grid)
        buffer.seek(0)
        frames.append(loader(buffer))

    return (*frames, datetime.now(SHOP_TZ))


def load_source_data():
    """Read the Google Sheet and return the three cleaned DataFrames.

    Returns (ingredient_database, recipe_sheet, menu_items). Halts the script
    with st.stop() and a targeted message on: missing credentials (KeyError),
    the sheet not shared with the service account (SpreadsheetNotFound), a
    renamed/missing tab (WorksheetNotFound), a Sheets API problem (APIError), or
    bad data in the sheet (ValueError) — so nothing downstream runs on bad data.
    """
    st.sidebar.header("Data source")
    st.sidebar.caption("Live from the Boat House margins Google Sheet.")
    st.sidebar.link_button("Open the sheet", SHEET_EDIT_URL, use_container_width=True)
    if st.sidebar.button("Refresh from sheet", use_container_width=True):
        _fetch_sheet.clear()
        _open_workbook.clear()
        st.rerun()

    try:
        ingredient_database, recipe_sheet, menu_items, fetched_at = _fetch_sheet()
    except (KeyError, StreamlitSecretNotFoundError):
        # KeyError: secrets.toml exists but has no [gcp_service_account] table.
        # StreamlitSecretNotFoundError: no secrets.toml at all.
        st.error(
            "No service-account credentials found. Add the key JSON under "
            "`[gcp_service_account]` in `.streamlit/secrets.toml` locally, and in "
            "the app's **Settings → Secrets** on Streamlit Cloud."
        )
        st.stop()
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(
            "The service account can't open the workbook — share the Google "
            "Sheet (Viewer) with the `client_email` from the key JSON."
        )
        st.stop()
    except gspread.exceptions.WorksheetNotFound as error:
        st.error(
            f"A tab is missing or renamed ({error}). Expected: "
            + ", ".join(SHEET_TABS)
            + "."
        )
        st.stop()
    except gspread.exceptions.APIError as error:
        st.error(
            "Google Sheets API error — check the Sheets API is enabled for the "
            f"service account's project.\n\n{error}"
        )
        st.stop()
    except ValueError as error:
        st.error(f"The Google Sheet has a data problem: {error}")
        st.stop()

    st.sidebar.success(f"Loaded — {fetched_at:%b %d, %I:%M %p %Z}")
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
            <h1 style="margin:0; padding:0;">Boat House Margins Dashboard</h1>
            <p style="margin:0.25rem 0 0; font-size:0.875rem; opacity:0.6;">{_counts}</p>
            <img src="data:image/png;base64,{_header_uri}"
                 style="position:absolute; right:0; bottom:0; height:11rem;
                        width:auto; pointer-events:none;">
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.title("Boat House Margins Dashboard")
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
    best_name = str(best["Menu Item"])
    # Only the item name (the metric *value*) scales — a long one like "Peanut
    # Butter Banana & Honey" would otherwise ellipsis-truncate. Taper past ~16
    # chars to a readable floor, then let it wrap. The label, the delta line, and
    # the tile's top edge are untouched, so it stays row-aligned with the others.
    _name_rem = 1.75 if len(best_name) <= 16 else round(max(1.0, 1.75 - (len(best_name) - 16) * 0.06), 2)
    with k4.container(key="best-margin"):
        st.metric(
            "Best margin",
            best_name,
            f"{best['Food Cost']:.1f}% food cost",
            delta_color="off",
            delta_arrow="off",
        )
    st.markdown(
        "<style>"
        ".st-key-best-margin{margin-top:0 !important;padding-top:0 !important;}"
        f".st-key-best-margin [data-testid='stMetricValue']{{font-size:{_name_rem}rem;"
        "white-space:normal;overflow-wrap:anywhere;}"
        "</style>",
        unsafe_allow_html=True,
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
