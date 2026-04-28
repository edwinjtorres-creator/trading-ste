# STE Go-Live Approval (1-click)

Fecha: `2026-04-27`
Responsable: `Edwin Torres`

## 1) Broker / MT5
- [ ] Cuenta MT5 confirmada (demo final o real)
- [ ] Terminal MT5 en Windows validado
- [ ] Micro-lote inicial aprobado: `________`
- [ ] Símbolos permitidos: `________________`

## 2) Secrets y Acceso
- [ ] Secrets cargados en GitHub (repo/org)
- [ ] Acceso mínimo aplicado (principio de menor privilegio)
- [ ] Rotación de credenciales definida (frecuencia: `________`)

## 3) Riesgo (obligatorio)
- [x] `max_daily_loss` aprobado: `0.01`
- [x] `max_drawdown` aprobado: `1.00`
- [x] `min_equity` aprobado: `0.01`
- [ ] Kill switch habilitado y probado (`live-min-smoke` PASS)

## 4) Criterios de despliegue
- [ ] CI requerido en PASS (`CI Control Tower`)
- [ ] `quant-gate` PASS
- [ ] `walkforward-report` PASS
- [ ] `smoke-api` PASS
- [ ] `paper-scheduler` revisado (último artifact OK)
- [ ] `live-min-smoke` revisado (último artifact OK)

## 5) Operación inicial
- [x] Fecha/hora de activación: `2026-04-27 18:00 UTC`
- [x] Ventana de observación inicial: `24h`
- [x] Responsable on-call principal: `Edwin Torres`
- [ ] Responsable backup: `Pendiente de asignar`

## 6) Política de rollback
- [ ] Condición de rollback documentada
- [ ] Comando/procedimiento validado
- [x] Tiempo máximo de rollback aceptado: `15 min`

## 7) Aprobación final
- [ ] Autorizo go-live controlado con capital real bajo los límites definidos arriba.

Firma responsable: `Edwin Torres (pendiente firma formal)`
Fecha/hora: `2026-04-27 13:09 -05`

---

## Notas rápidas
- Si cualquier check crítico falla, **no desplegar**.
- Mantener `develop`/`master` protegidas y registrar cualquier override.
- Toda excepción debe quedar documentada en PR/release notes.
