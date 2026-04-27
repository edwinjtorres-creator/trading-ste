from __future__ import annotations

from typing import Protocol, runtime_checkable

from ste.contracts import Bar, OrderIntent, OrderReport


@runtime_checkable
class ExecutionBackend(Protocol):
    """
    *Live* o simulación: mapea *intent* a *OrderReport* de forma *idempotente* por
    *idempotency_key*.
    """

    def execute(
        self,
        intent: OrderIntent,
        last_bar: Bar | None,
    ) -> OrderReport: ...


@runtime_checkable
class DataFeed(Protocol):
    def next_bar(self) -> Bar | None: ...
