"""
Evaluación y *backtest*; *walk-forward* y métricas mínimas; *backtest_stub* a extender.

*Live* no entra sin métricas y riesgo validados.
"""

from ste.eval.backtest_stub import run_walkforward_metrics_stub
from ste.eval.metrics import max_drawdown, sharpe_ratio, sortino_ratio, volatility
from ste.eval.paper_replay import replay_parquet_mtm, replay_to_jsonable, write_replay_csv
from ste.eval.walkforward import WalkWindow, iter_rolling, split_indices, walk_window_to_dict

__all__ = [
    "WalkWindow",
    "iter_rolling",
    "split_indices",
    "walk_window_to_dict",
    "sharpe_ratio",
    "sortino_ratio",
    "max_drawdown",
    "volatility",
    "run_walkforward_metrics_stub",
    "replay_parquet_mtm",
    "write_replay_csv",
    "replay_to_jsonable",
]
