from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiskState:
    """
    Corte mínimo intradía: P&L acumulado en *fracción* (ej. -0.02 = -2% del capital
    de referencia del día) y equity multiplicativa.
    """

    max_daily_loss_fraction: float = 0.02
    daily_pnl_fraction: float = 0.0
    equity: float = 1.0
    trading_halt: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_daily_loss_fraction < 0:
            raise ValueError("max_daily_loss_fraction no puede ser negativa")
        if self.max_daily_loss_fraction > 1.0:
            raise ValueError("límite de pérdida fraccionaria inusualmente alto")


def record_daily_pnl(state: RiskState, trade_pnl_fraction: float) -> None:
    """
    Suma un retorno incremental al P&L del día; actualiza equity; corta si toca mínimos.
    `trade_pnl_fraction` en fracción (0.01 = +1% sobre el notional bajo riesgo).
    """
    state.daily_pnl_fraction += float(trade_pnl_fraction)
    if state.daily_pnl_fraction <= -state.max_daily_loss_fraction:
        state.trading_halt = True
    if state.equity > 0:
        state.equity = max(0.0, state.equity * (1.0 + float(trade_pnl_fraction)))
    if state.equity <= 0.0:
        state.trading_halt = True


def can_trade(state: RiskState) -> bool:
    return not state.trading_halt


def reset_state(state: RiskState) -> None:
    state.daily_pnl_fraction = 0.0
    state.trading_halt = False
    state.equity = 1.0
