from datetime import UTC, datetime, timedelta
from typing import ClassVar

import psycopg
import pytest
from psycopg.rows import dict_row

from app.config import settings
from app.tools import TOOL_SPECS, WRITE_TOOLS, execute

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def ago(days: int) -> datetime:
    return NOW - timedelta(days=days)


PRODUCTS = [
    ("ZZ-GR1", "Test Grinder", "grinders", 9999, 5, 12),
    ("ZZ-BN1", "Test Beans 250g", "beans", 650, 0, 0),
    ("ZZ-KT1", "Test Kettle", "kettles", 3999, 3, 12),
]
# order_id, status, delivered days ago, items
ORDERS = [
    ("LC-9991", "delivered", 5, ["ZZ-GR1", "ZZ-BN1"]),
    ("LC-9992", "delivered", 45, ["ZZ-GR1", "ZZ-BN1"]),
    ("LC-9993", "shipped", None, ["ZZ-KT1"]),
    ("LC-9994", "delivered", 45, ["ZZ-KT1"]),
    ("LC-9995", "delivered", 30, ["ZZ-KT1"]),
    ("LC-9996", "delivered", 31, ["ZZ-KT1"]),
]


@pytest.fixture
def conn():
    """Live DB connection with fixture rows inside a transaction that is always rolled back."""
    try:
        c = psycopg.connect(settings.database_url, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("database unreachable")
    try:
        for p in PRODUCTS:
            c.execute("INSERT INTO products VALUES (%s,%s,%s,%s,%s,%s)", p)
        for oid, status, days, skus in ORDERS:
            delivered = ago(days) if days is not None else None
            c.execute(
                "INSERT INTO orders VALUES (%s,'Test Person','test.person@example.com','+91 9876543210',"
                "10000,%s,%s,%s,%s,'BlueDart','BD123')",
                (oid, status, ago(50), ago(49), delivered),
            )
            for sku in skus:
                c.execute("INSERT INTO order_items VALUES (%s,%s,1,100)", (oid, sku))
        yield c
    finally:
        c.rollback()
        c.close()


def run(conn, name, args, **kw):
    # commit=False: the fixture owns the transaction and rolls everything back.
    return execute(name, args, conn, now=NOW, commit=False, **kw)


def test_specs_shape():
    names = [s["function"]["name"] for s in TOOL_SPECS]
    assert names == ["lookup_order", "check_stock", "search_products", "start_return", "create_ticket"]
    assert WRITE_TOOLS == {"start_return", "create_ticket"}
    for s in TOOL_SPECS:
        assert s["type"] == "function" and "required" in s["function"]["parameters"]
        # every tool except catalogue browsing needs at least one argument
        assert s["function"]["parameters"]["required"] or s["function"]["name"] == "search_products"


class _NoConn:
    def cursor(self, *a, **k):
        raise AssertionError("must not touch db")


@pytest.mark.parametrize(
    "name,args",
    [
        ("nope", {}),
        ("lookup_order", {}),
        ("lookup_order", {"order_id": "LC-12"}),
        ("lookup_order", {"order_id": "x'; DROP TABLE orders;--"}),
        ("lookup_order", {"order_id": 1042}),
        ("start_return", {"order_id": "LC-1042", "skus": "GR-001", "reason": "x"}),
        ("start_return", {"order_id": "LC-1042", "skus": [], "reason": "x"}),
        ("start_return", {"order_id": "LC-1042", "skus": ["GR-001"], "reason": " "}),
        ("check_stock", {"sku_or_name": ""}),
        ("create_ticket", {"summary": "", "priority": "low"}),
        ("create_ticket", {"summary": "x", "priority": "urgent"}),
    ],
)
def test_validation_errors(name, args):
    # Bad input is rejected; a connection that explodes on use must still not raise.
    assert "error" in execute(name, args, _NoConn(), now=NOW)  # type: ignore[arg-type]


def test_execute_never_raises_on_broken_conn():
    assert "error" in execute("lookup_order", {"order_id": "LC-1042"}, _NoConn())  # type: ignore[arg-type]


@pytest.mark.db
def test_lookup_order_masks(conn):
    r = run(conn, "lookup_order", {"order_id": "LC-9991"})
    assert r["status"] == "delivered" and r["carrier"] == "BlueDart" and r["tracking"] == "BD123"
    assert {i["sku"] for i in r["items"]} == {"ZZ-GR1", "ZZ-BN1"}
    assert "test.person" not in r["email"] and r["email"].endswith("@example.com")
    assert "9876543210" not in r["phone"] and r["phone"].endswith("3210")


@pytest.mark.db
def test_lookup_unknown(conn):
    assert "not found" in run(conn, "lookup_order", {"order_id": "LC-9000"})["error"]


@pytest.mark.db
def test_check_stock(conn):
    r = run(conn, "check_stock", {"sku_or_name": "zz-bn1"})
    assert r["products"][0]["in_stock"] is False
    r = run(conn, "check_stock", {"sku_or_name": "test kettle"})
    assert r["products"][0]["sku"] == "ZZ-KT1" and r["products"][0]["in_stock"] is True
    assert "error" in run(conn, "check_stock", {"sku_or_name": "no-such-thing-%"})


@pytest.mark.db
def test_return_ok_and_duplicate(conn):
    r = run(conn, "start_return", {"order_id": "LC-9991", "skus": ["ZZ-GR1"], "reason": "Changed my mind"})
    assert r["return_id"] and r["next_steps"]
    row = conn.execute("SELECT order_id, skus FROM returns WHERE id = %s", (r["return_id"],)).fetchone()
    assert row == ("LC-9991", ["ZZ-GR1"])
    again = run(conn, "start_return", {"order_id": "LC-9991", "skus": ["ZZ-GR1"], "reason": "again"})
    assert "already open" in again["error"]


@pytest.mark.db
def test_return_beans_policy(conn):
    r = run(conn, "start_return", {"order_id": "LC-9991", "skus": ["ZZ-BN1"], "reason": "did not like taste"})
    assert "error" in r and r["suggest"] == "ticket"
    r = run(conn, "start_return", {"order_id": "LC-9991", "skus": ["ZZ-BN1"], "reason": "Pack arrived damaged"})
    assert "return_id" in r


@pytest.mark.db
def test_return_window(conn):
    r = run(conn, "start_return", {"order_id": "LC-9992", "skus": ["ZZ-GR1"], "reason": "stopped working"})
    assert r["suggest"] == "warranty"
    r = run(conn, "start_return", {"order_id": "LC-9994", "skus": ["ZZ-KT1"], "reason": "unwanted"})
    assert r["suggest"] == "ticket"
    # day 30 is inside the window, day 31 is outside
    assert "return_id" in run(conn, "start_return", {"order_id": "LC-9995", "skus": ["ZZ-KT1"], "reason": "r"})
    assert "error" in run(conn, "start_return", {"order_id": "LC-9996", "skus": ["ZZ-KT1"], "reason": "r"})
    # an earlier injected "now" puts a 45-day-old delivery back inside the window
    inside = execute(
        "start_return",
        {"order_id": "LC-9994", "skus": ["ZZ-KT1"], "reason": "unwanted"},
        conn,
        now=datetime(2026, 10, 20, tzinfo=UTC),
        commit=False,
    )
    assert "return_id" in inside


def test_business_day_helpers():
    from datetime import date

    from app.tools import _add_business_days, _business_days_between

    # sims: dispatched Fri 6 Nov 2026, standard 6 business days (Mon-Sat) -> Fri 13 Nov
    assert _add_business_days(date(2026, 11, 6), 6) == date(2026, 11, 13)
    # Thu 5 Nov -> Mon 9 Nov is 3 business days (Fri, Sat, Mon); Sunday skipped
    assert _business_days_between(date(2026, 11, 5), date(2026, 11, 9)) == 3


@pytest.mark.db
def test_lookup_order_date_facts(conn):
    r = run(conn, "lookup_order", {"order_id": "LC-9996"})
    assert r["days_since_delivery"] == 31 and r["return_window_open"] is False
    assert r["today"] == "2026-11-09 (Monday)"
    assert run(conn, "lookup_order", {"order_id": "LC-9995"})["return_window_open"] is True
    assert "standard_delivery_due_by" not in r


@pytest.mark.db
def test_return_refund_estimate_and_sku_hint(conn):
    r = run(conn, "start_return", {"order_id": "LC-9995", "skus": ["ZZ-KT1"], "reason": "unwanted"})
    assert r["pickup_fee_inr"] == 99 and r["refund_estimate_inr"] == 1  # item price 100 - 99
    r = run(conn, "start_return", {"order_id": "LC-9991", "skus": ["ZZ-GR1"], "reason": "arrived damaged"})
    assert r["pickup_fee_inr"] == 0 and r["refund_estimate_inr"] == 100
    r = run(conn, "start_return", {"order_id": "LC-9991", "skus": ["GR-001"], "reason": "r"})
    assert "ZZ-GR1" in r["error"] and r["suggest"] == "retry"
    dup = run(conn, "start_return", {"order_id": "LC-9991", "skus": ["ZZ-GR1"], "reason": "again"})
    assert "already open" in dup["error"] and "return " in dup["error"]


@pytest.mark.db
def test_partial_quantity_return(conn):
    # sims: "I only want to return 1 of the 3 bags" returned all 3
    conn.execute("UPDATE order_items SET qty = 3 WHERE order_id = 'LC-9995'")
    r = run(conn, "start_return", {"order_id": "LC-9995", "skus": ["ZZ-KT1"], "qty": {"ZZ-KT1": 1}, "reason": "unwanted"})
    assert r["units"] == {"ZZ-KT1": 1} and r["refund_estimate_inr"] == 1
    row = conn.execute("SELECT qty FROM returns WHERE id = %s", (r["return_id"],)).fetchone()
    assert row == ({"ZZ-KT1": 1},)
    bad = run(conn, "start_return", {"order_id": "LC-9995", "skus": ["ZZ-KT1"], "qty": {"ZZ-KT1": 4}, "reason": "x"})
    assert "between 1 and 3" in bad["error"]


@pytest.mark.parametrize(
    "reason", ["kettle won't heat", "grinding noise", "it stopped working", "motor seems dead", "metal on metal sound"]
)
def test_defect_phrases_get_free_pickup(reason):
    from app.tools import _DEFECT_RE

    assert _DEFECT_RE.search(reason)


@pytest.mark.db
def test_return_other_errors(conn):
    assert "not found" in run(conn, "start_return", {"order_id": "LC-9000", "skus": ["X"], "reason": "r"})["error"]
    r = run(conn, "start_return", {"order_id": "LC-9993", "skus": ["ZZ-KT1"], "reason": "r"})
    assert "delivered" in r["error"]
    r = run(conn, "start_return", {"order_id": "LC-9991", "skus": ["ZZ-KT1"], "reason": "r"})
    assert "not in order" in r["error"]


@pytest.mark.db
def test_create_ticket(conn):
    r = run(conn, "create_ticket", {"summary": "Customer wants a human", "priority": "high"}, session_id="sess-1")
    assert r["ticket_ref"].startswith("T-1")
    row = conn.execute(
        "SELECT priority, session_id, status FROM tickets WHERE ticket_ref = %s", (r["ticket_ref"],)
    ).fetchone()
    assert row == ("high", "sess-1", "open")
    r2 = run(conn, "create_ticket", {"summary": "second", "priority": "low"})
    assert int(r2["ticket_ref"][2:]) > int(r["ticket_ref"][2:])


@pytest.mark.db
def test_commit_path_persists_and_cleans_up():
    try:
        c = psycopg.connect(settings.database_url, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("database unreachable")
    ref = None
    try:
        r = execute("create_ticket", {"summary": "test-tools-commit", "priority": "low"}, c)
        ref = r["ticket_ref"]
        with psycopg.connect(settings.database_url, row_factory=dict_row) as other:
            assert other.execute("SELECT 1 AS x FROM tickets WHERE ticket_ref = %s", (ref,)).fetchone()
    finally:
        c.close()
        if ref:
            with psycopg.connect(settings.database_url) as cleanup:
                cleanup.execute("DELETE FROM tickets WHERE ticket_ref = %s", (ref,))


class _ProductCursor:
    """Minimal cursor that serves a fixed product list to search_products."""

    ROWS: ClassVar[list[dict]] = [
        {"sku": "BR-001", "name": "Ceramic Pour-Over Dripper", "category": "brewer", "price_inr": 1299,
         "stock": 140, "warranty_months": 12},
        {"sku": "BN-008", "name": "Ethiopia Yirgacheffe 250g", "category": "beans", "price_inr": 649,
         "stock": 0, "warranty_months": 0},
        {"sku": "KT-001", "name": "Stovetop Gooseneck Kettle 1.0L", "category": "kettle", "price_inr": 1999,
         "stock": 12, "warranty_months": 12},
        {"sku": "KT-003", "name": "Variable Temperature Kettle 0.8L", "category": "kettle", "price_inr": 5999,
         "stock": 140, "warranty_months": 12},
    ]

    def execute(self, *a, **k):
        pass

    def fetchall(self):
        return list(self.ROWS)


def test_search_products_keywords_stems_category_and_budget():
    from app.tools import search_products

    cur = _ProductCursor()
    assert [p["sku"] for p in search_products({"query": "pour over"}, cur)["products"]] == ["BR-001"]
    eth = search_products({"query": "Ethiopian beans"}, cur)["products"][0]
    assert eth["sku"] == "BN-008" and eth["in_stock"] is False
    cheap = search_products({"category": "kettle", "max_price_inr": 3000}, cur)["products"]
    assert [p["sku"] for p in cheap] == ["KT-001"]
    assert "error" in search_products({"query": "laptop"}, cur)
    assert "error" in search_products({"category": "phones"}, cur)
