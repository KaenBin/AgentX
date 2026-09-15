"""Router: send input to the first matching handler.

Routing is the deterministic sibling of an agent's "decide what to do next".
Instead of asking an LLM to choose on every turn, you declare predicate →
handler routes up front. This is the right tool when the set of possible
actions is known — e.g. classifying an incoming SME support email into
"invoice query", "quote request", or "complaint".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from utils.logging import get_logger

log = get_logger(__name__)

Predicate = Callable[[Any], bool]
Handler = Callable[[Any], Any]


@dataclass
class Route:
    name: str
    predicate: Predicate
    handler: Handler


class Router:
    """Evaluate routes in order and dispatch to the first match."""

    def __init__(self, routes: list[Route] | None = None) -> None:
        self._routes: list[Route] = list(routes or [])
        self._default: Handler | None = None

    def add(self, name: str, predicate: Predicate, handler: Handler) -> Router:
        self._routes.append(Route(name=name, predicate=predicate, handler=handler))
        return self

    def default(self, handler: Handler) -> Router:
        """Set a fallback handler used when no route matches."""
        self._default = handler
        return self

    def route(self, value: Any) -> Any:
        for route in self._routes:
            try:
                matched = route.predicate(value)
            except Exception:  # noqa: BLE001 - a broken predicate must not crash routing
                log.warning("router.predicate.error", extra={"route": route.name})
                matched = False
            if matched:
                log.debug("router.match", extra={"route": route.name})
                return route.handler(value)

        if self._default is not None:
            log.debug("router.default")
            return self._default(value)
        raise LookupError("No route matched and no default handler was set.")

    @property
    def route_names(self) -> list[str]:
        return [r.name for r in self._routes]
