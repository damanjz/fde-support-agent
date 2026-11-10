"""Deterministic generator for data/products.json and data/orders.json (seed 2026)."""

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA = Path(__file__).parent
IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime(2026, 11, 9, 0, 0, tzinfo=IST)
START = datetime(2026, 6, 1, 8, 0, tzinfo=IST)
END = datetime(2026, 11, 8, 18, 0, tzinfo=IST)
PLACED_AFTER = datetime(2026, 11, 8, 12, 0, tzinfo=IST)

WARRANTY = {"grinder": 24, "brewer": 12, "kettle": 12, "accessory": 6, "beans": 0}

# (sku, name, category, price_inr)
PRODUCTS = [
    ("GR-001", "Larkfield Hand Burr Grinder Compact", "grinder", 2499),
    ("GR-002", "Larkfield Hand Burr Grinder Pro", "grinder", 3999),
    ("GR-003", "Larkfield Electric Burr Grinder Everyday", "grinder", 5499),
    ("GR-004", "Larkfield Electric Burr Grinder Precision", "grinder", 8999),
    ("GR-005", "Larkfield Conical Burr Grinder Slim", "grinder", 6499),
    ("GR-006", "Larkfield Espresso Grinder 64mm", "grinder", 12999),
    ("GR-007", "Larkfield Travel Hand Grinder", "grinder", 1999),
    ("GR-008", "Larkfield Flat Burr Grinder", "grinder", 10499),
    ("BR-001", "Ceramic Pour-Over Dripper", "brewer", 1299),
    ("BR-002", "Glass Pour-Over Set", "brewer", 1799),
    ("BR-003", "French Press 600ml", "brewer", 1499),
    ("BR-004", "French Press 1L", "brewer", 1899),
    ("BR-005", "Larkfield Press Brewer", "brewer", 2499),
    ("BR-006", "Moka Pot 3-Cup", "brewer", 1199),
    ("BR-007", "Moka Pot 6-Cup", "brewer", 1599),
    ("BR-008", "Electric Drip Brewer 8-Cup", "brewer", 6999),
    ("BR-009", "Cold Brew Jar 1L", "brewer", 1399),
    ("BR-010", "Home Espresso Machine", "brewer", 24999),
    ("KT-001", "Stovetop Gooseneck Kettle 1.0L", "kettle", 1999),
    ("KT-002", "Electric Gooseneck Kettle 0.9L", "kettle", 4499),
    ("KT-003", "Variable Temperature Kettle 0.8L", "kettle", 5999),
    ("KT-004", "Variable Temperature Kettle Pro", "kettle", 7499),
    ("KT-005", "Travel Kettle 0.5L", "kettle", 2999),
    ("BN-001", "House Blend 250g", "beans", 499),
    ("BN-002", "Chikmagalur Estate Medium Roast 250g", "beans", 549),
    ("BN-003", "Coorg Peaberry 250g", "beans", 579),
    ("BN-004", "Araku Valley Light Roast 250g", "beans", 599),
    ("BN-005", "Baba Budangiri Medium Dark 250g", "beans", 549),
    ("BN-006", "Monsooned Malabar 250g", "beans", 529),
    ("BN-007", "Espresso Blend Dark 250g", "beans", 519),
    ("BN-008", "Ethiopia Yirgacheffe 250g", "beans", 899),
    ("BN-009", "Colombia Huila 250g", "beans", 799),
    ("BN-010", "Decaf Swiss Water 250g", "beans", 749),
    ("BN-011", "Cold Brew Blend 500g", "beans", 849),
    ("BN-012", "House Blend 1kg", "beans", 1799),
    ("BN-013", "Sampler Pack 4x100g", "beans", 899),
    ("BN-014", "Seasonal Filter Roast 250g", "beans", 649),
    ("BN-015", "Cappuccino Blend 250g", "beans", 539),
    ("AC-001", "Digital Coffee Scale with Timer", "accessory", 1499),
    ("AC-002", "Grinder Cleaning Tablets", "accessory", 299),
    ("AC-003", "Paper Filters V60 (100 pack)", "accessory", 349),
    ("AC-004", "Citric Acid Descaler 200g", "accessory", 249),
    ("AC-005", "Replacement Burr Set", "accessory", 1299),
    ("AC-006", "Ceramic Mug 12oz", "accessory", 599),
    ("AC-007", "Insulated Travel Mug", "accessory", 1299),
    ("AC-008", "Milk Frothing Jug", "accessory", 799),
    ("AC-009", "Coffee Tamper 58mm", "accessory", 999),
    ("AC-010", "Bean Storage Canister", "accessory", 1199),
    ("AC-011", "Knock Box", "accessory", 1499),
    ("AC-012", "Brew Thermometer", "accessory", 699),
]
OUT_OF_STOCK = {"GR-006", "BR-010", "KT-004", "BN-008", "BN-010", "BN-013", "AC-005", "BR-008"}

FIRST = ["Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Karthik", "Siddharth", "Rahul", "Nikhil", "Varun",
         "Ananya", "Diya", "Isha", "Kavya", "Meera", "Neha", "Priya", "Riya", "Sneha", "Tanvi",
         "Harini", "Lakshmi", "Venkat", "Suresh", "Imran", "Farhan", "Zoya", "Nandini", "Pooja", "Deepak"]
LAST = ["Sharma", "Reddy", "Iyer", "Nair", "Patel", "Gupta", "Mehta", "Rao", "Kulkarni", "Banerjee",
        "Chatterjee", "Joshi", "Menon", "Pillai", "Singh", "Khan", "Das", "Bose", "Naidu", "Verma"]
CARRIERS = [("BlueDart", "BD", 9), ("Delhivery", "DL", 10), ("DTDC", "DT", 8)]


def build_products(rng: random.Random) -> list[dict]:
    items = []
    for sku, name, cat, price in PRODUCTS:
        stock = 0 if sku in OUT_OF_STOCK else rng.choice([3, 5, 8, 12, 20, 35, 48, 60, 90, 140])
        items.append({"sku": sku, "name": name, "category": cat, "price_inr": price,
                      "stock": stock, "warranty_months": WARRANTY[cat]})
    return items


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def build_order(n: int, ordered: datetime, products: list[dict], rng: random.Random) -> dict:
    first, last = rng.choice(FIRST), rng.choice(LAST)
    items = []
    for p in rng.sample(products, rng.choice([1, 1, 2, 2, 3])):
        qty = rng.choice([1, 1, 1, 2]) if p["category"] != "beans" else rng.choice([1, 2, 3])
        items.append({"sku": p["sku"], "qty": qty, "price_inr": p["price_inr"]})
    shipped = ordered + timedelta(hours=rng.randint(5, 30))
    delivered = shipped + timedelta(days=rng.randint(2, 6), hours=rng.randint(0, 8))
    carrier, prefix, digits = rng.choice(CARRIERS)
    tracking = prefix + "".join(str(rng.randint(0, 9)) for _ in range(digits))
    roll = rng.random()
    if roll < 0.05:
        status = "cancelled"
    elif ordered > PLACED_AFTER:
        status = "placed"
    elif delivered > NOW:
        status = "shipped"
    else:
        status = "returned" if rng.random() < 0.07 else "delivered"
    has_ship = status in ("shipped", "delivered", "returned")
    has_deliv = status in ("delivered", "returned")
    return {
        "order_id": f"LC-{1000 + n}",
        "customer_name": f"{first} {last}",
        "email": f"{first.lower()}.{last.lower()}{rng.randint(1, 99)}@example.com",
        "phone": "+91 9" + "".join(str(rng.randint(0, 9)) for _ in range(9)),
        "items": items,
        "total_inr": sum(i["qty"] * i["price_inr"] for i in items),
        "status": status,
        "ordered_at": iso(ordered),
        "shipped_at": iso(shipped) if has_ship else None,
        "delivered_at": iso(delivered) if has_deliv else None,
        "carrier": carrier if has_ship else None,
        "tracking": tracking if has_ship else None,
    }


def main() -> None:
    rng = random.Random(2026)
    products = build_products(rng)
    span = (END - START).total_seconds()
    stamps = sorted(START + timedelta(seconds=(rng.random() ** 0.45) * span) for _ in range(194))
    late = PLACED_AFTER + timedelta(minutes=30)
    stamps += sorted(late + timedelta(minutes=rng.randint(0, 210)) for _ in range(6))
    orders = [build_order(n, ts, products, rng) for n, ts in enumerate(stamps, start=1)]
    (DATA / "products.json").write_text(json.dumps(products, indent=2) + "\n", encoding="utf-8")
    (DATA / "orders.json").write_text(json.dumps(orders, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(products)} products and {len(orders)} orders")


if __name__ == "__main__":
    main()
