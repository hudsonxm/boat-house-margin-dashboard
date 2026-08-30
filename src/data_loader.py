import pandas as pd


def strip_currency(series: pd.Series) -> pd.Series:
    """
    Strips currency symbols from a pandas Series of strings and converts to float.
    """
    cleaned = series.astype(str).str.replace(",", "").str.lstrip("$").str.rstrip("%") # astype(str) so numeric columns don't crash the .str accessor
    return pd.to_numeric(cleaned, errors="coerce") # TODO: should I check for parse failures (cell had data but came out NaN after coerce)?


def load_ingredient_database(source) -> pd.DataFrame:
    df = pd.read_csv(source)

    _validate_columns(df,
                    {"Ingredient ID", "Purchase Size", "Purchase Unit", "Purchase Cost", "Recipe Unit"},
                    "Ingredient Database"
                    )

    df["Purchase Cost"] = strip_currency(df["Purchase Cost"])
    return df


def load_recipe_sheet(source) -> pd.DataFrame:
    df = pd.read_csv(source)

    _validate_columns(df, {"Menu Item", "Ingredient ID", "Amount Used"}, "Recipe Sheet")

    return df


def load_menu_items(source) -> pd.DataFrame:
    df = pd.read_csv(source)

    _validate_columns(df, {"Menu Item", "Selling Price"}, "Menu Items")

    df["Selling Price"] = strip_currency(df["Selling Price"])
    return df


def _validate_columns(df: pd.DataFrame, required: set, csv_name: str) -> None:
    missing = sorted(required - set(df.columns))

    if missing:
        raise ValueError(f"Missing required {csv_name} columns: {missing}")