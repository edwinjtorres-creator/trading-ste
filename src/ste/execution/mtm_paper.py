from __future__ import annotations

from dataclasses import dataclass, field

from ste.contracts import Bar, OrderIntent, OrderReport, OrderSide


@dataclass
class SequentialMarkToMarket:
    """
    *Paper* con posición fraccionaria en [-1, 1]: en cada cierre, el P&L del
    retorno (close vs *last_close*) aplica a la posición *previa*; luego se
    actualiza posición con la intención de la vela. Auditable, sin *slip*.
    """

    _last_close: float | None = field(default=None, init=False, repr=False)
    _pos: float = field(default=0.0, init=False, repr=False)  # -1..+1 aproximado

    def reset(self) -> None:
        self._last_close = None
        self._pos = 0.0

    def position(self) -> float:
        return self._pos

    def execute(self, intent: OrderIntent, bar: Bar) -> OrderReport:
        c = float(bar.close)
        pnl = 0.0
        if self._last_close is not None and self._last_close > 0 and c > 0 and abs(self._pos) > 1e-15:
            r = c / self._last_close - 1.0
            pnl = self._pos * r
        self._reposition(intent)
        self._last_close = c
        return OrderReport(
            intent_idempotency_key=intent.idempotency_key,
            status="filled" if c > 0 else "rejected",
            filled_size=float(intent.size) if intent.size > 0 else 0.0,
            price=c,
            pnl_fraccion=float(pnl),
            as_of=bar.open_time_utc,
            details={"mode": "mtm_paper", "pos_after": self._pos},
        )

    def _reposition(self, intent: OrderIntent) -> None:
        if intent.side is OrderSide.FLAT or (intent.size or 0) <= 0:
            self._pos = 0.0
            return
        s = min(1.0, float(intent.size))
        if intent.side is OrderSide.BUY:
            self._pos = s
        else:
            self._pos = -s
