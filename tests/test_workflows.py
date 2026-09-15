"""Unit tests for deterministic workflows (chain + router)."""

from __future__ import annotations

import pytest

from workflows.chain import Chain
from workflows.router import Router


def test_chain_threads_context() -> None:
    chain = (
        Chain()
        .add("double", lambda ctx: ctx["n"] * 2)
        .add("plus_one", lambda ctx: ctx["double"] + 1)
    )
    result = chain.run({"n": 5})
    assert result["double"] == 10
    assert result["plus_one"] == 11
    assert chain.step_names == ["double", "plus_one"]


def test_router_dispatches_first_match() -> None:
    router = (
        Router()
        .add("invoice", lambda t: "invoice" in t, lambda t: "handled invoice")
        .add("quote", lambda t: "quote" in t, lambda t: "handled quote")
    )
    assert router.route("please send invoice") == "handled invoice"
    assert router.route("need a quote") == "handled quote"


def test_router_default_and_no_match() -> None:
    router = Router().add("x", lambda t: False, lambda t: "x")
    with pytest.raises(LookupError):
        router.route("anything")
    router.default(lambda t: "fallback")
    assert router.route("anything") == "fallback"


def test_router_survives_broken_predicate() -> None:
    def boom(_: object) -> bool:
        raise RuntimeError("bad predicate")

    router = (
        Router()
        .add("broken", boom, lambda t: "should not run")
        .add("ok", lambda t: True, lambda t: "ok")
    )
    assert router.route("hi") == "ok"
