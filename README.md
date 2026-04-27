# trading-ste

Sistema de Trading Evolutivo (STE) — núcleo mínimo con **señal**, **régimen (Hurst aproximado)**, **riesgo** (cortes diarios) y **verificación** (`pytest`). La visión de largo plazo y el **engranaje** entre capas está en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). La capa de *backtest/live* vive en `src/ste/eval/` (en expansión).

**Ubicación del repo:** `C:\Users\User\Projects\trading-ste`

## Estructura

| Ruta | Rol |
|------|-----|
| `src/ste/contracts.py` | Tipos compartidos (Bar, órdenes, régimen) |
| `src/ste/ingest/` | Parquet (roundtrip `Bar`), bares sintéticos para pruebas |
| `src/ste/signal/` | Señal baseline (cruce de medias EMA) |
| `src/ste/regime/` | Hurst aprox. + gating de régimen |
| `src/ste/risk/` | Riesgo, `PolicyConfig` / `decide` (régimen + señal + halt) |
| `src/ste/eval/` | Walk-forward, métricas, *replay* Parquet MTM |
| `src/ste/execution/mtm_paper.py` | *Paper* secuencial *mark-to-market* |
| `src/ste/__main__.py` | CLI `ste` / `python -m ste` |
| `src/ste/ingest/yfinance_bars.py` | Yahoo Finance → Parquet, validación OHLCV, *batch* |
| `src/ste/jobs/` | *Walk-forward* desde Parquet |
| `tests/` | Pruebas del núcleo |

## Desarrollo

1. `python -m venv .venv` y activar el venv
2. `pip install -e ".[dev]"`
3. `pytest`
4. **CLI:** `python -m ste --help` — `version`, `merge-req`, `install-layers`, `fetch`, `report-wf`, `replay` (Parquet → *simulación paper* MTM + riesgo; `--json`, `--ignore-regime`, `--csv`, `--cost-bps`, `--slippage-bps`, `--min-sharpe`, `--max-drawdown`, `--min-equity`; **código de salida `2`** si el Parquet no existe o no es legible / compatible STE, **`4`** si no pasa gates numéricos), `eval-gate` (replay + evaluación CI-friendly de gates, salida corta o `--json` con `passed/failures/metrics`, exit `4` si falla), `check` (Python/deps básicos; `--strict` para CI core/required, `--strict-optional` para fallar también por optional, `--fail-on core|required|optional|any`, `--json` estructurado, `--profile api|fetch|dev|all`, `--require mod1,mod2`, `--list-profiles`, y `--missing-only` para mostrar solo faltantes en texto; JSON incluye `effective_required`, `failed_categories`, `status_code` y `phase_progress` embebido), `phase-status` (progreso operativo de fases 0–4 con `--json`, `--phase N`, `--action-plan`, `blocked_by` y `next_actions`; usa `docs/PHASES_CHECKLIST.json` como checklist editable y admite acciones con `done: true/false`, `--mark-done` y `--mark-pending` vía CLI), `serve` (API `127.0.0.1:8765`). Tras `pip install -e .`, comando `ste`. En GitHub Actions hay `lint` + `test` en matrix de Python `3.10/3.11/3.12`, `env-check-profiles` (`api/dev/fetch/all`) con artefactos `ste-check-*.json`, `quant-gate` (dataset sintético reproducible + `ste eval-gate`, artefacto timestamped `ste-eval-gate-YYYYMMDDTHHMMSSZ` + resumen de métricas y thresholds en `GITHUB_STEP_SUMMARY`; parámetros configurables por `QG_SIZE`, `QG_FAST`, `QG_SLOW`, `QG_COST_BPS`, `QG_SLIPPAGE_BPS`, `QG_MIN_SHARPE`, `QG_MAX_DRAWDOWN`, `QG_MIN_EQUITY`), `walkforward-report` (`ste report-wf`, artefacto timestamped `ste-report-wf-YYYYMMDDTHHMMSSZ` + resumen de ventanas/métricas + gate PASS/FAIL en `GITHUB_STEP_SUMMARY`; umbrales configurables por `WF_MIN_SHARPE_MEAN` y `WF_MAX_DRAWDOWN_WORST`) y `smoke-api` (levanta `ste serve`, valida `/healthz`, `/phase` y `POST /v1/eval-gate`, sube artefacto `ste-smoke-api-YYYYMMDDTHHMMSSZ` con respuesta + logs). En ejecuciones manuales (`workflow_dispatch`) estos valores se pueden sobreescribir desde inputs sin editar YAML; además se ejecuta nightly (`schedule`, 03:00 UTC).
5. **Integración:** `iter_pipeline_rows` / `compose_full_pipeline` → `OrderIntent`; `replay_parquet_mtm` (equity, *halt*); `walkforward_report_from_parquet` en `ste.jobs`.
6. **API (*local*):** con `ste serve` (opciones `--host`, `--port`; por defecto `127.0.0.1:8765`), o `uvicorn ste.orchestration.app:build_app --factory --host 127.0.0.1 --port 8765` si preferís *uvicorn* directo. `GET /docs` o `GET /openapi.json`. *Replay* por HTTP (cuerpo = JSON con **`file_path`** a Parquet en disco del servidor, no enlace web):

   ```bash
   curl -sS -X POST "http://127.0.0.1:8765/v1/replay" -H "Content-Type: application/json" \
     -d "{\"file_path\": \"C:/ruta/bares.parquet\", \"position_size\": 0.25, \"ignore_regime\": false}"
   ```
   Misma lógica que `ste replay`; acepta también `cost_bps` y `slippage_bps` (impactan `equity_final` y `total_cost_frac`), y gates opcionales (`min_sharpe`, `max_drawdown`, `min_equity`) que devuelven `gate_passed`/`gate_failures` en la respuesta. En producción haría falta *auth* y *allowlist* de rutas.
   Endpoint corto de gates (ideal para orquestación externa / bots de CI):

   ```bash
   curl -sS -X POST "http://127.0.0.1:8765/v1/eval-gate" -H "Content-Type: application/json" \
     -d "{\"file_path\": \"C:/ruta/bares.parquet\", \"ignore_regime\": true, \"min_sharpe\": 0.5, \"max_drawdown\": 0.25}"
   ```
   Respuesta compacta: `passed`, `failures`, `metrics` (`equity_final`, `sharpe`, `max_drawdown`, `total_cost_frac`, `halted`) y `path`.
   **Códigos HTTP en `POST /v1/replay` y `POST /v1/eval-gate`:** `422` si el JSON no cumple el esquema (`position_size` en `(0,1]`, `slow` > `fast`, etc.); `404` si la ruta no existe; `400` si el archivo no es Parquet legible, está corrupto o no tiene el *schema* de bares STE (columnas / versión).
7. **Stack completo por capas:** `python scripts/install_layers.py` (y `--include-optional` al final
   para TF/Ray en *optional*). Detalle en [`docs/DEPENDENCIES.md`](docs/DEPENDENCIES.md). Alternativa:
   `python scripts/merge_requirements.py` y un solo `pip install -r requirements/all.txt` (más brusco).
8. `git init` (si aún no) y `git add . && git commit -m "STE: …"`.

## CI manual: presets rápidos

En `Actions -> CI -> Run workflow` podés ajustar `workflow_dispatch` inputs sin editar YAML.
Los jobs validan rangos antes de correr (fallan rápido si hay inputs inválidos).

- Preset conservador (más estricto):
  - `qg_min_sharpe=0.20`
  - `qg_max_drawdown=0.35`
  - `qg_min_equity=0.98`
  - `wf_min_sharpe_mean=0.15`
  - `wf_max_drawdown_worst=0.45`
- Preset agresivo (exploración):
  - `qg_min_sharpe=0.00`
  - `qg_max_drawdown=0.70`
  - `qg_min_equity=0.90`
  - `wf_min_sharpe_mean=0.00`
  - `wf_max_drawdown_worst=0.75`
- Ajustes finos opcionales:
  - `qg_size`, `qg_fast`, `qg_slow`, `qg_cost_bps`, `qg_slippage_bps`.

## Optimización local rápida (Windows)

- Usar pruebas paralelas: `./scripts/test_fast.ps1` (o `./scripts/test_fast.ps1 tests/test_cli_check.py`).
- Recomendado en Defender: excluir la carpeta del repo y la del venv para reducir I/O en `pytest`.
- Mantener `pip install -e ".[dev]"` una sola vez por sesión; evitar reinstalar dependencias sin cambios.

Nada de **capital real** en este repositorio hasta sombra/validación y *kill switch* acordados.
