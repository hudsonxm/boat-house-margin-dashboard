from pathlib import Path
import pandas as pd
from pytest import approx
from src.calculator import cost_per_recipe_unit
from src.calculator import calculate_ingredient_cost
from src.calculator import build_ingredient_costs
from src.calculator import calculate_total_ingredient_cost
from src.calculator import calculate_gross_profit
from src.calculator import calculate_margin_percent
from src.calculator import calculate_food_cost
from src.data_loader import strip_currency
from src.data_loader import load_ingredient_database
from src.data_loader import load_recipe_sheet
from src.data_loader import load_menu_items

FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures"


def test_cost_per_recipe_unit_bananas() -> None:
    """
    Frozen Bananas cost per recipe unit test.
    """
    result = cost_per_recipe_unit(
        purchase_cost=28.82,
        purchase_size=20,
        purchase_unit="lbs",
        recipe_unit="oz"
    )

    assert result == approx(0.0901, abs=0.0001)

def test_cost_per_recipe_unit_iced_tea() -> None:
    """
    bags -> fl oz conversion (factor 16.88). Only the pinned pilot
    fixtures still buy tea by the bag -- the live database now tracks
    brewed tea as its own ingredient -- but this branch must keep
    working for the regression fixtures.
    """
    result = cost_per_recipe_unit(
        purchase_cost=20.95,
        purchase_size=132,
        purchase_unit="bags",
        recipe_unit="fl oz"
    )

    assert result == approx(0.0094, abs=0.0001)

def test_cost_per_recipe_unit_oat_milk() -> None:
    """
    Oat Milk cost per recipe unit test, no conversion needed (fl oz to fl oz).
    """
    result = cost_per_recipe_unit(
        purchase_cost=32.93,
        purchase_size=384,
        purchase_unit="fl oz",
        recipe_unit="fl oz"
    )

    assert result == approx(0.0858, abs=0.0001)

def test_cost_per_recipe_unit_coconut_cubes() -> None:
    """
    Coconut Cubes cost per recipe unit test. Purchase Unit "cubes" and
    Recipe Unit "cubes" now match exactly (data-entry fix), so this falls
    through to the factor-1 path on purpose rather than by accident.
    """
    result = cost_per_recipe_unit(
        purchase_cost=2.03,
        purchase_size=14,
        purchase_unit="cubes",
        recipe_unit="cubes"
    )

    assert result == approx(0.1450, abs=0.0001)

def test_cost_per_recipe_unit_blank_cost_returns_none() -> None:
    """
    Missing-cost test: when an ingredient's Purchase Cost / Purchase Size
    haven't been filled in yet, pd.read_csv gives NaN, and
    cost_per_recipe_unit must return None rather than propagating NaN
    through the math. The full ingredient database is currently complete,
    so this guards the "new ingredient added before its price is known"
    case.
    """
    result = cost_per_recipe_unit(
        purchase_cost=float("nan"),
        purchase_size=float("nan"),
        purchase_unit="Powder",
        recipe_unit="Powder"
    )

    assert result is None

def test_calculate_ingredient_cost_oat_milk() -> None:
    """
    Oat milk ingredient cost test in Peanut Butter Banana.
    """
    result = calculate_ingredient_cost(
        amount_used=10,
        cost_per_recipe_unit=0.0858
    )

    assert result == approx(0.858, abs=0.0001)

def test_build_ingredient_costs_peanut_butter_banana() -> None:
    """
    Happy-path test for the glue function: given Peanut Butter Banana's
    recipe rows and a clean (already numeric) ingredient database, costs
    should match the pilot sheet's known per-ingredient values with no
    missing ingredients.
    """
    recipe_sheet = pd.DataFrame([
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "MLK-OAT_MILK", "Ingredient": "Oat Milk", "Amount Used": 10},
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "PWD-VANILLA_PROTEIN", "Ingredient": "Vanilla Protein", "Amount Used": 0.8},
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "PWD-PB2", "Ingredient": "PB2", "Amount Used": 0.41},
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "SPR-PEANUT_BUTTER", "Ingredient": "Peanut Butter", "Amount Used": 1},
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "EXT-VANILLA_EXTRACT", "Ingredient": "Vanilla Extract", "Amount Used": 1.5},
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "SWT-HONEY", "Ingredient": "Honey", "Amount Used": 0.5},
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "FRZ-BANANAS", "Ingredient": "Bananas", "Amount Used": 4.8},
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "PRP-COCONUT_CUBES", "Ingredient": "Coconut Cubes", "Amount Used": 3},
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "PKG-20OZ_BRANDED_CUP", "Ingredient": "20oz Branded Cup", "Amount Used": 1},
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "PKG-20OZ_LID", "Ingredient": "20oz Lid", "Amount Used": 1},
        {"Menu Item": "Peanut Butter Banana", "Ingredient ID": "PKG-SMOOTHIE_STRAW", "Ingredient": "Smoothie Straw", "Amount Used": 1},
    ])

    ingredient_database = pd.DataFrame([
        {"Ingredient ID": "MLK-OAT_MILK", "Ingredient": "Oat Milk", "Category": "Milk", "Purchase Size": 384, "Purchase Unit": "fl oz", "Purchase Cost": 32.93, "Recipe Unit": "fl oz"},
        {"Ingredient ID": "PWD-VANILLA_PROTEIN", "Ingredient": "Vanilla Protein", "Category": "Powder", "Purchase Size": 2.03, "Purchase Unit": "lbs", "Purchase Cost": 29.59, "Recipe Unit": "oz"},
        {"Ingredient ID": "PWD-PB2", "Ingredient": "PB2", "Category": "Powder", "Purchase Size": 2, "Purchase Unit": "lbs", "Purchase Cost": 17.94, "Recipe Unit": "oz"},
        {"Ingredient ID": "SPR-PEANUT_BUTTER", "Ingredient": "Peanut Butter", "Category": "Spread", "Purchase Size": 30, "Purchase Unit": "lbs", "Purchase Cost": 77.95, "Recipe Unit": "oz"},
        {"Ingredient ID": "EXT-VANILLA_EXTRACT", "Ingredient": "Vanilla Extract", "Category": "Extract", "Purchase Size": 946, "Purchase Unit": "ml", "Purchase Cost": 8.99, "Recipe Unit": "ml"},
        {"Ingredient ID": "SWT-HONEY", "Ingredient": "Honey", "Category": "Sweetener", "Purchase Size": 2.5, "Purchase Unit": "lbs", "Purchase Cost": 8.49, "Recipe Unit": "oz"},
        {"Ingredient ID": "FRZ-BANANAS", "Ingredient": "Bananas", "Category": "Frozen Fruit", "Purchase Size": 20, "Purchase Unit": "lbs", "Purchase Cost": 28.82, "Recipe Unit": "oz"},
        {"Ingredient ID": "PRP-COCONUT_CUBES", "Ingredient": "Coconut Cubes", "Category": "Prepared Ingredient", "Purchase Size": 14, "Purchase Unit": "cubes", "Purchase Cost": 2.03, "Recipe Unit": "cubes"},
        {"Ingredient ID": "PKG-20OZ_BRANDED_CUP", "Ingredient": "20oz Branded Cup", "Category": "Packaging", "Purchase Size": 1000, "Purchase Unit": "each", "Purchase Cost": 295.82, "Recipe Unit": "each"},
        {"Ingredient ID": "PKG-20OZ_LID", "Ingredient": "20oz Lid", "Category": "Packaging", "Purchase Size": 1000, "Purchase Unit": "each", "Purchase Cost": 33.36, "Recipe Unit": "each"},
        {"Ingredient ID": "PKG-SMOOTHIE_STRAW", "Ingredient": "Smoothie Straw", "Category": "Packaging", "Purchase Size": 2000, "Purchase Unit": "each", "Purchase Cost": 44.30, "Recipe Unit": "each"},
    ])

    result = build_ingredient_costs("Peanut Butter Banana", recipe_sheet, ingredient_database)

    assert result["missing_ingredients"] == []
    assert result["costs"] == approx(
        [0.8576, 0.7288, 0.2299, 0.1624, 0.0143, 0.1061, 0.4323, 0.4350, 0.2958, 0.0334, 0.0222],
        abs=0.0001
    )

def test_build_ingredient_costs_missing_ingredient() -> None:
    """
    An ingredient present in the recipe sheet but absent from the
    ingredient database (e.g. not yet added, or a mistyped Ingredient ID)
    should be flagged in missing_ingredients (by its Ingredient ID)
    rather than raising or silently skipping.
    """
    recipe_sheet = pd.DataFrame([
        {"Menu Item": "Test Item", "Ingredient ID": "MYS-MYSTERY", "Ingredient": "Mystery Ingredient", "Amount Used": 1},
    ])

    ingredient_database = pd.DataFrame([
        {"Ingredient ID": "MLK-OAT_MILK", "Ingredient": "Oat Milk", "Category": "Milk", "Purchase Size": 384, "Purchase Unit": "fl oz", "Purchase Cost": 32.93, "Recipe Unit": "fl oz"},
    ])

    result = build_ingredient_costs("Test Item", recipe_sheet, ingredient_database)

    assert result["costs"] == []
    assert result["missing_ingredients"] == ["MYS-MYSTERY"]

def test_calculate_total_ingredient_cost_peanut_butter_banana() -> None:
    """
    Total ingredient cost test for Peanut Butter Banana, summing all its
    ingredient and packaging costs from the recipe sheet.
    """
    result = calculate_total_ingredient_cost(
        ingredient_costs=[0.8576, 0.7288, 0.2299, 0.1624, 0.0143, 0.1061, 0.4323, 0.4350, 0.2958, 0.0334, 0.0222]
    )

    assert result == approx(3.3178, abs=0.0001)

def test_calculate_gross_profit_shark_bite() -> None:
    """
    Gross profit test for Shark Bite.
    """
    result = calculate_gross_profit(
        selling_price=9.00,
        total_ingredient_cost=1.9750
    )

    assert result == approx(7.0250, abs=0.0001)

def test_calculate_margin_percent_shark_bite() -> None:
    """
    Margin percent test for Shark Bite.
    """
    result = calculate_margin_percent(
        gross_profit=7.0250,
        selling_price=9.00
    )

    assert result == approx(78.06, abs=0.01)

def test_calculate_food_cost_shark_bite() -> None:
    """
    Food cost test for Shark Bite.
    """
    result = calculate_food_cost(
        margin_percent=78.0556
    )

    assert result == approx(21.94, abs=0.01)

def test_pipeline_ingredient_costs_all_menu_items() -> None:
    """
    End-to-end test: loads the pinned /data/fixtures CSVs through
    data_loader.py, then runs every pilot menu item through
    build_ingredient_costs and checks each ingredient's cost against
    expected_ingredient_costs.csv (computed independently from unrounded
    Purchase Cost / Purchase Size, not the stored Cost Per Recipe Unit
    column).
    """
    recipe_sheet = load_recipe_sheet(FIXTURES / "recipe_sheet.csv")
    recipe_sheet = recipe_sheet.sort_values(["Menu Item", "Ingredient ID"])
    ingredient_database = load_ingredient_database(FIXTURES / "ingredient_database.csv")

    expected = pd.read_csv(FIXTURES / "expected_ingredient_costs.csv")
    expected["Expected Ingredient Cost"] = strip_currency(expected["Expected Ingredient Cost"])
    expected = expected.sort_values(["Menu Item", "Ingredient ID"])

    for menu_item in expected["Menu Item"].unique():
        result = build_ingredient_costs(menu_item, recipe_sheet, ingredient_database)
        expected_costs = expected.loc[expected["Menu Item"] == menu_item, "Expected Ingredient Cost"].tolist() # type: ignore

        assert result["missing_ingredients"] == []
        assert result["costs"] == approx(expected_costs, abs=0.0001)

def test_pipeline_margins_all_menu_items() -> None:
    """
    End-to-end test: loads the pinned /data/fixtures CSVs through
    data_loader.py, runs each pilot menu item through the full margin
    pipeline (build_ingredient_costs -> calculate_total_ingredient_cost ->
    calculate_gross_profit -> calculate_margin_percent ->
    calculate_food_cost), and checks totals against expected_margins.csv.
    Tolerance is ~1 cent / 0.01 percentage point since expected_margins.csv
    is display-rounded, not exact.
    """
    recipe_sheet = load_recipe_sheet(FIXTURES / "recipe_sheet.csv")
    ingredient_database = load_ingredient_database(FIXTURES / "ingredient_database.csv")
    menu_items = load_menu_items(FIXTURES / "menu_items.csv")

    expected = pd.read_csv(FIXTURES / "expected_margins.csv")
    for column in ["Expected Total Ingredient Cost", "Expected Gross Profit", "Expected Margin %", "Expected Food Cost"]:
        expected[column] = strip_currency(expected[column])

    for _, row in expected.iterrows():
        menu_item = row["Menu Item"]
        selling_price = menu_items.loc[menu_items["Menu Item"] == menu_item, "Selling Price"].iloc[0] # type: ignore

        ingredient_costs = build_ingredient_costs(menu_item, recipe_sheet, ingredient_database)
        assert ingredient_costs["missing_ingredients"] == []

        total_cost = calculate_total_ingredient_cost(ingredient_costs["costs"])
        gross_profit = calculate_gross_profit(selling_price, total_cost)
        margin_percent = calculate_margin_percent(gross_profit, selling_price)
        food_cost = calculate_food_cost(margin_percent)

        assert total_cost == approx(row["Expected Total Ingredient Cost"], abs=0.01)
        assert gross_profit == approx(row["Expected Gross Profit"], abs=0.01)
        assert margin_percent == approx(row["Expected Margin %"], abs=0.01)
        assert food_cost == approx(row["Expected Food Cost"], abs=0.01)