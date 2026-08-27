import pandas as pd


def cost_per_recipe_unit(purchase_cost: float, purchase_size: float, purchase_unit: str, recipe_unit: str) -> float | None:
    """
    Calculates purchase cost per recipe unit for an ingredient.
    Data source: all params come from ingredient database
    Location: Ingredient Database
    Returns None if purchase_cost or purchase_size is blank (NaN), since the
    ingredient database is sparse and missing cost data can't be computed.
    """
    if pd.isna(purchase_cost) or pd.isna(purchase_size) or purchase_size == 0:
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

def build_ingredient_costs(menu_item: str, recipe_sheet: pd.DataFrame, ingredient_database: pd.DataFrame) -> dict:
    """
    Builds a dictionary of ingredient costs for a menu item.
    """
    ingredient_costs = {"costs": [], "missing_ingredients": []}
    recipe = recipe_sheet[recipe_sheet["Menu Item"] == menu_item]

    for _, row in recipe.iterrows():
        ingredient = row["Ingredient"]
        amount_used = row["Amount Used"]
        ingredient_category = row["Ingredient Category"]

        match = ingredient_database.loc[(ingredient_database["Ingredient"] == ingredient) & (ingredient_database["Category"] == ingredient_category)]
        if match.empty:
            ingredient_costs["missing_ingredients"].append(ingredient)
            continue

        row_data = match.iloc[0]
        purchase_cost = float(row_data["Purchase Cost"])
        purchase_size = float(row_data["Purchase Size"])
        purchase_unit = str(row_data["Purchase Unit"])
        recipe_unit = str(row_data["Recipe Unit"])

        cost_per_unit = cost_per_recipe_unit(purchase_cost, purchase_size, purchase_unit, recipe_unit)
        if cost_per_unit is not None:
            ingredient_cost = calculate_ingredient_cost(amount_used, cost_per_unit)
            ingredient_costs["costs"].append(ingredient_cost)
        else:
            ingredient_costs["missing_ingredients"].append(ingredient)

    return ingredient_costs




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