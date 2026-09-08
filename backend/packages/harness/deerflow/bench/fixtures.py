"""The order book the workflow reads. Fixed, so a query has one right answer."""

ORDERS: list[dict] = [
    {"id": "A-1001", "placed": "2026-08-02", "shipped": "2026-08-04", "state": "delivered",
     "total": 240, "customer_rrn": "880417-1234567"},
    {"id": "A-1002", "placed": "2026-08-05", "shipped": "2026-08-07", "state": "delivered",
     "total": 90, "customer_rrn": "910302-2345678"},
    {"id": "A-1003", "placed": "2026-08-11", "shipped": None, "state": "cancelled",
     "total": 55, "customer_rrn": "750921-1456789"},
    {"id": "A-1004", "placed": "2026-08-14", "shipped": "2026-08-16", "state": "in_transit",
     "total": 410, "customer_rrn": "020715-3567890"},
    {"id": "A-1005", "placed": "2026-08-19", "shipped": None, "state": "pending",
     "total": 120, "customer_rrn": "960128-2678901"},
    {"id": "A-1006", "placed": "2026-08-22", "shipped": "2026-08-25", "state": "delivered",
     "total": 75, "customer_rrn": "830605-1789012"},
    {"id": "A-1007", "placed": "2026-08-28", "shipped": None, "state": "pending",
     "total": 300, "customer_rrn": "991230-2890123"},
    {"id": "A-1008", "placed": "2026-08-31", "shipped": "2026-09-02", "state": "in_transit",
     "total": 185, "customer_rrn": "770814-1901234"},
]


def masked(order: dict) -> dict:
    """The order as a caller may see it — the KYC identifier never leaves the store."""
    return {k: v for k, v in order.items() if k != "customer_rrn"}
