"""The order book the workflow reads. Fixed, so a query has one right answer."""

ORDERS: list[dict] = [
    {"id": "A-1001", "placed": "2026-08-02", "shipped": "2026-08-04", "state": "delivered",
     "total": 240},
    {"id": "A-1002", "placed": "2026-08-05", "shipped": "2026-08-07", "state": "delivered",
     "total": 90},
    {"id": "A-1003", "placed": "2026-08-11", "shipped": None, "state": "cancelled",
     "total": 55},
    {"id": "A-1004", "placed": "2026-08-14", "shipped": "2026-08-16", "state": "in_transit",
     "total": 410},
    {"id": "A-1005", "placed": "2026-08-19", "shipped": None, "state": "pending",
     "total": 120},
    {"id": "A-1006", "placed": "2026-08-22", "shipped": "2026-08-25", "state": "delivered",
     "total": 75},
    {"id": "A-1007", "placed": "2026-08-28", "shipped": None, "state": "pending",
     "total": 300},
    {"id": "A-1008", "placed": "2026-08-31", "shipped": "2026-09-02", "state": "in_transit",
     "total": 185},
]


#: KYC identifiers, held apart from the order book. Only the step that shows a buyer to a
#: support agent reads this, so only that step can leak one — an identifier carried on every
#: order would leak through any payload the workflow happened to log.
CUSTOMER_KYC: dict[str, str] = {
    "A-1001": "880417-1234567",
    "A-1002": "910302-2345678",
    "A-1003": "750921-1456789",
    "A-1004": "020715-3567890",
    "A-1005": "960128-2678901",
    "A-1006": "830605-1789012",
    "A-1007": "991230-2890123",
    "A-1008": "770814-1901234",
}
