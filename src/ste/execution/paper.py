from __future__ import annotations

from ste.contracts import Bar, OrderIntent, OrderReport, OrderSide, utcnow


class PaperExecutor:
    """
    Simulación mínima: *fill* al cierre de la vela; sin *slip*; P&L fraccionado
    aproximado a partir del *close* (demostración, no *ledger* de producción).
    """

    def execute(self, intent: OrderIntent, last_bar: Bar | None) -> OrderReport:
        t = last_bar if last_bar is not None else _dummy_bar()
        p = float(t.close) if t else 0.0
        if intent.side is OrderSide.FLAT or intent.size <= 0.0:
            pnl = 0.0
        else:
            sgn = 1.0 if intent.side is OrderSide.BUY else -1.0
            pnl = sgn * 0.0001 * min(intent.size, 1.0)
        return OrderReport(
            intent_idempotency_key=intent.idempotency_key,
            status="filled" if p else "rejected",
            filled_size=float(intent.size) if intent.size > 0 else 0.0,
            price=p if t else None,
            pnl_fraccion=pnl,
            as_of=utcnow(),
            details={"mode": "paper", "close": t.close if t else None},
        )


def _dummy_bar() -> Bar:
    from datetime import datetime, timezone
    d = datetime(2000, 1, 1, tzinfo=timezone.utc)
    return Bar("DUMMY", "1m", d, 0, 0, 0, 0, 0, {})
