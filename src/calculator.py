# Ingredient Database works alone, Recipe Sheet needs Ingreident Database,
# Menu Items needs both, double removed

"""
Calculates purchase cost per recipe unit for an ingredient.
Data source: all params come from ingredient database
Location: Ingredient Database
"""
def cost_per_recipe_unit(purchase_cost: float, purchase_size: float, purchase_unit: str, recipe_unit: str):
    pass


"""
Calculates the cost of an ingredient in a recipe.
Data source: amount_used comes from recipe sheet, cost_per_recipe_unit comes from ingredient database
Location: Recipe Sheet
"""
def calculate_ingredient_cost(amount_used: float, cost_per_recipe_unit: float):
    pass


"""
Adds up all ingredient costs in the menu item.
Data source: ingredient_costs is the list of all ingredient cost floats for a menu item in recipe sheet
Location: Menu Items
"""
def calculate_total_ingredient_cost(ingredient_costs: list[float]):
    pass


"""
Calculates gross profit by subtracting total ingredient cost from selling price.
Data source: selling_price comes from menu_items.csv; total_ingredient_cost is computed by calculate_total_ingredient_cost()
Location: Menu Items
"""
def calculate_gross_profit(selling_price: float, total_ingredient_cost: float):
    pass

"""
Calculates margin percentage by dividing gross profit by selling price.
Data source: selling_price comes from menu_items.csv; gross_profit is computed by calculate_gross_profit()
Location: Menu Items
"""
def calculate_margin_percent(gross_profit: float, selling_price: float):
    pass

"""
Calculates food cost by subtracting margin percent from 100.
Data source: all params come from menu items
Location: Menu Items
"""
def calculate_food_cost(margin_percent: float):
    pass



