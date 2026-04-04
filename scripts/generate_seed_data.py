import csv
import random
from datetime import datetime, timedelta
from typing import Dict, List


random.seed(42)

# config
NUM_ROWS = 50000
OUTPUT_PATH = "dbt/seeds/fact_order_items_seed.csv"
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 3, 1)

# based on real FakeStoreAPI data
USER_IDS = list(range(1, 11))
PRODUCT_IDS = list(range(1, 21))

PRODUCT_PRICES = {
    1:  109.95,
    2:  22.30,
    3:  55.99,
    4:  15.99,
    5:  695.00,
    6:  168.00,
    7:  7.95,
    8:  375.00,
    9:  64.00,
    10: 67.99,
    11: 109.50,
    12: 12.99,
    13: 9.85,
    14: 19.99,
    15: 39.99,
    16: 299.00,
    17: 49.99,
    18: 129.00,
    19: 89.99,
    20: 24.99,
}

# seasonal weights — higher in Nov, Dec, Jan
def get_seasonal_weight(date: datetime) -> float:
    month = date.month
    weights = {
        1:  1.4,
        2:  0.8,
        3:  0.9,
        4:  0.9,
        5:  1.0,
        6:  1.0,
        7:  1.1,
        8:  1.1,
        9:  1.0,
        10: 1.2,
        11: 1.5,
        12: 2.0,
    }
    return weights.get(month, 1.0)


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def generate_rows(num_rows: int) -> List[Dict]:
    rows = []
    order_item_id = 1
    order_id = 1001

    # generate orders — each order has 1 to 4 items
    while len(rows) < num_rows:
        user_id = random.choice(USER_IDS)
        order_date = random_date(START_DATE, END_DATE)

        # seasonal adjustment — more orders in peak months
        weight = get_seasonal_weight(order_date)
        if random.random() > (1 / weight):
            num_items = random.randint(1, 4)
            products_in_order = random.sample(PRODUCT_IDS, min(num_items, len(PRODUCT_IDS)))

            for product_id in products_in_order:
                quantity = random.randint(1, 5)
                unit_price = PRODUCT_PRICES[product_id]
                total_price = round(quantity * unit_price, 2)

                rows.append({
                    "order_item_id":    order_item_id,
                    "order_id":         order_id,
                    "user_id":          user_id,
                    "product_id":       product_id,
                    "quantity":         quantity,
                    "unit_price":       unit_price,
                    "total_price":      total_price,
                    "order_date":       order_date.strftime("%Y-%m-%d"),
                })
                order_item_id += 1

                if len(rows) >= num_rows:
                    break

            order_id += 1

    return rows[:num_rows]


def write_csv(rows: List[Dict], output_path: str) -> None:
    fieldnames = [
        "order_item_id", "order_id", "user_id", "product_id",
        "quantity", "unit_price", "total_price", "order_date"
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    print(f"Generating {NUM_ROWS} rows of synthetic order data...")
    rows = generate_rows(NUM_ROWS)
    write_csv(rows, OUTPUT_PATH)

    total_revenue = sum(r["total_price"] for r in rows)
    print(f"Total revenue: ${total_revenue:,.2f}")
    print(f"Unique orders: {len(set(r['order_id'] for r in rows))}")
    print(f"Date range: {rows[0]['order_date']} to {rows[-1]['order_date']}")