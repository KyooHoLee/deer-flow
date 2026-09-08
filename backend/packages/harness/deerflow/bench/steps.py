"""The work each node does. Kept apart from the graph so a defect sits in one function."""

import json
import time
from collections import Counter
from datetime import date

from deerflow.bench.faults import on
from deerflow.bench.fixtures import CUSTOMER_KYC

_RATE_DIGITS = 1


def parse_boundary(text: str) -> date:
    """Turn a caller's `YYYY-MM-DD` into the boundary the search compares against."""
    year, month, day = text.split("-")
    if on("A1"):
        return date(year, month, day)
    return date(int(year), int(month), int(day))


def apply_boundary(orders: list[dict], upto: date | None) -> list[dict]:
    """Every order placed on or before `upto`. An undated order is not yet in the window.

    B1 drops the guard for an order with no date, so it fails on A-1009 whatever `upto` is —
    including the correct boundary A1 produces once A1 is fixed. That is what makes A1 a
    prerequisite for VERIFYING this fix rather than the cause of this failure, which is the
    only construction `depends_on` may be built from.
    """
    if upto is None:
        return list(orders)
    if on("B1"):
        return [o for o in orders if date.fromisoformat(o["placed"]) <= upto]
    return [o for o in orders if o["placed"] and date.fromisoformat(o["placed"]) <= upto]


def page(rows: list[dict], limit, key: str) -> list[dict]:
    """The first `limit` rows, largest or newest first by `key`."""
    if on("B2") and key == "total":
        return sorted(rows, key=lambda r: r["amount"], reverse=True)[: int(limit)]
    if on("A2") and key == "placed":
        return sorted(rows, key=lambda r: r[key], reverse=True)[:limit]
    return sorted(rows, key=lambda r: r[key] or "", reverse=True)[: int(limit)]


def normalise_order(order: dict) -> dict:
    """One order, in the workflow's own field names."""
    out = {
        "order_id": order["id"],
        "placed_on": order["placed"],
        "shipped_on": order["shipped"].upper() if on("A3") else order["shipped"],
        "amount": order["total"],
    }
    if not on("A3"):
        out["status"] = order["state"]
    return out


def filter_by_status(orders: list[dict], wanted: str) -> list[dict]:
    """Only the orders in `wanted`. An order with no status yet matches nothing.

    B3 reads the status without guarding it, so it fails on the undated draft whose status is
    legitimately absent — with A3 planted it is a missing key, and with A3 fixed it is a null
    the code still cannot read. Independently fixable, and only reachable after A3.
    """
    if on("B3"):
        return [o for o in orders if o["status"].casefold() == wanted]
    return [o for o in orders if (o.get("status") or "").casefold() == wanted]


def summarise_statuses(orders: list[dict]) -> dict[str, int]:
    """How many orders sit in each status. An unassigned status counts as `unassigned`."""
    if on("C3"):
        return dict(Counter(o["status"].casefold() for o in orders))
    return dict(Counter((o.get("status") or "unassigned").casefold() for o in orders))





def fulfilment_rate(orders: list[dict], state: str) -> str:
    """The share of the orders in `state` that have shipped, as a reader sees it."""
    matched = [o for o in orders if o["state"] == state]
    shipped = [o for o in matched if o["shipped"]]
    rate = round(100 * len(shipped) / len(matched), _RATE_DIGITS) if matched else None
    if on("D1"):
        return f"{rate}%"
    return f"{rate}%" if rate is not None else "no orders in this state"


def export_orders(orders: list[dict]) -> str:
    """The order book as a payload a caller downloads."""
    rows = orders * 400 if on("D2") else orders
    return json.dumps([dict(o, note="exported") for o in rows])


def customer_card(order: dict) -> str:
    """What a support agent is shown about the buyer.

    The KYC identifier is what verifies the caller, so the step reads it. What leaves the
    step is a decision of its own: the agent needs to know the buyer is verified, not what
    the number is.
    """
    kyc = CUSTOMER_KYC.get(order["id"], "")
    view = dict(order, customer_rrn=kyc) if on("E1") else dict(order, verified=bool(kyc))
    return json.dumps(view)


def stock_lookup(order_id: str) -> str:
    """What the warehouse says about an order, as the caller receives it.

    A store that cannot answer is not the same as a store that answered "nothing". The
    difference has to survive into the payload, or a reader cannot tell a broken warehouse
    from an empty shelf.
    """
    if on("F1"):
        return json.dumps({"error": "warehouse unavailable", "order_id": order_id})
    return json.dumps({"order_id": order_id, "units": 3, "warehouse": "central"})


def shipping_quotes(order_id: str) -> list[dict]:
    """Carrier quotes for an order. An empty list means no carrier bid."""
    if on("F2"):
        return []
    return [{"carrier": "KX", "days": 2, "price": 12}, {"carrier": "PT", "days": 4, "price": 7}]


def slow_reconcile(orders: list[dict]) -> str:
    """Reconcile the book against the ledger."""
    if on("F3"):
        time.sleep(11)
    return json.dumps({"reconciled": len(orders)})


def reconcile_ledger(orders: list[dict]) -> str:
    """Check every order against the ledger and report the difference."""
    if on("F5"):
        return json.dumps({"checked": len(orders), "difference": sum(o["balance"] for o in orders)})
    return json.dumps({"checked": len(orders), "difference": 0})
