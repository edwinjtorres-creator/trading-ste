# Dependencias: capas y riesgos

## Versiones de Python

- **3.10–3.12:** recomendado para el *stack* completo (muchos binarios, incl. TensorFlow si lo necesitás).
- **3.13+ / 3.14:** *TensorFlow* aún puede no publicar *wheel*; *requirements/all* omite comentado TF; ver `requirements/optional/tensorflow.txt`.

## Cómo instalar

- **Mínimo (núcleo y tests con API):** `pip install -e ".[dev]"` (ya incluye FastAPI/httpx/uvicorn para *healthz*).
- **Todo en capas (recomendado, “vamos a hacerlo todo” sin un solo *pip* frágil):** desde la raíz del repo:

  ```text
  python scripts/install_layers.py
  ```

  - `--continue` — si una capa falla (p. ej. *TA-Lib* en Windows), seguir con la siguiente.
  - `--include-optional` — al final, instala `requirements/optional/*.txt` (TensorFlow, Ray, etc., según lo que tengas en esa carpeta y tu versión de Python).
  - `--log install-log.txt` — deja rastro de qué se intentó.
  - `--dry-run` — solo lista los comandos `pip` que se ejecutarían.

- **Un solo manifiesto (menos control):** `python scripts/merge_requirements.py` y luego
  `pip install -r requirements/all.txt` (mismo riesgo de *resolver* que arriba).

**No** existe garantía de que **todo** se instale a la vez: hay conflictos versionados (JAX vs. CUDA, `TA-Lib` en Windows, `pygmo` con compilación, *mxnet* de GluonTS, etc.).

## Qué no entra vía *pip* tal cual

- **VectorBT *PRO*:** comercial, aparte; el repo alinea *vectorbt* open.
- **Lean / QuantConnect:** ecosistema propio, no reemplazable con una sola dependencia.
- **FinGPT / repositorios diversos:** a veces *GitHub* + requisitos propios, no *PyPI* estable.
- **Dissect / *DMA* a medida:** no es el mismo conjunto “instalar y olvidar”.

## Estrategia sana

1. Instala por `requirements/layers/01-*.txt`, luego 02, … y para cuando falle, **aísla** el paquete.
2. Usa *conda* o *wheels* precompilados para `TA-Lib` / `pygmo` en Windows.
3. Separa *entornos* si hace falta: “*research ML*” vs. “*ejecución* ligera” (dos venvs).

## Actualizar el manifiesto

- Edita los archivos en `requirements/layers/`.
- Ejecuta `python scripts/merge_requirements.py` y revisa *diff* de `requirements/all.txt` antes de *commit*.
