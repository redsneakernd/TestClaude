"""
Generates a sample sales Excel dataset for the demo app.
Run once: python sample_data.py
"""

import random
from pathlib import Path
from datetime import date, timedelta

import pandas as pd

REGIONS = ["North", "South", "East", "West"]
PRODUCTS = ["Widget A", "Widget B", "Gadget Pro", "Gadget Lite", "SuperTool", "MegaKit"]
SALES_REPS = [
    "Alice Johnson", "Bob Smith", "Carol White", "David Lee",
    "Eva Martinez", "Frank Brown", "Grace Kim", "Henry Davis",
]

PRODUCT_PRICE = {
    "Widget A": 49.99,
    "Widget B": 79.99,
    "Gadget Pro": 199.99,
    "Gadget Lite": 99.99,
    "SuperTool": 149.99,
    "MegaKit": 299.99,
}

PRODUCT_COST_RATIO = {
    "Widget A": 0.45,
    "Widget B": 0.40,
    "Gadget Pro": 0.35,
    "Gadget Lite": 0.42,
    "SuperTool": 0.38,
    "MegaKit": 0.33,
}

random.seed(42)

start_date = date(2024, 1, 1)
end_date = date(2024, 12, 31)
num_rows = 250

rows = []
for _ in range(num_rows):
    days_offset = random.randint(0, (end_date - start_date).days)
    sale_date = start_date + timedelta(days=days_offset)
    product = random.choice(PRODUCTS)
    units = random.randint(1, 50)
    price = PRODUCT_PRICE[product]
    revenue = round(units * price, 2)
    cost = round(revenue * PRODUCT_COST_RATIO[product], 2)

    rows.append({
        "Date": sale_date,
        "Region": random.choice(REGIONS),
        "Product": product,
        "Sales Rep": random.choice(SALES_REPS),
        "Units Sold": units,
        "Revenue": revenue,
        "Cost": cost,
        "Profit": round(revenue - cost, 2),
    })

df = pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)

output_path = Path(__file__).parent / "data" / "sample_sales.xlsx"
output_path.parent.mkdir(exist_ok=True)
df.to_excel(output_path, index=False)

print(f"Generated {len(df)} rows -> {output_path}")
