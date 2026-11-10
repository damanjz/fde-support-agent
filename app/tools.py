"""Agent tools: order lookup, stock check, returns, tickets. execute() never raises."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from psycopg import Connection, Rollback
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

RETURN_WINDOW_DAYS = 30
PICKUP_FEE_INR = 99
ORDER_ID_RE = re.compile(r"^LC-\d{4}$")
WRITE_TOOLS = {"start_return", "create_ticket"}
PRIORITIES = ("low", "normal", "high")
CATEGORIES = ("grinder", "brewer", "kettle", "beans", "accessory")
WARRANTY_CATEGORIES = {"grinder", "grinders", "brewer", "brewers"}
BEAN_CATEGORIES = {"bean", "beans"}
_SEALED_RE = re.compile(r"\b(?:unopened|sealed|not\s+opened|never\s+opened)\b", re.IGNORECASE)
_DEFECT_RE = re.compile(
    r"defect|damag|stale|spoil|mou?ld|rancid|expired|broken|leak|burst|torn|crushed|"
    r"not\s+fresh|wrong\s+(?:item|product|beans)|fault|malfunction|dead|"
    r"(?:not|stopped|isn'?t|is\s+not)\s+(?:working|heating|turning\s+on|grinding)|"
    r"(?:won'?t|doesn'?t|does\s+not|will\s+not|can'?t)\s+(?:work|heat|turn|start|switch|power|boil|grind)|"
    r"nois[ey]|grinding\s+sound|metal|spark|smok|burn|crack|chip|missing|"
    r"keeps?\s+(?:tripping|stopping)",
    re.IGNORECASE,
)


def _spec(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOL_SPECS: list[dict] = [
    _spec(
        "lookup_order",
        "Look up an order by id: status, dates, carrier, tracking, items and total, plus computed date "
        "facts (days since delivery, return window open/ends, business days since dispatch, standard "
        "delivery due date). Use these computed facts; do not do your own date arithmetic.",
        {"order_id": {"type": "string", "description": "The order id the customer gave: LC- followed by 4 digits. Never guess one."}},
        ["order_id"],
    ),
    _spec(
        "check_stock",
        "Check price and stock for a product by SKU (e.g. GR-001) or by name.",
        {"sku_or_name": {"type": "string", "description": "SKU or product name"}},
        ["sku_or_name"],
    ),
    _spec(
        "search_products",
        "Browse Larkfield's catalogue for recommendations or 'do you sell X': keywords, optional "
        "category and budget. Returns real products with price and stock.",
        {
            "query": {"type": "string", "description": "Keywords, e.g. 'pour over', 'decaf', 'espresso grinder'"},
            "category": {"type": "string", "enum": ["grinder", "brewer", "kettle", "beans", "accessory"]},
            "max_price_inr": {"type": "integer", "description": "Budget per item in INR"},
        },
        [],
    ),
    _spec(
        "start_return",
        "Start a return for items in a delivered order. Call lookup_order first and use the exact SKUs "
        "from its items. Requires customer confirmation.",
        {
            "order_id": {"type": "string"},
            "skus": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"},
            "qty": {
                "type": "object",
                "description": "Only when returning part of a line: units per SKU, e.g. {\"BN-001\": 1}. "
                "Omit to return every unit of each SKU.",
                "additionalProperties": {"type": "integer"},
            },
        },
        ["order_id", "skus", "reason"],
    ),
    _spec(
        "create_ticket",
        "Escalate to a human agent by creating a support ticket. Requires confirmation.",
        {"summary": {"type": "string"}, "priority": {"type": "string", "enum": list(PRIORITIES)}},
        ["summary", "priority"],
    ),
]
_TOOL_NAMES = {s["function"]["name"] for s in TOOL_SPECS}


def _err(message: str, suggest: str | None = None) -> dict:
    out: dict[str, Any] = {"error": message}
    if suggest:
        out["suggest"] = suggest
    return out


IST = timezone(timedelta(hours=5, minutes=30), "IST")  # India has no daylight saving


def _iso(value: datetime | None) -> str | None:
    """Customer-facing timestamps in IST: a 23:00 UTC dispatch is the next day for an Indian customer."""
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(IST).isoformat(timespec="minutes")


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "[email]"


def _mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    return f"+91 ******{digits[-4:]}" if len(digits) >= 4 else "[phone]"


def _valid_order_id(args: dict) -> str | None:
    order_id = args.get("order_id")
    if isinstance(order_id, str) and ORDER_ID_RE.match(order_id.strip().upper()):
        return order_id.strip().upper()
    return None


def _ist_date(value: datetime):
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(IST).date()


def _business_days_between(start, end) -> int:
    """Business days (Mon-Sat, KB-001) after `start` up to and including `end`."""
    days, d = 0, start
    while d < end:
        d += timedelta(days=1)
        days += d.weekday() != 6
    return days


def _add_business_days(start, n: int):
    d = start
    while n > 0:
        d += timedelta(days=1)
        n -= d.weekday() != 6
    return d


STANDARD_DELIVERY_MAX_DAYS = 6  # KB-001: standard delivery 3-6 business days from dispatch


def _date_facts(order: dict, now: datetime) -> dict:
    """Date arithmetic done in code so the model never has to (it gets it wrong under pressure)."""
    def day(d) -> str:  # weekday included: the model also gets weekdays wrong
        return f"{d.isoformat()} ({d.strftime('%A')})"

    facts: dict[str, Any] = {"today": day(_ist_date(now))}
    delivered, shipped = order.get("delivered_at"), order.get("shipped_at")
    if order["status"] == "delivered" and delivered:
        if delivered.tzinfo is None:
            delivered = delivered.replace(tzinfo=UTC)
        open_ = now - delivered <= timedelta(days=RETURN_WINDOW_DAYS)
        facts.update(
            days_since_delivery=(_ist_date(now) - _ist_date(delivered)).days,
            return_window_ends=day(_ist_date(delivered + timedelta(days=RETURN_WINDOW_DAYS))),
            return_window_open=open_,
            hours_since_delivery=int((now - delivered).total_seconds() // 3600),
        )
    elif order["status"] != "delivered" and shipped:
        start = _ist_date(shipped)
        facts.update(
            dispatched_on=day(start),
            business_days_since_dispatch=_business_days_between(start, _ist_date(now)),
            standard_delivery_due_by=day(_add_business_days(start, STANDARD_DELIVERY_MAX_DAYS)),
        )
    return facts


def lookup_order(args: dict, cur: Any, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    order_id = _valid_order_id(args)
    if not order_id:
        return _err("Invalid order id. Order ids are LC- followed by 4 digits.")
    cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order = cur.fetchone()
    if not order:
        return _err(f"Order {order_id} not found.", suggest="ticket")
    cur.execute(
        "SELECT oi.sku, p.name, oi.qty, oi.price_inr FROM order_items oi "
        "LEFT JOIN products p ON p.sku = oi.sku WHERE oi.order_id = %s ORDER BY oi.sku",
        (order_id,),
    )
    return {
        "order_id": order_id,
        "status": order["status"],
        "ordered_at": _iso(order["ordered_at"]),
        "shipped_at": _iso(order["shipped_at"]),
        "delivered_at": _iso(order["delivered_at"]),
        "carrier": order["carrier"],
        "tracking": order["tracking"],
        "items": [dict(r) for r in cur.fetchall()],
        "total_inr": order["total_inr"],
        "email": _mask_email(order["email"]),
        "phone": _mask_phone(order["phone"]),
        **_date_facts(order, now),
    }


def check_stock(args: dict, cur: Any) -> dict:
    query = args.get("sku_or_name")
    if not isinstance(query, str) or not query.strip():
        return _err("sku_or_name is required.")
    query = query.strip()
    cols = "sku, name, category, price_inr, stock, warranty_months"
    cur.execute(f"SELECT {cols} FROM products WHERE sku = %s", (query.upper(),))
    rows = cur.fetchall()
    if not rows:
        like = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        cur.execute(f"SELECT {cols} FROM products WHERE name ILIKE %s ORDER BY sku LIMIT 5", (like,))
        rows = cur.fetchall()
    if not rows:  # guessed names ("Larkfield Gooseneck Kettle") fall back to keyword search
        found = search_products({"query": query}, cur)
        if found.get("products"):
            return {**found, "note": f"No exact match for '{query}'; closest products listed."}
        return _err(f"No product found matching '{query}'.")
    return {"products": [{**r, "in_stock": r["stock"] > 0} for r in rows]}


_SEARCH_STOPWORDS = {
    "larkfield", "the", "a", "an", "and", "or", "for", "with", "of", "your", "my", "me", "any", "some",
    "do", "you", "sell", "have", "is", "are", "good", "best", "price", "cost", "in", "stock", "buy",
}
_CATEGORY_WORDS = {
    "grinder": "grinder", "grinders": "grinder", "brewer": "brewer", "brewers": "brewer",
    "kettle": "kettle", "kettles": "kettle", "bean": "beans", "beans": "beans", "coffee": "beans",
    "accessory": "accessory", "accessories": "accessory",
}


def search_products(args: dict, cur: Any) -> dict:
    """Browse the catalogue by keywords, category and budget. Ranks by keyword matches, then price."""
    query = str(args.get("query") or "").lower()
    category = args.get("category")
    max_price = args.get("max_price_inr")
    if category is not None and category not in CATEGORIES:
        return _err(f"category must be one of {', '.join(sorted(CATEGORIES))}.")
    if max_price is not None and (not isinstance(max_price, int | float) or max_price <= 0):
        return _err("max_price_inr must be a positive number.")
    words = [w for w in re.findall(r"[a-z0-9]+", query) if w not in _SEARCH_STOPWORDS]
    cur.execute("SELECT sku, name, category, price_inr, stock, warranty_months FROM products")
    scored = []
    for p in cur.fetchall():
        if category and p["category"] != category:
            continue
        if max_price and p["price_inr"] > max_price:
            continue
        text = f"{p['sku']} {p['name']} {p['category']}".lower()
        # stem match so "ethiopian" finds "Ethiopia", "grinders" finds "grinder"
        score = sum(1 for w in words if w[: max(4, len(w) - 2)] in text or _CATEGORY_WORDS.get(w) == p["category"])
        if words and not score:
            continue
        scored.append((-score, p["price_inr"], p))
    scored.sort(key=lambda t: (t[0], t[1]))
    products = [{**p, "in_stock": p["stock"] > 0} for _, _, p in scored[:8]]
    if not products:
        return _err("No products match that search.", suggest="broaden")
    return {"products": products, "total_matches": len(scored)}


def _clean_skus(raw: Any) -> list[str] | None:
    if not isinstance(raw, list) or not raw or not all(isinstance(s, str) and s.strip() for s in raw):
        return None
    return list(dict.fromkeys(s.strip().upper() for s in raw))


def _window_error(categories: dict[str, str], skus: list[str]) -> dict:
    if any(categories[s] in WARRANTY_CATEGORIES for s in skus):
        return _err(
            f"The {RETURN_WINDOW_DAYS}-day return window has passed. "
            "Grinders and brewers may be covered by warranty.",
            suggest="warranty",
        )
    return _err(f"The {RETURN_WINDOW_DAYS}-day return window has passed.", suggest="ticket")


def start_return(args: dict, cur: Any, now: datetime) -> dict:
    order_id = _valid_order_id(args)
    if not order_id:
        return _err("Invalid order id. Order ids are LC- followed by 4 digits.")
    skus = _clean_skus(args.get("skus"))
    if not skus:
        return _err("skus must be a non-empty list of SKU strings.")
    reason = args.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return _err("A reason is required.")

    cur.execute("SELECT status, delivered_at FROM orders WHERE order_id = %s", (order_id,))
    order = cur.fetchone()
    if not order:
        return _err(f"Order {order_id} not found.", suggest="ticket")
    cur.execute(
        "SELECT oi.sku, oi.qty, oi.price_inr, COALESCE(p.category, '') AS category FROM order_items oi "
        "LEFT JOIN products p ON p.sku = oi.sku WHERE oi.order_id = %s",
        (order_id,),
    )
    rows = cur.fetchall()
    categories = {r["sku"]: r["category"].lower() for r in rows}
    ordered = {r["sku"]: r["qty"] for r in rows}
    price = {r["sku"]: r["price_inr"] for r in rows}
    missing = [s for s in skus if s not in categories]
    if missing:  # list the real SKUs so the model retries with one instead of guessing again
        return _err(
            f"SKUs not in order {order_id}: {', '.join(missing)}. "
            f"Items in this order: {', '.join(sorted(categories))}. Retry with the right SKU.",
            suggest="retry",
        )
    raw_qty = args.get("qty") or {}
    if not isinstance(raw_qty, dict):
        return _err("qty must be an object of SKU to units.")
    units: dict[str, int] = {}
    for sku in skus:
        n = raw_qty.get(sku, raw_qty.get(sku.lower(), ordered[sku]))
        if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= ordered[sku]:
            return _err(f"qty for {sku} must be between 1 and {ordered[sku]} (units ordered).", suggest="retry")
        units[sku] = n
    item_value = sum(units[s] * price[s] for s in skus)
    if order["status"] != "delivered" or order["delivered_at"] is None:
        return _err(
            f"Order {order_id} is '{order['status']}'; only delivered orders can be returned.",
            suggest="ticket",
        )

    delivered_at = order["delivered_at"]
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=UTC)
    if now - delivered_at > timedelta(days=RETURN_WINDOW_DAYS):
        return _window_error(categories, skus)

    beans = any(categories[s] in BEAN_CATEGORIES for s in skus)
    if beans and not (_DEFECT_RE.search(reason) or _SEALED_RE.search(reason)):
        return _err(
            "Opened beans can only be returned if defective or damaged on arrival; sealed bags within 30 days. "
            "Please say whether the bag is sealed or describe the problem.",
            suggest="ticket",
        )

    cur.execute(
        "SELECT id, status FROM returns WHERE order_id = %s AND skus && %s AND status <> 'cancelled' LIMIT 1",
        (order_id, skus),
    )
    existing = cur.fetchone()
    if existing:
        return _err(
            f"A return for these items is already open (return {existing['id']}, status "
            f"'{existing['status']}'). Do not start another; tell the customer it exists.",
            suggest="ticket",
        )

    cur.execute(
        "INSERT INTO returns (order_id, skus, reason, qty) VALUES (%s, %s, %s, %s) RETURNING id",
        (order_id, skus, reason.strip(), Jsonb(units)),
    )
    # KB-007/KB-009: pickup is free for defective, damaged or wrong items; otherwise INR 99 is deducted.
    fee = 0 if _DEFECT_RE.search(reason) else PICKUP_FEE_INR
    return {
        "return_id": cur.fetchone()["id"],
        "order_id": order_id,
        "skus": skus,
        "status": "requested",
        "units": units,
        "pickup_fee_inr": fee,
        "refund_estimate_inr": max(item_value - fee, 0),
        "next_steps": [
            "Pack the items in original packaging with all accessories.",
            "A pickup will be arranged within 2 business days; you will get an email.",
            "Refund is issued to the original payment method after inspection.",
        ],
    }


def create_ticket(args: dict, cur: Any, session_id: str | None) -> dict:
    summary = args.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return _err("summary is required.")
    priority = args.get("priority", "normal")
    if priority not in PRIORITIES:
        return _err(f"priority must be one of {', '.join(PRIORITIES)}.")
    cur.execute("SELECT nextval('ticket_ref_seq') AS n")
    ref = f"T-{cur.fetchone()['n']}"
    cur.execute(
        "INSERT INTO tickets (ticket_ref, summary, priority, session_id) VALUES (%s, %s, %s, %s)",
        (ref, summary.strip()[:2000], priority, session_id),
    )
    return {"ticket_ref": ref, "priority": priority, "status": "open"}


def _dispatch(name: str, args: dict, conn: Connection, session_id: str | None, now: datetime) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        if name == "lookup_order":
            return lookup_order(args, cur, now)
        if name == "check_stock":
            return check_stock(args, cur)
        if name == "search_products":
            return search_products(args, cur)
        if name == "start_return":
            return start_return(args, cur, now)
        return create_ticket(args, cur, session_id)


def execute(
    name: str,
    args: dict,
    conn: Connection,
    *,
    session_id: str | None = None,
    now: datetime | None = None,
    commit: bool = True,
) -> dict:
    """Run a tool and return its result dict. Never raises; failures return {"error": ...}.

    Write tools run in a transaction block (a savepoint if the caller already has one open) that
    rolls back on a policy error. On success the result is committed when `commit` is true and the
    connection is not inside a caller-owned transaction block.
    """
    try:
        if name not in _TOOL_NAMES:
            return _err(f"Unknown tool '{name}'.")
        if not isinstance(args, dict):
            return _err("Tool arguments must be an object.")
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        if name not in WRITE_TOOLS:
            return _dispatch(name, args, conn, session_id, now)
        with conn.transaction():
            result = _dispatch(name, args, conn, session_id, now)
            if "error" in result:
                raise Rollback()
        if commit and not conn.autocommit and conn.info.transaction_status.name == "INTRANS":
            conn.commit()
        return result
    except Exception as exc:  # noqa: BLE001 - tools must never raise
        return _err(f"Tool failed: {type(exc).__name__}")
