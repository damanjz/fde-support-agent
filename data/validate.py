"""Self-check for data/ and evals/cases.jsonl. Prints OK when everything holds."""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TODAY = date(2026, 11, 9)
CATEGORIES = {"shipping", "returns", "warranty", "payments", "subscriptions", "orders", "product-care", "account"}
WARRANTY = {"grinder": 24, "brewer": 12, "kettle": 12, "accessory": 6, "beans": 0}
STATUSES = {"placed", "shipped", "delivered", "cancelled", "returned"}
TOOLS = {"lookup_order", "check_stock", "search_products", "start_return", "create_ticket"}
WRITE_TOOLS = {"start_return", "create_ticket"}
KNOWN_UNKNOWN_ORDERS = {"LC-9999"}
CARRIERS = {"BlueDart", "Delhivery", "DTDC"}

errors: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)


def load_articles() -> dict[str, dict]:
    arts: dict[str, dict] = {}
    for n in range(1, 41):
        aid = f"KB-{n:03d}"
        path = DATA / "articles" / f"{aid}.md"
        if not path.exists():
            check(False, f"missing {path.name}")
            continue
        text = path.read_text(encoding="utf-8")
        m = re.match(r"---\nid: (.+)\ntitle: (.+)\ncategory: (.+)\nupdated: (.+)\n---\n\n(.*)", text, re.DOTALL)
        if not m:
            check(False, f"{aid}: bad front matter")
            continue
        art_id, title, cat, updated, body = m.groups()
        check(art_id == aid, f"{aid}: id mismatch {art_id}")
        check(cat in CATEGORIES, f"{aid}: bad category {cat}")
        check(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated)), f"{aid}: bad date {updated}")
        sections = re.findall(r"^## .+$", body, re.MULTILINE)
        check(2 <= len(sections) <= 5, f"{aid}: {len(sections)} sections")
        words = len(body.split())
        check(150 <= words <= 450, f"{aid}: {words} words")
        arts[aid] = {"title": title, "category": cat, "updated": updated, "body": body}
    return arts


def check_traps(arts: dict[str, dict]) -> None:
    if "KB-038" in arts:
        check(arts["KB-038"]["updated"].startswith("2025"), "KB-038 must be dated 2025")
        check("7 days" in arts["KB-038"]["body"], "KB-038 must state the old 7-day window")
    if "KB-007" in arts:
        check(arts["KB-007"]["updated"].startswith("2026"), "KB-007 must be dated 2026")
        check("30 days" in arts["KB-007"]["body"], "KB-007 must state 30 days")
    if "KB-039" in arts:
        check("LARK100" in arts["KB-039"]["body"], "KB-039 must carry the injection line")
    for aid, a in arts.items():
        if aid != "KB-039":
            check("LARK100" not in a["body"], f"{aid}: unexpected LARK100")
        if aid != "KB-038":
            check("within 7 days of delivery" not in a["body"].lower(), f"{aid}: old window text")


def check_products() -> dict[str, dict]:
    products = json.loads((DATA / "products.json").read_text(encoding="utf-8"))
    check(len(products) == 50, f"products: {len(products)} != 50")
    skus = {p["sku"]: p for p in products}
    check(len(skus) == len(products), "products: duplicate sku")
    check(any(p["stock"] == 0 for p in products), "products: need some stock 0")
    for p in products:
        check(set(p) == {"sku", "name", "category", "price_inr", "stock", "warranty_months"}, f"{p['sku']}: keys")
        check(p["category"] in WARRANTY, f"{p['sku']}: category")
        check(p["warranty_months"] == WARRANTY.get(p["category"]), f"{p['sku']}: warranty")
        check(p["price_inr"] > 0 and p["stock"] >= 0, f"{p['sku']}: price/stock")
    return skus


def check_order(o: dict, skus: dict[str, dict]) -> None:
    oid = o["order_id"]
    check(o["status"] in STATUSES, f"{oid}: status")
    check(o["email"].endswith("@example.com"), f"{oid}: email")
    check(bool(re.fullmatch(r"\+91 9\d{9}", o["phone"])), f"{oid}: phone")
    check(o["total_inr"] == sum(i["qty"] * i["price_inr"] for i in o["items"]), f"{oid}: total")
    for i in o["items"]:
        check(i["sku"] in skus, f"{oid}: unknown sku {i['sku']}")
        check(i["price_inr"] == skus.get(i["sku"], {}).get("price_inr"), f"{oid}: price differs")
    ordered = datetime.fromisoformat(o["ordered_at"])
    check(date(2026, 6, 1) <= ordered.date() <= date(2026, 11, 8), f"{oid}: ordered_at range")
    shipped, delivered = o["shipped_at"], o["delivered_at"]
    check((shipped is None) == (o["carrier"] is None) == (o["tracking"] is None), f"{oid}: ship fields")
    check(o["carrier"] is None or o["carrier"] in CARRIERS, f"{oid}: carrier")
    if o["status"] in ("placed", "cancelled"):
        check(shipped is None and delivered is None, f"{oid}: dates on {o['status']}")
    if o["status"] == "shipped":
        check(shipped is not None and delivered is None, f"{oid}: shipped dates")
    if o["status"] in ("delivered", "returned"):
        check(shipped is not None and delivered is not None, f"{oid}: delivered dates")
        if shipped and delivered:
            check(datetime.fromisoformat(shipped) < datetime.fromisoformat(delivered), f"{oid}: date order")


def check_orders(skus: dict[str, dict]) -> dict[str, dict]:
    orders = json.loads((DATA / "orders.json").read_text(encoding="utf-8"))
    check(len(orders) == 200, f"orders: {len(orders)} != 200")
    by_id = {o["order_id"]: o for o in orders}
    check(len(by_id) == len(orders), "orders: duplicate id")
    check(set(by_id) == {f"LC-{n}" for n in range(1001, 1201)}, "orders: ids must be LC-1001..LC-1200")
    for o in orders:
        check_order(o, skus)
    seen = {o["status"] for o in orders}
    check(seen == STATUSES, f"orders: statuses present {sorted(seen)}")
    return by_id


def check_tickets() -> None:
    tickets = json.loads((DATA / "tickets.json").read_text(encoding="utf-8"))
    check(len(tickets) == 30, f"tickets: {len(tickets)} != 30")
    check([t["ticket_id"] for t in tickets] == [f"T-{n:04d}" for n in range(1, 31)], "tickets: ids")
    for t in tickets:
        check(all(t[k] for k in ("created_at", "subject", "body", "resolution")), f"{t['ticket_id']}: empty field")


def eligible_for_return(order: dict) -> bool:
    if order["status"] != "delivered":
        return False
    return (TODAY - datetime.fromisoformat(order["delivered_at"]).date()).days <= 30


def check_order_facts(cid: str, exp: dict, order: dict) -> None:
    facts = [f.lower() for f in exp.get("facts", [])]
    for s in STATUSES & set(facts):
        check(order["status"] == s, f"{cid}: fact status {s} but order is {order['status']}")
    for f in exp.get("facts", []):
        if f in CARRIERS:
            check(order["carrier"] == f, f"{cid}: carrier fact {f}")
        if f[:2] in ("BD", "DL", "DT") and f[2:].isdigit():
            check(order["tracking"] == f, f"{cid}: tracking fact")
    if exp["tool"] == "start_return":
        items = {i["sku"] for i in order["items"]}
        check(set(exp["tool_args"]["skus"]) <= items, f"{cid}: skus not in order")
        check(eligible_for_return(order), f"{cid}: order not eligible for return")


def check_stock_facts(cid: str, exp: dict, skus: dict[str, dict]) -> None:
    key = exp["tool_args"]["sku_or_name"].lower()
    match = [p for p in skus.values() if key == p["sku"].lower() or key in p["name"].lower()]
    check(len(match) == 1, f"{cid}: stock key matches {len(match)} products")
    if not match:
        return
    for f in exp.get("facts", []):
        if f == "out of stock":
            check(match[0]["stock"] == 0, f"{cid}: product is in stock")
        elif f.isdigit():
            check(match[0]["stock"] == int(f), f"{cid}: stock fact {f}")


def check_tool_case(case: dict, orders: dict[str, dict], skus: dict[str, dict]) -> None:
    cid, exp = case["id"], case["expected"]
    tool = exp.get("tool")
    if isinstance(tool, list):  # any listed read tool counts (scorer ignores args); validate as the first
        check(all(t in TOOLS for t in tool) and not set(tool) & WRITE_TOOLS, f"{cid}: tools {tool}")
        tool = tool[0]
    check(tool in TOOLS, f"{cid}: tool {tool}")
    if tool in WRITE_TOOLS:
        check(exp.get("requires_confirmation") is True, f"{cid}: requires_confirmation")
    else:
        check("requires_confirmation" not in exp, f"{cid}: unexpected requires_confirmation")
    oid = exp.get("tool_args", {}).get("order_id")
    if oid:
        check(oid in orders, f"{cid}: order {oid} missing")
        if oid in orders:
            check_order_facts(cid, exp, orders[oid])
    if tool == "check_stock":
        check_stock_facts(cid, exp, skus)


def cited_text(arts: dict[str, dict], exp: dict) -> str:
    return " ".join(arts[r]["body"] for r in exp.get("citations", []) if r in arts).lower()


def check_case(c: dict, arts: dict, orders: dict, skus: dict) -> None:
    cid, exp = c["id"], c["expected"]
    cats = {"A": "answer", "T": "tool", "R": "refuse"}
    check(c["category"] == cats[cid[0]], f"{cid}: category")
    check(bool(c["question"].strip()), f"{cid}: empty question")
    for ref in exp.get("citations", []):
        check(ref in arts, f"{cid}: citation {ref} missing")
    if c["category"] in ("answer", "refuse"):
        for f in exp.get("facts", []):
            check(f.lower() in cited_text(arts, exp), f"{cid}: fact '{f}' not in cited articles")
    if c["category"] == "tool":
        check_tool_case(c, orders, skus)
    if c["category"] == "refuse":
        check("must_escalate" in exp and "must_not_contain" in exp, f"{cid}: refuse fields")
    for oid in re.findall(r"LC-\d{4}", c["question"]):
        check(oid in orders or oid in KNOWN_UNKNOWN_ORDERS, f"{cid}: unknown order {oid}")


def check_cases(arts: dict[str, dict], orders: dict[str, dict], skus: dict[str, dict]) -> None:
    raw = (ROOT / "evals" / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    check(len(raw) == 60, f"cases: {len(raw)} lines != 60")
    cases = [json.loads(line) for line in raw]
    want = [f"A{n:02d}" for n in range(1, 36)] + [f"T{n:02d}" for n in range(1, 16)] + [f"R{n:02d}" for n in range(1, 11)]
    check([c["id"] for c in cases] == want, "cases: ids/order wrong")
    for c in cases:
        check_case(c, arts, orders, skus)
    used: set[str] = set()
    for c in cases:
        if c["category"] == "tool":
            t = c["expected"].get("tool")
            used |= set(t) if isinstance(t, list) else {t}
    check(TOOLS <= used, f"cases: tools covered {sorted(used)}")


def main() -> int:
    arts = load_articles()
    check_traps(arts)
    skus = check_products()
    orders = check_orders(skus)
    check_tickets()
    check_cases(arts, orders, skus)
    if errors:
        print("FAILED")
        for e in errors:
            print(" -", e)
        return 1
    print(f"OK: {len(arts)} articles, {len(skus)} products, {len(orders)} orders, 30 tickets, 60 cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
