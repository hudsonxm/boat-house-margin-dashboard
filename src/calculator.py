import pandas as pd


def cost_per_recipe_unit(
    purchase_cost: float, purchase_size: float, purchase_unit: str, recipe_unit: str
) -> float | None:
    """
    Calculates purchase cost per recipe unit for an ingredient.
    Returns None if purchase_cost or purchase_size is blank (NaN), since the
    ingredient database is sparse and missing cost data can't be computed.
    """
    if pd.isna(purchase_cost) or pd.isna(purchase_size) or purchase_size == 0:
        return None

    factor = 1
    if purchase_unit == "lbs" and recipe_unit == "oz":
        factor = 16  # Standard unit conversion factor for pounds to ounces
    elif purchase_unit == "bags" and recipe_unit == "fl oz":
        factor = 16.88  # Boat House's estimated fl oz yield per tea bag

    return purchase_cost / (purchase_size * factor)


def calculate_ingredient_cost(amount_used: float, cost_per_recipe_unit: float) -> float:
    """
    Calculates the cost of an ingredient in a recipe.
    """
    return amount_used * cost_per_recipe_unit


def build_ingredient_costs(
    menu_item: str, recipe_sheet: pd.DataFrame, ingredient_database: pd.DataFrame
) -> dict:
    """
    Builds a dictionary of ingredient costs and missing ingredients (if applicable) for a menu item.
    """
    ingredient_costs = {"costs": [], "missing_ingredients": []}
    recipe = recipe_sheet.loc[recipe_sheet["Menu Item"] == menu_item]

    for _, row in recipe.iterrows():
        ingredient_id = row["Ingredient ID"]
        amount_used = row["Amount Used"]

        match = ingredient_database.loc[
            ingredient_database["Ingredient ID"] == ingredient_id
        ]
        if match.empty:
            ingredient_costs["missing_ingredients"].append(ingredient_id)
            continue

        row_data = match.iloc[0]
        purchase_cost = float(row_data["Purchase Cost"])
        purchase_size = float(row_data["Purchase Size"])
        purchase_unit = str(row_data["Purchase Unit"])
        recipe_unit = str(row_data["Recipe Unit"])

        cost_per_unit = cost_per_recipe_unit(
            purchase_cost, purchase_size, purchase_unit, recipe_unit
        )
        if cost_per_unit is not None:
            ingredient_cost = calculate_ingredient_cost(amount_used, cost_per_unit)
            ingredient_costs["costs"].append(ingredient_cost)
        else:
            ingredient_costs["missing_ingredients"].append(ingredient_id)

    return ingredient_costs


def calculate_total_ingredient_cost(ingredient_costs: list[float]) -> float:
    """
    Adds up all ingredient costs in the menu item.
    """
    return sum(ingredient_costs)


def calculate_gross_profit(selling_price: float, total_ingredient_cost: float) -> float:
    """
    Calculates gross profit by subtracting total ingredient cost from selling price.
    """
    return selling_price - total_ingredient_cost


def calculate_margin_percent(gross_profit: float, selling_price: float) -> float:
    """
    Calculates margin percentage by dividing gross profit by selling price.
    """
    return (gross_profit / selling_price) * 100


def calculate_food_cost(margin_percent: float) -> float:
    """
    Calculates food cost by subtracting margin percent from 100.
    Data source: all params come from menu items
    Location: Menu Items
    """
    return 100 - margin_percent


def build_margin_report(
    menu_items: pd.DataFrame,
    recipe_sheet: pd.DataFrame,
    ingredient_database: pd.DataFrame,
) -> pd.DataFrame:
    """
    One row per menu item: Menu Item, Category, Selling Price, Total Ingredient Cost,
    Gross Profit, Food Cost, Missing Ingredients. The glue the UI renders.
    """

    rows = []
    for _, row in menu_items.iterrows():
        menu_item = row["Menu Item"]
        menu_item_category = row["Menu Item Category"]
        selling_price = row["Selling Price"]

        ingredient_costs = build_ingredient_costs(
            menu_item, recipe_sheet, ingredient_database
        )
        total_ingredient_cost = calculate_total_ingredient_cost(
            ingredient_costs["costs"]
        )
        gross_profit = calculate_gross_profit(selling_price, total_ingredient_cost)

        margin_percent = calculate_margin_percent(gross_profit, selling_price)
        food_cost = calculate_food_cost(margin_percent)

        missing_ingredients = ingredient_costs["missing_ingredients"]

        rows.append(
            {
                "Menu Item": menu_item,
                "Category": menu_item_category,
                "Selling Price": selling_price,
                "Total Ingredient Cost": total_ingredient_cost,
                "Gross Profit": gross_profit,
                "Food Cost": food_cost,
                "Missing Ingredients": missing_ingredients,
            }
        )

    return pd.DataFrame(rows)
