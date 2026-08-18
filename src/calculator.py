# Ingredient Database works alone, Recipe Sheet needs ingredient Database,
# Menu Items needs both, double removed

import math


def cost_per_recipe_unit(purchase_cost: float, purchase_size: float, purchase_unit: str, recipe_unit: str) -> float | None:
    """
    Calculates purchase cost per recipe unit for an ingredient.
    Data source: all params come from ingredient database
    Location: Ingredient Database
    Returns None if purchase_cost or purchase_size is blank (NaN), since the
    ingredient database is sparse and missing cost data can't be computed.
    """
    if math.isnan(purchase_cost) or math.isnan(purchase_size):
        return None

    factor  = 1

    if purchase_unit == "lbs" and recipe_unit == "oz":
        factor = 16 # Standard unit conversion factor for pounds to ounces
    elif purchase_unit == "bags" and recipe_unit == "fl oz":
        factor = 16.88 # Row and Ride's estimated fl oz yield per tea bag

    return purchase_cost / (purchase_size * factor)
    
def calculate_ingredient_cost(amount_used: float, cost_per_recipe_unit: float) -> float:
    """
    Calculates the cost of an ingredient in a recipe.
    Data source: amount_used comes from recipe sheet, cost_per_recipe_unit comes from ingredient database
    Location: Recipe Sheet
    """
    return amount_used * cost_per_recipe_unit

def build_ingredient_costs(): # TODO
    pass

def calculate_total_ingredient_cost(ingredient_costs: list[float]) -> float:
    """
    Adds up all ingredient costs in the menu item.
    Data source: ingredient_costs is the list of all ingredient cost floats for a menu item in recipe sheet
    Location: Menu Items
    """
    return sum(ingredient_costs)


def calculate_gross_profit(selling_price: float, total_ingredient_cost: float) -> float:
    """
    Calculates gross profit by subtracting total ingredient cost from selling price.
    Data source: selling_price comes from menu_items.csv; total_ingredient_cost is computed by calculate_total_ingredient_cost()
    Location: Menu Items
    """
    return selling_price - total_ingredient_cost


def calculate_margin_percent(gross_profit: float, selling_price: float) -> float:
    """
    Calculates margin percentage by dividing gross profit by selling price.
    Data source: selling_price comes from menu_items.csv; gross_profit is computed by calculate_gross_profit()
    Location: Menu Items
    """
    return (gross_profit / selling_price) * 100


def calculate_food_cost(margin_percent: float) -> float:
    """
    Calculates food cost by subtracting margin percent from 100.
    Data source: all params come from menu items
    Location: Menu Items
    """
    return 100 - margin_percent