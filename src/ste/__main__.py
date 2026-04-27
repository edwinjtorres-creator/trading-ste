"""
CLI: `python -m ste` o el comando de consola `ste` (tras `pip install -e .`).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ste import __version__
from ste.diagnostics.check import (
    CHECK_ALL_PROFILE,
    CHECK_PROFILES,
    merge_required_from_profile,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _cmd_version(_: argparse.Namespace) -> int:
    print(__version__)
    return 0


def _cmd_merge_req(_: argparse.Namespace) -> int:
    p = _root() / "scripts" / "merge_requirements.py"
    r = subprocess.run([sys.executable, str(p)], cwd=_root(), check=False)
    return int(r.returncode != 0)


def _cmd_install_layers(ns: argparse.Namespace) -> int:
    p = _root() / "scripts" / "install_layers.py"
    args = [sys.executable, str(p)]
    if ns.dry_run:
        args.append("--dry-run")
    if ns.cont:
        args.append("--continue")
    if ns.include_optional:
        args.append("--include-optional")
    if ns.log:
        args.extend(["--log", ns.log])
    r = subprocess.run(args, cwd=_root(), check=False)
    return int(r.returncode != 0)


def _cmd_fetch(ns: argparse.Namespace) -> int:
    from ste.ingest.yfinance_bars import download_many_to_parquet, download_ohlc_to_parquet

    tickers = [t.strip().upper() for t in ns.ticker if t.strip()]
    if not tickers:
        print("Indica al menos un ticker.", file=sys.stderr)
        return 1
    out = Path(ns.out)
    v = not ns.no_validate
    if len(tickers) == 1 and out.suffix.lower() == ".parquet":
        out.parent.mkdir(parents=True, exist_ok=True)
        n = download_ohlc_to_parquet(
            tickers[0],
            out,
            period=ns.period,
            interval=ns.interval,
            validate_rows=v,
        )
        print(f"OK: {n} bares -> {out}")
        return 0
    if len(tickers) > 1 and out.suffix.lower() == ".parquet":
        print("Con varios tickers, -o debe ser un directorio, no un .parquet", file=sys.stderr)
        return 1
    out_dir = out if (out.suffix == "" and not out.is_file()) or out.is_dir() else out.parent
    if not out_dir.is_dir():
        out_dir.mkdir(parents=True, exist_ok=True)
    for t, p, n in download_many_to_parquet(
        tickers, out_dir, period=ns.period, interval=ns.interval, validate_rows=v
    ):
        print(f"OK: {t} {n} bares -> {p}")
    return 0


def _cmd_report_wf(ns: argparse.Namespace) -> int:
    import json

    from ste.jobs.walkforward_from_parquet import walkforward_report_from_parquet

    rows = walkforward_report_from_parquet(ns.path, ns.train, ns.test, ns.step)
    if not rows:
        if ns.as_json:
            print("[]")
            return 0
        print(
            "Sin resultados: pocos bares, Parquet vacío o *train*+*test* mayores que retornos.",
            file=sys.stderr,
        )
        return 1
    if ns.as_json:
        print(
            json.dumps(
                rows,
                indent=2,
                default=str,
            )
        )
    else:
        for r in rows:
            w = r.get("window", {})
            print(
                f"train{w.get('train')} test{w.get('test')}: "
                f"sharpe={r.get('sharpe'):.4f} max_dd={r.get('max_dd'):.4f}"
            )
    return 0


def _cmd_replay(ns: argparse.Namespace) -> int:
    import json

    from pydantic import ValidationError

    from ste.eval.paper_replay import (
        evaluate_replay_gates,
        replay_parquet_mtm,
        replay_to_jsonable,
        write_replay_csv,
    )
    from ste.eval.replay_io import (
        CLI_REPLAY_IO_EXIT,
        PARQUET_REPLAY_READ_ERRORS,
        parquet_invalid_message,
        parquet_not_found_message,
    )
    from ste.orchestration.schemas import ReplayRequest
    from ste.risk import PolicyConfig

    GATE_FAIL_EXIT = 4

    try:
        cfg = ReplayRequest.model_validate(
            {
                "file_path": ns.path,
                "position_size": ns.size,
                "fast": ns.fast,
                "slow": ns.slow,
                "cost_bps": float(getattr(ns, "cost_bps", 0.0)),
                "slippage_bps": float(getattr(ns, "slippage_bps", 0.0)),
                "ignore_regime": ns.ignore_regime,
            }
        )
    except ValidationError as e:
        print("Parámetros de replay inválidos:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1

    pc = PolicyConfig(require_regime_ok=not cfg.ignore_regime)
    try:
        out = replay_parquet_mtm(
            cfg.file_path,
            position_size=cfg.position_size,
            fast=cfg.fast,
            slow=cfg.slow,
            cost_bps=cfg.cost_bps,
            slippage_bps=cfg.slippage_bps,
            policy=pc,
        )
    except FileNotFoundError as e:
        print(parquet_not_found_message(e, ns.path), file=sys.stderr)
        return CLI_REPLAY_IO_EXIT
    except PARQUET_REPLAY_READ_ERRORS as e:
        print(parquet_invalid_message(e), file=sys.stderr)
        return CLI_REPLAY_IO_EXIT
    if ns.csv:
        write_replay_csv(out, ns.csv)
    gate_failures = evaluate_replay_gates(
        out,
        min_sharpe=getattr(ns, "min_sharpe", None),
        max_drawdown=getattr(ns, "max_drawdown", None),
        min_equity=getattr(ns, "min_equity", None),
    )
    out["gate_passed"] = len(gate_failures) == 0
    out["gate_failures"] = gate_failures
    if ns.as_json:
        print(json.dumps(replay_to_jsonable(out), indent=2, default=str))
    if not ns.as_json:
        line = (
            f"path={out['path']} equity_final={out['equity_final']:.6f} "
            f"sharpe={out['sharpe']:.4f} max_dd={out['max_drawdown']:.4f} "
            f"cost={out['total_cost_frac']:.6f} halted={out['halted']}"
        )
        if ns.csv:
            line += f" csv={ns.csv}"
        print(line)
    if gate_failures:
        print("Replay gate failed:", file=sys.stderr)
        for f in gate_failures:
            print(f"- {f}", file=sys.stderr)
        return GATE_FAIL_EXIT
    return 0


def _cmd_eval_gate(ns: argparse.Namespace) -> int:
    import json

    from pydantic import ValidationError

    from ste.eval.paper_replay import evaluate_replay_gates, replay_parquet_mtm
    from ste.eval.replay_io import (
        CLI_REPLAY_IO_EXIT,
        PARQUET_REPLAY_READ_ERRORS,
        parquet_invalid_message,
        parquet_not_found_message,
    )
    from ste.orchestration.schemas import ReplayRequest
    from ste.risk import PolicyConfig

    GATE_FAIL_EXIT = 4
    try:
        cfg = ReplayRequest.model_validate(
            {
                "file_path": ns.path,
                "position_size": ns.size,
                "fast": ns.fast,
                "slow": ns.slow,
                "cost_bps": ns.cost_bps,
                "slippage_bps": ns.slippage_bps,
                "ignore_regime": ns.ignore_regime,
                "min_sharpe": ns.min_sharpe,
                "max_drawdown": ns.max_drawdown,
                "min_equity": ns.min_equity,
            }
        )
    except ValidationError as e:
        print("Parámetros de eval-gate inválidos:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1

    pc = PolicyConfig(require_regime_ok=not cfg.ignore_regime)
    try:
        out = replay_parquet_mtm(
            cfg.file_path,
            position_size=cfg.position_size,
            fast=cfg.fast,
            slow=cfg.slow,
            cost_bps=cfg.cost_bps,
            slippage_bps=cfg.slippage_bps,
            policy=pc,
        )
    except FileNotFoundError as e:
        print(parquet_not_found_message(e, ns.path), file=sys.stderr)
        return CLI_REPLAY_IO_EXIT
    except PARQUET_REPLAY_READ_ERRORS as e:
        print(parquet_invalid_message(e), file=sys.stderr)
        return CLI_REPLAY_IO_EXIT

    failures = evaluate_replay_gates(
        out,
        min_sharpe=cfg.min_sharpe,
        max_drawdown=cfg.max_drawdown,
        min_equity=cfg.min_equity,
    )
    passed = len(failures) == 0
    payload = {
        "passed": passed,
        "failures": failures,
        "metrics": {
            "equity_final": float(out.get("equity_final", 1.0)),
            "sharpe": float(out.get("sharpe", 0.0)),
            "max_drawdown": float(out.get("max_drawdown", 0.0)),
            "total_cost_frac": float(out.get("total_cost_frac", 0.0)),
            "halted": bool(out.get("halted", False)),
        },
        "path": str(out.get("path", cfg.file_path)),
    }
    if ns.as_json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        state = "PASS" if passed else "FAIL"
        print(
            f"{state} path={payload['path']} "
            f"equity_final={payload['metrics']['equity_final']:.6f} "
            f"sharpe={payload['metrics']['sharpe']:.4f} "
            f"max_dd={payload['metrics']['max_drawdown']:.4f}"
        )
        if failures:
            for f in failures:
                print(f"- {f}")
    return 0 if passed else GATE_FAIL_EXIT


def _cmd_check(ns: argparse.Namespace) -> int:
    import json

    from ste.diagnostics.check import run_checks
    from ste.pipeline.phases import phase_progress_report

    if ns.list_profiles:
        profile_map = {k: list(v) for k, v in CHECK_PROFILES.items()}
        profile_map[CHECK_ALL_PROFILE] = merge_required_from_profile(CHECK_ALL_PROFILE, ())
        if ns.as_json:
            print(json.dumps(profile_map, indent=2, default=str))
        else:
            for k in sorted(profile_map):
                print(f"{k}: {', '.join(profile_map[k])}")
        return 0

    req = [m.strip() for m in (ns.require or "").split(",") if m.strip()]
    r = run_checks(required_modules=req, profile=ns.profile)
    failed: list[str] = []
    if r.core_missing:
        failed.append("core")
    if r.required_missing:
        failed.append("required")
    if r.optional_missing:
        failed.append("optional")
    r.failed_categories = failed
    exit_code = 0
    if ns.fail_on == "any" and (r.core_missing or r.required_missing or r.optional_missing):
        exit_code = 1
    elif ns.fail_on == "core" and r.core_missing:
        exit_code = 1
    elif ns.fail_on == "required" and r.required_missing:
        exit_code = 1
    elif ns.fail_on == "optional" and r.optional_missing:
        exit_code = 1
    elif ns.strict and not r.ok:
        exit_code = 1
    elif ns.strict_optional and r.optional_missing:
        exit_code = 1
    r.status_code = exit_code
    if ns.as_json:
        payload = r.to_jsonable()
        payload["phase_progress"] = phase_progress_report()
        print(json.dumps(payload, indent=2, default=str))
    else:
        if ns.missing_only:
            def _join_or_none(xs: list[str]) -> str:
                return ", ".join(xs) if xs else "(none)"

            print(f"core_missing: {_join_or_none(r.core_missing)}")
            print(f"optional_missing: {_join_or_none(r.optional_missing)}")
            print(f"required_missing: {_join_or_none(r.required_missing)}")
        else:
            print("\n".join(r.lines))
            if r.core_missing:
                print(f"core_missing: {', '.join(r.core_missing)}", file=sys.stderr)
            if r.optional_missing:
                print(f"optional_missing: {', '.join(r.optional_missing)}", file=sys.stderr)
            if r.required_missing:
                print(f"required_missing: {', '.join(r.required_missing)}", file=sys.stderr)
    return exit_code


def _cmd_serve(ns: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Instalá uvicorn: pip install uvicorn[standard]", file=sys.stderr)
        return 1
    from ste.orchestration.app import build_app

    app = build_app()
    uvicorn.run(app, host=ns.host, port=ns.port, log_level="info")
    return 0


def _cmd_phase_status(ns: argparse.Namespace) -> int:
    import json

    from ste.pipeline.phases import phase_progress_report, set_phase_action_done

    rep = phase_progress_report()
    phases = rep["phases"]
    phase_map = {int(p["phase"]): p for p in phases}
    selected = None
    if ns.phase is not None:
        selected = phase_map.get(ns.phase)
        if selected is None:
            print(f"Fase inválida: {ns.phase} (esperado 0..4)", file=sys.stderr)
            return 2
    if ns.mark_done and ns.mark_pending:
        print("Usa solo uno: --mark-done o --mark-pending.", file=sys.stderr)
        return 2
    if ns.mark_done or ns.mark_pending:
        if ns.phase is None:
            print("Para --mark-done/--mark-pending debes indicar --phase N.", file=sys.stderr)
            return 2
        action = (ns.action_text or "").strip()
        if not action:
            print("Para marcar acción debes indicar --action-text.", file=sys.stderr)
            return 2
        done = bool(ns.mark_done)
        ok = set_phase_action_done(ns.phase, action, done=done)
        if not ok:
            print(f"No se encontró acción en fase {ns.phase}: {action}", file=sys.stderr)
            return 2
        state = "done" if done else "pending"
        print(f"updated phase={ns.phase} action={action!r} -> {state}")
        return 0
    if ns.action_plan:
        src = selected if selected is not None else next((p for p in phases if not p["ready"]), None)
        if src is None:
            print("No hay acciones pendientes: todas las fases están listas.")
            return 0
        print(f"action_plan phase={src['phase']} {src['name']}")
        prog = src.get("action_progress") or {}
        if prog:
            print(
                f"progress pending={prog.get('pending', 0)} "
                f"completed={prog.get('completed', 0)} total={prog.get('total', 0)}"
            )
        for a in src.get("next_actions", []):
            print(f"- {a}")
        if src.get("missing"):
            print(f"blocked_by={', '.join(src['missing'])}")
        return 0
    if ns.as_json:
        out = selected if selected is not None else rep
        print(json.dumps(out, indent=2, default=str))
        return 0
    if selected is not None:
        mark = "OK" if selected["ready"] else "PENDING"
        print(f"[{mark}] {selected['phase']} {selected['name']}: {selected['description']}")
        if selected.get("missing"):
            print(f"missing={', '.join(selected['missing'])}")
        if selected.get("next_actions"):
            print("next_actions:")
            for a in selected["next_actions"]:
                print(f"- {a}")
        return 0
    print(f"highest_ready_phase={rep['highest_ready_phase']} next_phase={rep['next_phase']}")
    if rep.get("blocked_by"):
        print(f"blocked_by={', '.join(rep['blocked_by'])}")
    if rep.get("next_actions"):
        print("next_actions:")
        for a in rep["next_actions"]:
            print(f"- {a}")
    for ph in rep["phases"]:
        mark = "OK" if ph["ready"] else "PENDING"
        print(f"[{mark}] {ph['phase']} {ph['name']}: {ph['description']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="ste", description="Sistema de Trading Evolutivo (STE).")
    ap.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("version", help="Imprimir versión del paquete")
    s.set_defaults(_fn=_cmd_version)

    s = sub.add_parser("merge-req", help="Regenerar requirements/all.txt desde requirements/layers/")
    s.set_defaults(_fn=_cmd_merge_req)

    s = sub.add_parser("install-layers", help="Pasar pip install -r en cada capa (ver scripts/install_layers.py)")
    s.add_argument("--dry-run", action="store_true", help="Solo listar comandos pip")
    s.add_argument(
        "--continue",
        action="store_true",
        dest="cont",
        help="Seguir si una capa falla",
    )
    s.add_argument(
        "--include-optional",
        action="store_true",
        help="También requirements/optional/*.txt",
    )
    s.add_argument("--log", type=str, default=None, help="Archivo de registro")
    s.set_defaults(_fn=_cmd_install_layers)

    s = sub.add_parser("fetch", help="Yahoo Finance -> Parquet (requiere yfinance)")
    s.add_argument("ticker", nargs="+", help="Uno o más tickers (AAPL MSFT …)")
    s.add_argument(
        "-o",
        "--out",
        type=str,
        default="data",
        help="Archivo .parquet (un solo ticker) o **directorio** (varios tickers → {SYM}.parquet). Por defecto *data*.",
    )
    s.add_argument("--period", type=str, default="1y")
    s.add_argument("--interval", type=str, default="1d")
    s.add_argument(
        "--no-validate",
        action="store_true",
        help="No filtrar filas con OHLC/volumen inválido",
    )
    s.set_defaults(_fn=_cmd_fetch)

    s = sub.add_parser("report-wf", help="Parquet de bares → *walk-forward* (métricas *stub*)")
    s.add_argument("path", type=str, help="Ruta a .parquet (schema Bar)")
    s.add_argument("--train", type=int, default=60, help="Filas *train* sobre retornos (no bares)")
    s.add_argument("--test", type=int, default=20, help="Filas *test*")
    s.add_argument("--step", type=int, default=20, help="Desplazamiento *rolling*")
    s.add_argument("--json", action="store_true", dest="as_json", help="Salida JSON")
    s.set_defaults(_fn=_cmd_report_wf)

    s = sub.add_parser("replay", help="Parquet de bares → *replay* *paper* MTM + riesgo")
    s.add_argument("path", type=str, help="Ruta a .parquet (schema Bar)")
    s.add_argument("--size", type=float, default=0.25, help="Tamaño fraccionado (<=1)")
    s.add_argument("--fast", type=int, default=5)
    s.add_argument("--slow", type=int, default=15)
    s.add_argument("--cost-bps", type=float, default=0.0, help="Coste por turnover (bps)")
    s.add_argument(
        "--slippage-bps", type=float, default=0.0, help="Slippage por turnover (bps)"
    )
    s.add_argument(
        "--ignore-regime",
        action="store_true",
        help="Pasar PolicyConfig(require_regime_ok=False)",
    )
    s.add_argument("--json", action="store_true", dest="as_json", help="Salida JSON")
    s.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Escribir CSV (open_time_utc, pnl_fraccion, equity_after; puede combinarse con --json)",
    )
    s.add_argument("--min-sharpe", type=float, default=None, help="Gate: sharpe mínimo")
    s.add_argument(
        "--max-drawdown", type=float, default=None, help="Gate: drawdown máximo permitido"
    )
    s.add_argument("--min-equity", type=float, default=None, help="Gate: equity final mínima")
    s.set_defaults(_fn=_cmd_replay)

    s = sub.add_parser("eval-gate", help="Replay + gates numéricos en salida CI-friendly")
    s.add_argument("path", type=str, help="Ruta a .parquet (schema Bar)")
    s.add_argument("--size", type=float, default=0.25, help="Tamaño fraccionado (<=1)")
    s.add_argument("--fast", type=int, default=5)
    s.add_argument("--slow", type=int, default=15)
    s.add_argument(
        "--ignore-regime",
        action="store_true",
        help="Pasar PolicyConfig(require_regime_ok=False)",
    )
    s.add_argument("--cost-bps", type=float, default=0.0, help="Coste por turnover (bps)")
    s.add_argument(
        "--slippage-bps", type=float, default=0.0, help="Slippage por turnover (bps)"
    )
    s.add_argument("--min-sharpe", type=float, default=None, help="Gate: sharpe mínimo")
    s.add_argument(
        "--max-drawdown", type=float, default=None, help="Gate: drawdown máximo permitido"
    )
    s.add_argument("--min-equity", type=float, default=None, help="Gate: equity final mínima")
    s.add_argument("--json", action="store_true", dest="as_json", help="Salida JSON")
    s.set_defaults(_fn=_cmd_eval_gate)

    s = sub.add_parser("check", help="Comprobar entorno; opcionalmente fallar en CI")
    s.add_argument("--strict", action="store_true", help="Salir con código 1 si falta algo core")
    s.add_argument(
        "--strict-optional",
        action="store_true",
        help="Salir con código 1 si falta algo en optional_missing",
    )
    s.add_argument("--json", action="store_true", dest="as_json", help="Salida JSON estructurada")
    s.add_argument(
        "--require",
        type=str,
        default="",
        help="Módulos extra obligatorios para este entorno (CSV), ej: fastapi,uvicorn",
    )
    s.add_argument(
        "--profile",
        type=str,
        default=None,
        choices=sorted((*CHECK_PROFILES, CHECK_ALL_PROFILE)),
        help="Perfil predefinido de módulos requeridos (se combina con --require)",
    )
    s.add_argument(
        "--list-profiles",
        action="store_true",
        help="Listar perfiles disponibles y módulos asociados",
    )
    s.add_argument(
        "--missing-only",
        action="store_true",
        help="En salida texto, mostrar solo listas *_missing (útil en CI)",
    )
    s.add_argument(
        "--fail-on",
        type=str,
        default=None,
        choices=("core", "required", "optional", "any"),
        help="Fallar (exit 1) si faltan módulos en esa categoría",
    )
    s.set_defaults(_fn=_cmd_check)

    s = sub.add_parser("phase-status", help="Ver progreso operativo de fases 0–4")
    s.add_argument("--phase", type=int, default=None, help="Mostrar solo una fase (0..4)")
    s.add_argument(
        "--action-plan",
        action="store_true",
        help="Mostrar checklist accionable (siguiente fase pendiente por defecto)",
    )
    s.add_argument("--mark-done", action="store_true", help="Marcar acción como completada")
    s.add_argument("--mark-pending", action="store_true", help="Marcar acción como pendiente")
    s.add_argument(
        "--action-text",
        type=str,
        default="",
        help="Texto exacto de acción en checklist para marcar estado",
    )
    s.add_argument("--json", action="store_true", dest="as_json", help="Salida JSON")
    s.set_defaults(_fn=_cmd_phase_status)

    s = sub.add_parser(
        "serve",
        help="Levantar API mínima con *uvicorn* (por defecto 127.0.0.1:8765)",
    )
    s.add_argument("--host", type=str, default="127.0.0.1", help="Dirección de enlace")
    s.add_argument("--port", type=int, default=8765, help="Puerto TCP")
    s.set_defaults(_fn=_cmd_serve)

    ns = ap.parse_args()
    return ns._fn(ns)  # type: ignore[union-attr, no-any-return]


if __name__ == "__main__":
    raise SystemExit(main())
