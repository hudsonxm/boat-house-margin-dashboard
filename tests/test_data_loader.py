import re
from pathlib import Path
import pandas as pd
import pytest
from src.data_loader import strip_currency
from src.data_loader import load_ingredient_database
from src.data_loader import load_menu_items
from src.data_loader import load_recipe_sheet
from src.data_loader import _validate_columns
from src.data_loader import _parse_currency_column
from src.data_loader import google_sheet_csv_url

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures"


def test_google_sheet_csv_url_encodes_tab_name():
    """
    google_sheet_csv_url() builds the per-tab CSV export endpoint and
    URL-encodes the tab's display name (spaces -> %20) so a multi-word tab like
    "INGREDIENT DATABASE" resolves instead of 400ing.
    """
    url = google_sheet_csv_url("SHEET_ID_123", "INGREDIENT DATABASE")

    assert url == (
        "https://docs.google.com/spreadsheets/d/SHEET_ID_123"
        "/gviz/tq?tqx=out:csv&headers=1&sheet=INGREDIENT%20DATABASE"
    )

def test_strip_currency_preserve_nan():
    """
    strip_currency() test on Series with dollar signs, NaN, and a plain number.
    """
    expected = pd.Series([28.82, float("nan"), 43.23])

    assert expected.equals(strip_currency(pd.Series(["$28.82", float("nan"), 43.23])))


def test_validate_columns_raises_value_error():
    """"
    _validate_columns() test on a recipe sheet DataFrame with two missing required columns
    (Ingredient ID and Amount Used).
    """
    expected_df = pd.DataFrame([
        {"Menu Item": "Mermaid", "Ingredient": "Zipfizz", "Ingredient Category": "Powder", "Recipe Unit": "each", "Notes": float("nan")}
        ])
    expected_required = {"Menu Item", "Ingredient ID", "Amount Used"}
    expected_csv_name = "Recipe Sheet"
    expected_missing = sorted({"Ingredient ID", "Amount Used"})

    expected_msg = f"Missing required {expected_csv_name} columns: {expected_missing}"

    with pytest.raises(ValueError, match=re.escape(expected_msg)):
        _validate_columns(expected_df, expected_required, expected_csv_name)


def test_parse_currency_column_raises_value_error():
    """
    _parse_currency_column() test on a menu items DataFrame with a
    Selling Price data-entry typo ($9.0.0).
    """

    expected_df = pd.DataFrame([
        {"Menu Item": "Mojito", "Menu Item Category": "Portside Power Tea", "Available At": "Both", "Selling Price": "$9.0.0", "Notes": float("nan")}
    ])
    expected_column = "Selling Price"
    expected_csv_name = "Menu Items"
    expected_bad = {0: "$9.0.0"}

    expected_msg = f"{expected_csv_name} could not parse {expected_column} values: {list(expected_bad.values())}"

    with pytest.raises(ValueError, match=re.escape(expected_msg)):
        _parse_currency_column(expected_df, expected_column, expected_csv_name)


def test_load_ingredient_database():
    """
    load_ingredient_database() test on the pinned fixture CSV: required columns
    survive, Purchase Cost is stripped from "$28.82"-style strings to float, and a
    blank Notes cell stays NaN (missing-data policy).
    """
    df = load_ingredient_database(FIXTURES / "ingredient_database.csv")

    expected_required = {"Ingredient ID", "Purchase Size", "Purchase Unit", "Purchase Cost", "Recipe Unit"}
    assert expected_required <= set(df.columns)
    assert df["Purchase Cost"].dtype == float

    expected_bananas = df.loc[df["Ingredient ID"] == "FRZ-BANANAS"].iloc[0]
    assert expected_bananas["Purchase Cost"] == 28.82
    assert pd.isna(expected_bananas["Notes"])


def test_load_menu_items():
    """
    load_menu_items() test on the pinned fixture CSV: required columns survive and
    Selling Price is stripped from "$12.00"-style strings to float.
    """
    df = load_menu_items(FIXTURES / "menu_items.csv")

    expected_prices = pd.Series([12.00, 12.00, 9.00, 12.00])

    assert {"Menu Item", "Selling Price"} <= set(df.columns)
    assert expected_prices.equals(df["Selling Price"])


def test_load_recipe_sheet():
    """
    load_recipe_sheet() test on the pinned fixture CSV: required columns survive
    and rows pass through unchanged (no currency columns to clean here).
    """
    df = load_recipe_sheet(FIXTURES / "recipe_sheet.csv")

    assert {"Menu Item", "Ingredient ID", "Amount Used"} <= set(df.columns)

    expected_pb_banana = df.loc[df["Menu Item"] == "Peanut Butter Banana"]
    assert len(expected_pb_banana) == 11
    assert expected_pb_banana.loc[expected_pb_banana["Ingredient ID"] == "FRZ-BANANAS", "Amount Used"].iloc[0] == 4.8

