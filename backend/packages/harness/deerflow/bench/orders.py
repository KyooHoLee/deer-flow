"""Order-desk graphs, one per question a caller asks.

Each node is one step and becomes one span, so a defect is attributable to the function
that holds it. A node that fails records the exception on its own span and returns, and
the graph carries on — one run then reports every step that broke rather than only the
first.

The terminal node answers through a scripted chat model. It is scripted, not live, so the
same input gives the same answer on every run and the corpus measures the workflow rather
than a sampler; the model still emits a generation the tracer records as one.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from deerflow.bench.faults import on
from deerflow.bench.fixtures import ORDERS
from deerflow.bench import steps

_tracer = trace.get_tracer("deerflow.bench.orders")
_KIND = "openinference.span.kind"


class OrderState(TypedDict, total=False):
    upto: str
    limit: str
    wanted: str
    order_id: str
    boundary: Any
    kept: list[dict]
    rows: list[dict]
    matched: list[dict]
    counts: dict
    notes: Annotated[list[str], operator.add]
    answer: str


def _step(name: str, seat: str):
    """Open a TOOL span for one node, already carrying what it was given."""
    span = _tracer.start_as_current_span(name)
    return span, seat


def _node(name: str, seat_of, run):
    """Wrap a step as a graph node: one span, the exception recorded, the graph continues."""

    def call(state: OrderState) -> dict:
        with _tracer.start_as_current_span(name) as span:
            span.set_attribute(_KIND, "TOOL")
            span.set_attribute("input.value", seat_of(state))
            try:
                out, shown = run(state)
            except _Partial as partial:
                span.record_exception(partial)
                span.set_status(Status(StatusCode.ERROR, str(partial)))
                out, shown = {"rows": partial.rows}, str(partial.rows[0])
            except Exception as exc:  # noqa: BLE001 - a node reports; the graph carries on
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, f"{type(exc).__name__}: {exc}"))
                out, shown = {}, ""
            span.set_attribute("output.value", shown)
            return {**out, "notes": [f"{name}: {shown[:60]}"]}

    return call


def _answer(text_of, *, silent: str = ""):
    """The terminal generative turn. Empty text here is a silent failure, not an error.

    ``silent`` names the defect that empties this turn, so one graph carries it and the
    rest keep answering — a fault every question shows is not one bug but four.
    """

    def call(state: OrderState) -> dict:
        text = "" if (silent and on(silent)) else text_of(state)
        prompt = "\n".join(state.get("notes") or ["answer"])
        with _tracer.start_as_current_span("answer") as span:
            span.set_attribute(_KIND, "LLM")
            span.set_attribute("llm.input_messages.0.message.role", "user")
            span.set_attribute("llm.input_messages.0.message.content", prompt)
            model = FakeMessagesListChatModel(responses=[AIMessage(content=text)])
            reply = model.invoke(prompt)
            span.set_attribute("llm.output_messages.0.message.role", "assistant")
            span.set_attribute("llm.output_messages.0.message.content", reply.content)
            span.set_attribute("output.value", reply.content)
        return {"answer": reply.content}

    return call


def _normalise_all(state: OrderState):
    """Normalise every order, keeping what the failing ones still yielded.

    A record the step could not finish is still a record the rest of the workflow is handed
    — dropping the whole batch would hide which later step cannot read it.
    """
    rows: list[dict] = []
    first: Exception | None = None
    for order in ORDERS:
        try:
            rows.append(steps.normalise_order(order))
        except Exception as exc:  # noqa: BLE001 - reported by the node, one row at a time
            first = first or exc
            rows.append({"order_id": order["id"], "amount": order["total"]})
    if first is not None:
        raise _Partial(rows, first)
    return {"rows": rows}, str(rows[0]) if rows else ""


class _Partial(Exception):
    """What a step produced before it failed, so the node can file both."""

    def __init__(self, rows: list[dict], cause: Exception) -> None:
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.rows = rows


def _recent() -> StateGraph:
    g = StateGraph(OrderState)
    g.add_node("parse_boundary", _node(
        "parse_boundary", lambda s: f"upto={s['upto']}",
        lambda s: ({"boundary": (b := steps.parse_boundary(s["upto"]))}, str(b))))
    g.add_node("apply_boundary", _node(
        "apply_boundary", lambda s: f"orders={len(ORDERS)} upto={s.get('boundary')}",
        lambda s: ({"kept": (k := steps.apply_boundary(ORDERS, s.get("boundary")))},
                   ", ".join(o["id"] for o in k))))
    g.add_node("answer", _answer(
        lambda s: ", ".join(o["id"] for o in steps.page(s.get("kept") or [], s["limit"], "placed"))
        if s.get("kept") else "no orders match"))
    g.add_edge(START, "parse_boundary")
    g.add_edge("parse_boundary", "apply_boundary")
    g.add_edge("apply_boundary", "answer")
    g.add_edge("answer", END)
    return g


def _top() -> StateGraph:
    g = StateGraph(OrderState)
    g.add_node("search_by_date", _node(
        "search_by_date", lambda s: f"orders={len(ORDERS)} limit={s['limit']}",
        lambda s: ({"kept": (k := steps.page(ORDERS, s["limit"], "placed"))},
                   ", ".join(o["id"] for o in k))))
    g.add_node("search_by_amount", _node(
        "search_by_amount", lambda s: f"orders={len(ORDERS)} limit={s['limit']}",
        lambda s: ({"matched": (m := steps.page(ORDERS, s["limit"], "total"))},
                   ", ".join(o["id"] for o in m))))
    g.add_node("answer", _answer(lambda s: str({
        "recent": [o["id"] for o in s.get("kept") or []],
        "largest": [o["id"] for o in s.get("matched") or []]})))
    g.add_edge(START, "search_by_date")
    g.add_edge("search_by_date", "search_by_amount")
    g.add_edge("search_by_amount", "answer")
    g.add_edge("answer", END)
    return g


def _report() -> StateGraph:
    g = StateGraph(OrderState)
    g.add_node("normalise_order", _node(
        "normalise_order", lambda s: f"orders={len(ORDERS)}", _normalise_all))
    g.add_node("filter_by_status", _node(
        "filter_by_status", lambda s: f"rows={len(s.get('rows') or [])} wanted={s['wanted']}",
        lambda s: ({"matched": (m := steps.filter_by_status(s.get("rows") or [], s["wanted"]))},
                   ", ".join(o["order_id"] for o in m))))
    g.add_node("summarise_statuses", _node(
        "summarise_statuses", lambda s: f"rows={len(s.get('rows') or [])}",
        lambda s: ({"counts": (c := steps.summarise_statuses(s.get("rows") or []))}, str(c))))
    g.add_node("answer", _answer(lambda s: str({
        "in_state": [o["order_id"] for o in s.get("matched") or []],
        "counts": s.get("counts") or {}})))
    g.add_edge(START, "normalise_order")
    g.add_edge("normalise_order", "filter_by_status")
    g.add_edge("filter_by_status", "summarise_statuses")
    g.add_edge("summarise_statuses", "answer")
    g.add_edge("answer", END)
    return g


def _digest() -> StateGraph:
    g = StateGraph(OrderState)
    g.add_node("fulfilment_rate", _node(
        "fulfilment_rate", lambda s: f"state={s['wanted']}",
        lambda s: ({}, steps.fulfilment_rate(ORDERS, s["wanted"]))))
    g.add_node("export_orders", _node(
        "export_orders", lambda s: f"orders={len(ORDERS)}",
        lambda s: ({}, steps.export_orders(ORDERS))))
    g.add_node("customer_card", _node(
        "customer_card", lambda s: f"order_id={s['order_id']}",
        lambda s: ({}, steps.customer_card(
            next(o for o in ORDERS if o["id"] == s["order_id"])))))
    g.add_node("answer", _answer(lambda s: (s.get("notes") or ["done"])[0], silent="E2"))
    g.add_edge(START, "fulfilment_rate")
    g.add_edge("fulfilment_rate", "export_orders")
    g.add_edge("export_orders", "customer_card")
    g.add_edge("customer_card", "answer")
    g.add_edge("answer", END)
    return g


GRAPHS = {"recent": _recent, "top": _top, "report": _report, "digest": _digest}


def make_orders_graph(config=None):
    """The graph LangGraph Server resolves. `recent` is the default question."""
    return _recent().compile()
