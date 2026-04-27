import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest


def test_m_ste_version() -> None:
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "-m", "ste", "version"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0
    out = (r.stdout or "").strip()
    assert len(out) > 0


def test_m_ste_phase_status_json() -> None:
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "-m", "ste", "phase-status", "--json"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0
    o = (r.stdout or "")
    assert "highest_ready_phase" in o
    assert '"phases"' in o
    assert '"next_actions"' in o


def test_m_ste_phase_status_phase_json() -> None:
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "-m", "ste", "phase-status", "--phase", "2", "--json"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0
    o = (r.stdout or "")
    assert '"phase": 2' in o
    assert '"name"' in o
    assert '"next_actions"' in o


def test_m_ste_phase_status_action_plan() -> None:
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "-m", "ste", "phase-status", "--action-plan"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r.returncode == 0
    o = (r.stdout or "")
    assert "action_plan phase=" in o or "No hay acciones pendientes" in o
    if "action_plan phase=" in o:
        assert "progress pending=" in o


def test_ste_replay_cli_missing_parquet_exit_2(tmp_path: Path) -> None:
    from ste.__main__ import _cmd_replay

    ns = Namespace(
        path=str(tmp_path / "definitely_missing_ste.parquet"),
        size=0.25,
        fast=5,
        slow=15,
        ignore_regime=True,
        as_json=False,
        csv=None,
        min_sharpe=None,
        max_drawdown=None,
        min_equity=None,
    )
    assert _cmd_replay(ns) == 2


def test_ste_serve_passes_host_port_to_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("uvicorn")
    captured: dict[str, object] = {}

    def fake_run(app: object, **kwargs: object) -> None:
        captured["app"] = app
        captured.update(kwargs)

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", fake_run)
    from ste.__main__ import _cmd_serve

    ns = Namespace(host="0.0.0.0", port=9999)
    assert _cmd_serve(ns) == 0
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9999
    assert captured.get("log_level") == "info"


def test_ste_replay_cli_invalid_params_exit_1(tmp_path: Path) -> None:
    from ste.__main__ import _cmd_replay

    p = tmp_path / "nope.parquet"
    ns = Namespace(
        path=str(p),
        size=0.25,
        fast=10,
        slow=5,
        ignore_regime=True,
        as_json=False,
        csv=None,
        min_sharpe=None,
        max_drawdown=None,
        min_equity=None,
    )
    assert _cmd_replay(ns) == 1


def test_ste_replay_cli_corrupt_parquet_exit_2(tmp_path: Path) -> None:
    from ste.__main__ import _cmd_replay

    p = tmp_path / "bad.parquet"
    p.write_bytes(b"not parquet")
    ns = Namespace(
        path=str(p),
        size=0.25,
        fast=5,
        slow=15,
        ignore_regime=True,
        as_json=False,
        csv=None,
        min_sharpe=None,
        max_drawdown=None,
        min_equity=None,
    )
    assert _cmd_replay(ns) == 2


def test_ste_replay_cli_gate_fail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from ste.__main__ import _cmd_replay

    def _fake_replay(*args, **kwargs):
        return {
            "path": "x",
            "equity_final": 0.95,
            "sharpe": 0.1,
            "max_drawdown": 0.3,
            "total_cost_frac": 0.0,
            "halted": False,
            "returns": [],
            "bar_times": [],
            "equity_curve": [1.0],
        }

    monkeypatch.setattr("ste.eval.paper_replay.replay_parquet_mtm", _fake_replay)
    ns = Namespace(
        path=str(tmp_path / "g.parquet"),
        size=0.25,
        fast=5,
        slow=15,
        ignore_regime=True,
        as_json=False,
        csv=None,
        min_sharpe=0.2,
        max_drawdown=0.2,
        min_equity=1.0,
    )
    assert _cmd_replay(ns) == 4


def test_ste_replay_cli_gate_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from ste.__main__ import _cmd_replay

    def _fake_replay(*args, **kwargs):
        return {
            "path": "x",
            "equity_final": 1.02,
            "sharpe": 0.8,
            "max_drawdown": 0.1,
            "total_cost_frac": 0.0,
            "halted": False,
            "returns": [],
            "bar_times": [],
            "equity_curve": [1.0],
        }

    monkeypatch.setattr("ste.eval.paper_replay.replay_parquet_mtm", _fake_replay)
    ns = Namespace(
        path=str(tmp_path / "g.parquet"),
        size=0.25,
        fast=5,
        slow=15,
        ignore_regime=True,
        as_json=False,
        csv=None,
        min_sharpe=0.2,
        max_drawdown=0.2,
        min_equity=1.0,
    )
    assert _cmd_replay(ns) == 0


def test_ste_replay_cli_json_includes_gate_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from ste.__main__ import _cmd_replay

    def _fake_replay(*args, **kwargs):
        return {
            "path": "x",
            "equity_final": 1.02,
            "sharpe": 0.8,
            "max_drawdown": 0.1,
            "total_cost_frac": 0.0,
            "halted": False,
            "returns": [],
            "bar_times": [],
            "equity_curve": [1.0],
        }

    monkeypatch.setattr("ste.eval.paper_replay.replay_parquet_mtm", _fake_replay)
    ns = Namespace(
        path=str(tmp_path / "g.parquet"),
        size=0.25,
        fast=5,
        slow=15,
        ignore_regime=True,
        as_json=True,
        csv=None,
        min_sharpe=0.2,
        max_drawdown=0.2,
        min_equity=1.0,
    )
    assert _cmd_replay(ns) == 0
    out = capsys.readouterr().out
    assert '"gate_passed": true' in out
    assert '"gate_failures": []' in out


def test_eval_gate_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from ste.__main__ import _cmd_eval_gate

    def _fake_replay(*args, **kwargs):
        return {
            "path": "x",
            "equity_final": 1.02,
            "sharpe": 0.8,
            "max_drawdown": 0.1,
            "total_cost_frac": 0.0,
            "halted": False,
        }

    monkeypatch.setattr("ste.eval.paper_replay.replay_parquet_mtm", _fake_replay)
    ns = Namespace(
        path=str(tmp_path / "g.parquet"),
        size=0.25,
        fast=5,
        slow=15,
        ignore_regime=True,
        cost_bps=0.0,
        slippage_bps=0.0,
        min_sharpe=0.2,
        max_drawdown=0.2,
        min_equity=1.0,
        as_json=False,
    )
    assert _cmd_eval_gate(ns) == 0


def test_eval_gate_fail_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from ste.__main__ import _cmd_eval_gate

    def _fake_replay(*args, **kwargs):
        return {
            "path": "x",
            "equity_final": 0.95,
            "sharpe": 0.1,
            "max_drawdown": 0.3,
            "total_cost_frac": 0.0,
            "halted": False,
        }

    monkeypatch.setattr("ste.eval.paper_replay.replay_parquet_mtm", _fake_replay)
    ns = Namespace(
        path=str(tmp_path / "g.parquet"),
        size=0.25,
        fast=5,
        slow=15,
        ignore_regime=True,
        cost_bps=0.0,
        slippage_bps=0.0,
        min_sharpe=0.2,
        max_drawdown=0.2,
        min_equity=1.0,
        as_json=True,
    )
    assert _cmd_eval_gate(ns) == 4
    out = capsys.readouterr().out
    assert '"passed": false' in out
    assert '"failures": [' in out
