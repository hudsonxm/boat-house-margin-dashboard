from urllib.parse import quote

import pandas as pd


def google_sheet_csv_url(spreadsheet_id: str, sheet_name: str) -> str:
    """
    Builds the CSV-export URL for one tab of a Google Sheet.

    spreadsheet_id is the long id from the sheet's URL; sheet_name is the tab's
    display name (e.g. "INGREDIENT DATABASE"). The workbook must be shared
    "Anyone with the link -> Viewer" for this to be readable without credentials.
    The result is a plain URL string — pass it straight to any load_* function
    below, exactly like a local path.

    headers=1 is required, not optional: without it the CSV endpoint auto-detects
    the header-row count and, once a tab grows past a certain size, guesses wrong
    — collapsing column A into a single giant row-1 cell and dropping the real
    header, which then trips _validate_columns. Pinning it to 1 disables that
    guess.
    """
    return (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        f"/gviz/tq?tqx=out:csv&headers=1&sheet={quote(sheet_name)}"
    )


def strip_currency(series: pd.Series) -> pd.Series:
    """
    Strips currency symbols from a pandas Series of strings and converts to float.
    """
    # astype(str) so numeric columns don't crash the .str accessor. This round-trips
    # NaN through the string "nan" which happens to work in the end (coerced back into NaN).
    cleaned = series.astype(str).str.replace(",", "").str.lstrip("$").str.rstrip("%")
    return pd.to_numeric(cleaned, errors="coerce")


def _parse_currency_column(df: pd.DataFrame, column: str, csv_name: str) -> pd.Series:
    """
    Cleans a currency/percent column to float and raises if any populated cell
    failed to parse (came in with data, went out NaN) - a data-entry typo, not
    a genuine blank. Genuine blanks (NaN in, NaN out) pass through untouched.
    """
    raw = df[column]
    cleaned = strip_currency(raw)

    missing = raw.notna() & cleaned.isna()
    if missing.any():
        bad = raw[missing].to_dict()  # {row index: original value}
        raise ValueError(
            f"{csv_name} could not parse {column} values: {list(bad.values())}"
        )  # TODO: surface as UI warning like missing_ingredients

    return cleaned


def _validate_columns(df: pd.DataFrame, required: set, csv_name: str) -> None:
    missing = sorted(required - set(df.columns))

    if missing:
        raise ValueError(f"Missing required {csv_name} columns: {missing}")


def load_ingredient_database(source) -> pd.DataFrame:
    """
    Loads + cleans + validates ingredient_database.csv; Purchase Cost arrives as $-strings.
    """
    df = pd.read_csv(source)

    _validate_columns(
        df,
        {
            "Ingredient ID",
            "Purchase Size",
            "Purchase Unit",
            "Purchase Cost",
            "Recipe Unit",
        },
        "Ingredient Database",
    )

    df["Purchase Cost"] = _parse_currency_column(
        df, "Purchase Cost", "Ingredient Database"
    )
    return df


def load_recipe_sheet(source) -> pd.DataFrame:
    """
    Loads + validates recipe_sheet.csv; no cleaning necessary.
    """
    df = pd.read_csv(source)

    _validate_columns(df, {"Menu Item", "Ingredient ID", "Amount Used"}, "Recipe Sheet")

    return df


def load_menu_items(source) -> pd.DataFrame:
    """
    Loads + cleans + validates menu_items.csv; Selling Price arrives as $-strings.
    """
    df = pd.read_csv(source)

    _validate_columns(df, {"Menu Item", "Menu Item Category", "Selling Price"}, "Menu Items")

    df["Selling Price"] = _parse_currency_column(df, "Selling Price", "Menu Items")
    return df
