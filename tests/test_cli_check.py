import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest


def test_m_ste_check() -> None:
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "-m", "ste", "check"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0
    o = (r.stdout or "") + (r.stderr or "")
    assert "python:" in o.lower() or "Python" in o
    assert "numpy" in o
    assert "pydantic" in o.lower()


def test_cmd_check_strict_returns_1_on_core_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    fake = CheckResult(ok=False, lines=["x"], core_missing=["numpy"])
    monkeypatch.setattr(
        "ste.diagnostics.check.run_checks",
        lambda required_modules=None, profile=None: fake,
    )
    ns = Namespace(
        strict=True,
        strict_optional=False,
        as_json=False,
        require="",
        profile=None,
        list_profiles=False,
        missing_only=False,
        fail_on=None,
    )
    assert _cmd_check(ns) == 1


def test_cmd_check_json_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    fake = CheckResult(
        ok=True,
        lines=["python: x"],
        effective_required=["fastapi", "uvicorn"],
        core_missing=[],
        optional_missing=["uvicorn"],
        required_missing=[],
    )
    monkeypatch.setattr(
        "ste.diagnostics.check.run_checks",
        lambda required_modules=None, profile=None: fake,
    )
    ns = Namespace(
        strict=False,
        strict_optional=False,
        as_json=True,
        require="",
        profile=None,
        list_profiles=False,
        missing_only=False,
        fail_on=None,
    )
    assert _cmd_check(ns) == 0
    out = capsys.readouterr().out
    assert '"ok": true' in out
    assert '"profile": null' in out
    assert '"effective_required": [' in out
    assert '"failed_categories": [' in out
    assert '"status_code": 0' in out
    assert '"phase_progress": {' in out
    assert '"optional_missing": [' in out


def test_cmd_check_require_forces_failure_in_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    fake = CheckResult(ok=False, lines=["x"], required_missing=["fastapi"])
    seen: list[str] = []

    def _fake_run(
        required_modules: list[str] | tuple[str, ...] | None = None,
        *,
        profile: str | None = None,
    ) -> CheckResult:
        seen[:] = list(required_modules or ())
        return fake

    monkeypatch.setattr("ste.diagnostics.check.run_checks", _fake_run)
    ns = Namespace(
        strict=True,
        strict_optional=False,
        as_json=False,
        require="fastapi",
        profile=None,
        list_profiles=False,
        missing_only=False,
        fail_on=None,
    )
    assert _cmd_check(ns) == 1
    assert seen == ["fastapi"]


def test_cmd_check_passes_profile_to_run_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    captured: dict[str, object] = {}

    def recv(
        required_modules: list[str] | tuple[str, ...] | None = None,
        *,
        profile: str | None = None,
    ) -> CheckResult:
        captured["required_modules"] = list(required_modules or ())
        captured["profile"] = profile
        return CheckResult(
            ok=True,
            profile=profile,
            effective_required=["fastapi", "uvicorn", "httpx", "pandas"],
            lines=[],
            core_missing=[],
            optional_missing=[],
            required_missing=[],
        )

    monkeypatch.setattr("ste.diagnostics.check.run_checks", recv)
    ns = Namespace(
        strict=False,
        strict_optional=False,
        as_json=False,
        require="pandas",
        profile="api",
        list_profiles=False,
        missing_only=False,
        fail_on=None,
    )
    assert _cmd_check(ns) == 0
    assert captured["profile"] == "api"
    assert captured["required_modules"] == ["pandas"]


def test_cmd_check_list_profiles_text(capsys: pytest.CaptureFixture[str]) -> None:
    from ste.__main__ import _cmd_check

    ns = Namespace(
        strict=False,
        strict_optional=False,
        as_json=False,
        require="",
        profile=None,
        list_profiles=True,
        missing_only=False,
        fail_on=None,
    )
    assert _cmd_check(ns) == 0
    out = capsys.readouterr().out
    assert "all:" in out
    assert "api:" in out
    assert "fetch:" in out


def test_cmd_check_list_profiles_json(capsys: pytest.CaptureFixture[str]) -> None:
    from ste.__main__ import _cmd_check

    ns = Namespace(
        strict=False,
        strict_optional=False,
        as_json=True,
        require="",
        profile=None,
        list_profiles=True,
        missing_only=False,
        fail_on=None,
    )
    assert _cmd_check(ns) == 0
    out = capsys.readouterr().out
    assert '"all"' in out
    assert '"api"' in out
    assert '"fetch"' in out


def test_m_ste_check_profile_api_strict() -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("uvicorn")
    pytest.importorskip("httpx")
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "ste",
            "check",
            "--strict",
            "--profile",
            "api",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0


def test_cmd_check_strict_optional_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    fake = CheckResult(ok=True, lines=["x"], optional_missing=["yfinance"])
    monkeypatch.setattr(
        "ste.diagnostics.check.run_checks",
        lambda required_modules=None, profile=None: fake,
    )
    ns = Namespace(
        strict=False,
        strict_optional=True,
        as_json=False,
        require="",
        profile=None,
        list_profiles=False,
        missing_only=False,
        fail_on=None,
    )
    assert _cmd_check(ns) == 1


def test_cmd_check_missing_only_text(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    fake = CheckResult(
        ok=False,
        lines=["python: x", "numpy: y"],
        core_missing=["numpy"],
        optional_missing=["yfinance"],
        required_missing=[],
    )
    monkeypatch.setattr(
        "ste.diagnostics.check.run_checks",
        lambda required_modules=None, profile=None: fake,
    )
    ns = Namespace(
        strict=False,
        strict_optional=False,
        as_json=False,
        require="",
        profile=None,
        list_profiles=False,
        missing_only=True,
        fail_on=None,
    )
    assert _cmd_check(ns) == 0
    out = capsys.readouterr().out
    assert "core_missing: numpy" in out
    assert "optional_missing: yfinance" in out
    assert "required_missing: (none)" in out
    assert "python: x" not in out


def test_cmd_check_fail_on_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    fake = CheckResult(ok=True, lines=["x"], optional_missing=["uvicorn"])
    monkeypatch.setattr(
        "ste.diagnostics.check.run_checks",
        lambda required_modules=None, profile=None: fake,
    )
    ns = Namespace(
        strict=False,
        strict_optional=False,
        as_json=False,
        require="",
        profile=None,
        list_profiles=False,
        missing_only=False,
        fail_on="optional",
    )
    assert _cmd_check(ns) == 1


def test_cmd_check_fail_on_required(monkeypatch: pytest.MonkeyPatch) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    fake = CheckResult(ok=False, lines=["x"], required_missing=["fastapi"])
    monkeypatch.setattr(
        "ste.diagnostics.check.run_checks",
        lambda required_modules=None, profile=None: fake,
    )
    ns = Namespace(
        strict=False,
        strict_optional=False,
        as_json=False,
        require="",
        profile=None,
        list_profiles=False,
        missing_only=False,
        fail_on="required",
    )
    assert _cmd_check(ns) == 1


def test_cmd_check_fail_on_any_with_core(monkeypatch: pytest.MonkeyPatch) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    fake = CheckResult(ok=False, lines=["x"], core_missing=["numpy"])
    monkeypatch.setattr(
        "ste.diagnostics.check.run_checks",
        lambda required_modules=None, profile=None: fake,
    )
    ns = Namespace(
        strict=False,
        strict_optional=False,
        as_json=False,
        require="",
        profile=None,
        list_profiles=False,
        missing_only=False,
        fail_on="any",
    )
    assert _cmd_check(ns) == 1


def test_cmd_check_json_reports_status_and_failed_categories(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    fake = CheckResult(
        ok=False,
        lines=["x"],
        core_missing=["numpy"],
        optional_missing=["uvicorn"],
        required_missing=[],
    )
    monkeypatch.setattr(
        "ste.diagnostics.check.run_checks",
        lambda required_modules=None, profile=None: fake,
    )
    ns = Namespace(
        strict=False,
        strict_optional=False,
        as_json=True,
        require="",
        profile=None,
        list_profiles=False,
        missing_only=False,
        fail_on="any",
    )
    assert _cmd_check(ns) == 1
    out = capsys.readouterr().out
    assert '"failed_categories": [' in out
    assert '"core"' in out
    assert '"optional"' in out
    assert '"status_code": 1' in out


def test_cmd_phase_status_mark_done_calls_writer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from ste.__main__ import _cmd_phase_status

    monkeypatch.setattr(
        "ste.pipeline.phases.phase_progress_report",
        lambda: {"phases": [{"phase": 0}], "highest_ready_phase": -1, "next_phase": 0},
    )
    called: dict[str, object] = {}

    def _fake_set(phase: int, action_text: str, done: bool) -> bool:
        called["phase"] = phase
        called["action_text"] = action_text
        called["done"] = done
        return True

    monkeypatch.setattr("ste.pipeline.phases.set_phase_action_done", _fake_set)
    ns = Namespace(
        phase=0,
        action_plan=False,
        mark_done=True,
        mark_pending=False,
        action_text="abc",
        as_json=False,
    )
    assert _cmd_phase_status(ns) == 0
    assert called == {"phase": 0, "action_text": "abc", "done": True}
    assert "updated phase=0" in capsys.readouterr().out


def test_cmd_check_json_includes_phase_progress_with_hierarchy(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from ste.__main__ import _cmd_check
    from ste.diagnostics.check import CheckResult

    fake = CheckResult(ok=True, lines=["x"])
    monkeypatch.setattr(
        "ste.diagnostics.check.run_checks",
        lambda required_modules=None, profile=None: fake,
    )
    ns = Namespace(
        strict=False,
        strict_optional=False,
        as_json=True,
        require="",
        profile=None,
        list_profiles=False,
        missing_only=False,
        fail_on=None,
    )
    assert _cmd_check(ns) == 0
    out = capsys.readouterr().out
    assert '"phase_progress": {' in out
    assert '"highest_ready_phase"' in out
    assert '"next_phase"' in out
    assert '"phases"' in out
