"""Generate a synthetic retail transactions dataset and load it into PostgreSQL.

The data is deterministic (fixed seed). It is built so that real association
rules are discoverable: a set of product "bundles" co-occur far more often than
chance, which produces lift > 1 for those pairs. Everything else is random
noise, so the analysis has to *find* the signal.

Creates and fills three tables: products, transactions, transaction_items.
"""

import random
from datetime import date, timedelta

from psycopg2.extras import execute_values

from db import connect

SEED = 42
random.seed(SEED)

N_TRANSACTIONS = 12000
START = date(2024, 1, 1)
DAYS = 364

# Product catalogue: name -> category
CATALOGUE = {
    "Coffee": "Beverages", "Milk": "Dairy", "Sugar": "Pantry", "Tea": "Beverages",
    "Pasta": "Pantry", "Tomato Sauce": "Pantry", "Parmesan": "Dairy",
    "Olive Oil": "Pantry",
    "Chips": "Snacks", "Soda": "Beverages", "Salsa": "Snacks", "Beer": "Alcohol",
    "Bread": "Bakery", "Butter": "Dairy", "Jam": "Pantry", "Eggs": "Dairy",
    "Bacon": "Meat", "Diapers": "Baby", "Baby Wipes": "Baby", "Shampoo": "Care",
    "Conditioner": "Care", "Toothpaste": "Care", "Bananas": "Produce",
    "Apples": "Produce", "Lettuce": "Produce", "Chicken": "Meat",
    "Rice": "Pantry", "Yogurt": "Dairy", "Cheese": "Dairy", "Water": "Beverages",
    "Cereal": "Pantry", "Orange Juice": "Beverages", "Cookies": "Snacks",
    "Ice Cream": "Frozen", "Frozen Pizza": "Frozen",
}
PRODUCTS = list(CATALOGUE.keys())
PRODUCT_ID = {name: i + 1 for i, name in enumerate(PRODUCTS)}

# Injected bundles: (items, probability the bundle is added to a basket,
# probability each member is actually included given the bundle fired).
# This is the signal the analysis should recover.
BUNDLES = [
    (["Coffee", "Milk", "Sugar"],        0.16, 0.85),
    (["Pasta", "Tomato Sauce", "Parmesan"], 0.14, 0.85),
    (["Chips", "Soda", "Salsa"],         0.13, 0.80),
    (["Bread", "Butter", "Jam"],         0.12, 0.82),
    (["Eggs", "Bacon"],                  0.11, 0.88),
    (["Diapers", "Baby Wipes"],          0.07, 0.90),
    (["Diapers", "Beer"],                0.05, 0.70),   # the classic
    (["Shampoo", "Conditioner"],         0.08, 0.88),
    (["Frozen Pizza", "Beer"],           0.06, 0.75),
]

# Per-item baseline popularity for the random (noise) part of each basket.
POPULARITY = {p: random.uniform(0.02, 0.12) for p in PRODUCTS}
for staple in ["Bananas", "Milk", "Bread", "Water", "Eggs"]:
    POPULARITY[staple] += 0.10

SCHEMA = """
drop table if exists transaction_items;
drop table if exists transactions;
drop table if exists products;

create table products (
    product_id    int primary key,
    product_name  text not null,
    category      text not null
);

create table transactions (
    transaction_id    int primary key,
    customer_id       int not null,
    transaction_date  date not null
);

create table transaction_items (
    transaction_id  int not null references transactions(transaction_id),
    product_id      int not null references products(product_id),
    primary key (transaction_id, product_id)
);

create index on transaction_items (product_id);
"""


def build_basket():
    items = set()
    for members, p_bundle, p_member in BUNDLES:
        if random.random() < p_bundle:
            for m in members:
                if random.random() < p_member:
                    items.add(m)
    for p in PRODUCTS:
        if random.random() < POPULARITY[p]:
            items.add(p)
    while len(items) < 2:
        items.add(random.choice(PRODUCTS))
    return items


def build_dataset():
    products = [(PRODUCT_ID[name], name, CATALOGUE[name]) for name in PRODUCTS]
    tx_rows = []
    item_rows = []
    for tid in range(1, N_TRANSACTIONS + 1):
        tx_date = START + timedelta(days=random.randint(0, DAYS))
        customer_id = random.randint(1, 3000)
        tx_rows.append((tid, customer_id, tx_date))
        for item in build_basket():
            item_rows.append((tid, PRODUCT_ID[item]))
    return products, tx_rows, item_rows


def main():
    products, tx_rows, item_rows = build_dataset()

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
            execute_values(
                cur,
                "insert into products (product_id, product_name, category) values %s",
                products,
            )
            execute_values(
                cur,
                "insert into transactions "
                "(transaction_id, customer_id, transaction_date) values %s",
                tx_rows,
            )
            execute_values(
                cur,
                "insert into transaction_items (transaction_id, product_id) values %s",
                item_rows,
            )
    finally:
        conn.close()

    print(f"products:        {len(products)}")
    print(f"transactions:    {len(tx_rows):,}")
    print(f"basket lines:    {len(item_rows):,}")
    print(f"avg basket size: {len(item_rows) / len(tx_rows):.2f}")
    print("loaded into PostgreSQL (tables: products, transactions, transaction_items)")


if __name__ == "__main__":
    main()
