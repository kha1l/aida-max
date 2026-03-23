"""Константы и справочники для меню подписок."""
# Сопоставление "код отчёта" -> "текст кнопки"
POST = {
    "stops_rest": "\U0001F3E2 Stops by sales channels",
    "stops_ings": "\U0001F9C0 Stops by ingredients",
    "stops_key_ings": "\U0001F355 Stops by key ingredients",
    "stops_sector": "\U0001F5FE Stops by sectors",
    "tickets": "\U0001F4D8 Customer tickets",
    "birthday": "\U0001F389 Birthdays",
    "couriers": "\U0001F69B Courier reports",
    "refusal": "\U0001F17E Cancelled orders",
    "defect": "\U0001F9EA Defect",
    "metrics": "\U0001F4C9 Key metrics",
    "stationary": "\U0001F373 Restaurant delays",
    "revenue": "\U0001F4B5 Network revenue",
    "stock": "\U0001F69A Stock balances",
    "writeoff": "\U0001F5D1 Write-offs",
    "stock_finished": "\U0001F69A Stock balances",
    "staff": "\U0001F9FE Staff info",
}

# Категории для складских остатков
STOCK_ITEMS = [
    {"id": "Ingredient", "label": "\U0001F345 Ingredients"},
    {"id": "SemiFinishedProduct", "label": "\U0001F364 Semi-finished products"},
    {"id": "FinishedProduct", "label": "\U0001F355 Finished products"},
    {"id": "Packing", "label": "\U0001F961 Packaging"},
]
