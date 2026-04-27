from __future__ import annotations

from dataclasses import dataclass

from ste.contracts import OrderSide, RegimeAction, RegimeView
from ste.risk.guardrails import RiskState, can_trade


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    """Unifica *gate* de régimen (Hurst/otros) con riesgo y señal discreta."""

    require_regime_ok: bool = True


def decide(
    risk: RiskState,
    regime: RegimeView,
    momentum: int,
    cfg: PolicyConfig | None = None,
) -> tuple[OrderSide, str]:
    """
    Devuelve *lado* y *razón* (auditoría). No calcula tamaño: eso es otra capa.
    """
    c = cfg or PolicyConfig()
    if not can_trade(risk):
        return OrderSide.FLAT, "risk_halt"
    if c.require_regime_ok and regime.action is RegimeAction.AVOID:
        return OrderSide.FLAT, "regime_avoid"
    if momentum > 0:
        return OrderSide.BUY, "momentum_long"
    if momentum < 0:
        return OrderSide.SELL, "momentum_short"
    return OrderSide.FLAT, "neutral"
