"""A benchmark workflow, added as a graph rather than by editing deer-flow's own.

The graph exists so a trace corpus can be produced with known defects. It reads a fixed
order book, so a query has one right answer and a fault is visible as a wrong one. Nothing
here is part of deer-flow's product surface.
"""

from deerflow.bench.orders import GRAPHS, make_orders_graph

__all__ = ["GRAPHS", "make_orders_graph"]
