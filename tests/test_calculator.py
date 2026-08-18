from pytest import approx
from src.calculator import cost_per_recipe_unit
from src.calculator import calculate_ingredient_cost
from src.calculator import calculate_total_ingredient_cost
from src.calculator import calculate_gross_profit
from src.calculator import calculate_margin_percent
from src.calculator import calculate_food_cost


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
    Iced Tea cost per recipe unit test, bags to fl oz conversion.
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

def test_cost_per_recipe_unit_blank_cost_returns_none() -> None:
    """
    Blank-cost test using Collagen's current row in the full ingredient
    database (blank Purchase Cost and Purchase Size as of 2026-08-13 --
    this ingredient is expected to get real cost data eventually). pandas
    reads blank numeric CSV cells as NaN, so cost_per_recipe_unit must
    return None rather than propagating NaN math.
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