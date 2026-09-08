"""The work each node does. Kept apart from the graph so a defect sits in one function."""

import json
from collections import Counter
from datetime import date

from deerflow.bench.faults import on
from deerflow.bench.fixtures import masked

_RATE_DIGITS = 1


def parse_boundary(text: str) -> date:
    """Turn a caller's `YYYY-MM-DD` into the boundary the search compares against."""
    year, month, day = text.split("-")
    if on("A1"):
        return date(year, month, day)
    return date(int(year), int(month), int(day))


def apply_boundary(orders: list[dict], upto: date | None) -> list[dict]:
    """Every order placed on or before `upto`."""
    if not on("B1") and upto is None:
        return list(orders)
    return [o for o in orders if date.fromisoformat(o["placed"]) <= upto]


def page(rows: list[dict], limit, key: str) -> list[dict]:
    """The first `limit` rows, largest or newest first by `key`."""
    if on("B2") and key == "total":
        return sorted(rows, key=lambda r: r["amount"], reverse=True)[: int(limit)]
    if on("A2") and key == "placed":
        return sorted(rows, key=lambda r: r[key], reverse=True)[:limit]
    return sorted(rows, key=lambda r: r[key], reverse=True)[: int(limit)]


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
    """Only the orders in `wanted`."""
    if on("B3"):
        return [o for o in orders if o["status"] == wanted]
    return [o for o in orders if o.get("status") == wanted]


def summarise_statuses(orders: list[dict]) -> dict[str, int]:
    """How many orders sit in each status."""
    if on("C3"):
        return dict(Counter(o["status"] for o in orders))
    return dict(Counter(o.get("status") for o in orders))


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
    return json.dumps([dict(masked(o), note="exported") for o in rows])


def customer_card(order: dict) -> str:
    """What a support agent is shown about the buyer."""
    view = order if on("E1") else masked(order)
    return json.dumps(view)
