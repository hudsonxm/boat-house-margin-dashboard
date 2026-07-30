from pytest import approx
from src.calculator import cost_per_recipe_unit
from src.calculator import calculate_ingredient_cost


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

    assert result == approx(0.901, abs=0.0001)

def test_calculate_ingredient_cost_oat_milk() -> None:
    """
    Oat milk ingredient cost test in Peanut Butter Banana.
    """
    result = calculate_ingredient_cost(
        amount_used=10,
        cost_per_recipe_unit=0.0858
    )

    assert result == approx(0.858, abs=0.0001)