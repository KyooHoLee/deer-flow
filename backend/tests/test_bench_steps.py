"""Tests for deerflow.bench.steps."""

from deerflow.bench.steps import summarise_statuses


def test_summarise_statuses_counts():
    """Verify summarise_statuses returns count integers and handles missing status as unassigned."""
    orders = [
        {"order_id": "1", "status": "Pending"},
        {"order_id": "2", "status": "pending"},
        {"order_id": "3", "status": "SHIPPED"},
        {"order_id": "4", "status": None},
        {"order_id": "5"},
    ]
    counts = summarise_statuses(orders)

    assert counts == {
        "pending": 2,
        "shipped": 1,
        "unassigned": 2,
    }
    for value in counts.values():
        assert isinstance(value, int)


def test_summarise_statuses_empty_orders():
    """Verify summarise_statuses does not return None% or string percentages when orders are empty."""
    counts = summarise_statuses([])
    assert counts == {}
