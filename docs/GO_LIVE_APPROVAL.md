# STE Go-Live Approval (1-click)

Fecha: `____-__-__`
Responsable: `________________`

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
- [ ] `max_daily_loss` aprobado: `________`
- [ ] `max_drawdown` aprobado: `________`
- [ ] `min_equity` aprobado: `________`
- [ ] Kill switch habilitado y probado (`live-min-smoke` PASS)

## 4) Criterios de despliegue
- [ ] CI requerido en PASS (`CI Control Tower`)
- [ ] `quant-gate` PASS
- [ ] `walkforward-report` PASS
- [ ] `smoke-api` PASS
- [ ] `paper-scheduler` revisado (último artifact OK)
- [ ] `live-min-smoke` revisado (último artifact OK)

## 5) Operación inicial
- [ ] Fecha/hora de activación: `____-__-__ __:__ UTC`
- [ ] Ventana de observación inicial: `________`
- [ ] Responsable on-call principal: `________________`
- [ ] Responsable backup: `________________`

## 6) Política de rollback
- [ ] Condición de rollback documentada
- [ ] Comando/procedimiento validado
- [ ] Tiempo máximo de rollback aceptado: `________`

## 7) Aprobación final
- [ ] Autorizo go-live controlado con capital real bajo los límites definidos arriba.

Firma responsable: `________________`
Fecha/hora: `____-__-__ __:__`

---

## Notas rápidas
- Si cualquier check crítico falla, **no desplegar**.
- Mantener `develop`/`master` protegidas y registrar cualquier override.
- Toda excepción debe quedar documentada en PR/release notes.
