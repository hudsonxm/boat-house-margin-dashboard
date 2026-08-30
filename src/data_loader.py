import pandas as pd


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
        bad = raw[missing].to_dict() # {row index: original value}
        raise ValueError(f"{csv_name} could not parse {column} values: {list(bad.values())}") # TODO: surface as UI warning like missing_ingredients

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

    _validate_columns(df,
                    {"Ingredient ID", "Purchase Size", "Purchase Unit", "Purchase Cost", "Recipe Unit"},
                    "Ingredient Database"
                    )

    df["Purchase Cost"] = _parse_currency_column(df, "Purchase Cost", "Ingredient Database")
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

    _validate_columns(df, {"Menu Item", "Selling Price"}, "Menu Items")

    df["Selling Price"] = _parse_currency_column(df, "Selling Price", "Menu Items")
    return df