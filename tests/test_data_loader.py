import re
import pandas as pd
import pytest
from src.data_loader import strip_currency
from src.data_loader import load_ingredient_database
from src.data_loader import load_menu_items
from src.data_loader import load_recipe_sheet
from src.data_loader import _validate_columns
from src.data_loader import _parse_currency_column

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

