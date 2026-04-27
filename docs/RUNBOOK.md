# STE Runbook Operativo

## Objetivo
Operar y monitorear STE en modo seguro (paper/LIVE_MIN smoke), con decisiones claras ante fallos de CI.

## Cadencia diaria recomendada
1. Revisar el workflow más reciente en GitHub Actions.
2. Abrir `GITHUB_STEP_SUMMARY` y validar el bloque `CI Control Tower`.
3. Confirmar estado de:
   - `quant-gate`
   - `walkforward-report`
   - `smoke-api`
   - `paper-scheduler` (schedule/manual)
   - `live-min-smoke` (schedule/manual)
4. Si todo está en `PASS`, continuar con cambios o promoción.

## Criterios de bloqueo
- Bloquear merge/promoción si falla cualquiera de:
  - `lint`
  - `test`
  - `env-check-profiles`
  - `quant-gate`
  - `walkforward-report`
  - `smoke-api`
- Tratar `paper-scheduler` y `live-min-smoke` como alarmas operativas en corridas programadas.

## Respuesta rápida por tipo de fallo
- `quant-gate` FAIL:
  - revisar `ste-eval-gate-*.json`
  - identificar métrica fuera de umbral (`sharpe`, `max_drawdown`, `equity`)
  - ajustar estrategia o umbrales con justificación explícita
- `walkforward-report` FAIL:
  - revisar `ste-report-wf-gate.json`
  - confirmar ventanas suficientes y benchmark de `sharpe_mean/max_dd_worst`
- `smoke-api` FAIL:
  - revisar `.ci/smoke_api.log` y `ste-smoke-api.json`
  - validar `healthz`, `phase`, `openapi`, `POST /v1/eval-gate`
- `paper-scheduler` FAIL:
  - revisar `ste-paper-scheduler-*.json`
  - analizar `gate_failures` y estado `halted`
- `live-min-smoke` FAIL:
  - revisar `ste-live-min-smoke-*.json`
  - verificar kill switch (`pre_trade`/`post_trade`, `trading_halt`)
  - validar disponibilidad de `MetaTrader5` en entorno Windows

## Comandos útiles locales
- Estado operativo unificado:
  - `python -m ste ops-status --json`
- Smoke LIVE_MIN:
  - `python -m ste live-min-smoke --json`
- Fases:
  - `python -m ste phase-status --json`

## Regla de seguridad
No usar capital real hasta que `live-min-smoke` y kill switch pasen de forma consistente y con evidencia en artefactos CI.

## Aprobación formal
Antes de go-live, completar el acta:
- `docs/GO_LIVE_APPROVAL.md`
