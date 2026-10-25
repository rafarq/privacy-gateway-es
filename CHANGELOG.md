# Cambios

## 1.1.0 — 2026-10-25

- **Ya no se reparte ningún fichero derivado del plugin original.** El parche
  `overlay/upstream-es.patch` (que llevaba dentro líneas de código de terceros
  sin licencia) se sustituye por `scripts/extend_es.py`, de autoría propia, que
  aplica las mismas cuatro ediciones sobre los ficheros descargados. Se ha
  comprobado que el resultado es **byte a byte idéntico** al que producía el
  parche, y que el script es idempotente.
- Efecto secundario: **el instalador ya no necesita `patch` ni `git`.**
- `README.md` reescrito como documento público: qué es, cómo funciona, qué
  detecta, qué no cubre, uso, configuración, mantenimiento, licencia y contacto.
- Añadidos `LICENSE` (MIT, código propio) y `PARA-AGENTES.md` (instrucciones
  imperativas para un agente de IA).
- `AVISO-LICENCIA.md` reescrito para reflejar que no se redistribuye código de
  terceros.
- `AGENTS.md` no se incluye a propósito: en Hermes es un fichero protegido y el
  paquete debe instalarse sin aprobaciones especiales.

## 1.0.1 — 2026-10-25

- Anadido `PARA-AGENTES.md`: instrucciones imperativas para que un agente de IA
  instale el paquete sin interpretaciones (orden de pasos, salida esperada y las
  trampas conocidas). El `README.md` avisa de ello en su primera linea.
- `AGENTS.md` **no** se incluye a proposito: en Hermes es un fichero protegido y
  el paquete debe ser instalable sin aprobaciones especiales.

## 1.0.0 — 2026-10-25

Primera version empaquetada.

- Instalador idempotente con modo `--dry-run`, `--reapply`, `--patch-core` y
  `--unattended`.
- Overlay sobre el commit base `032bda95` del plugin original:
  - `recognizers_es.py` con reconocedores espanoles locales (NIF/NIE con digito
    de control, CIF, telefonos ES, matricula, referencia catastral, NUSS,
    pasaporte).
  - `nlp.yaml` en `es` y gancho de reconocedores en `privacy.py`.
  - Idioma por defecto del motor: `en` -> `es` (evita el fallo silencioso).
- Clave del almacen al `.env` global (el `.env` de perfil no llega al proceso).
- Modelo `es_core_news_lg` en el entorno gestionado del gateway, con deteccion
  automatica del entorno.
- Deteccion y aplicacion optativa del override de `numpy` en el core.
- Verificacion end-to-end (`verify.sh`) que ejercita el plugin real, sin cargar
  modulos del core (evita relanzados y sincronizaciones de venv no deseados).
- Recarga del gateway con resumen legible (y `PGW_VERBOSE=1` para el detalle).
- `MANIFEST.sha256` regenerado con `sha256sum` o `shasum`, portable Linux/macOS.
- Desinstalador con `--purge` opcional.

### Corregido durante las pruebas

- El instalador abortaba en modo normal: varias lineas del tipo `[ ... ] && algo`
  hacian que `set -e` cortase la ejecucion al ser la condicion falsa.
- `pgw_detect_envs` mezclaba rutas con y sin `/venv` y el `sort -u` rompia la
  preferencia por el entorno del gateway en marcha.
- La deteccion del override de `numpy` parsea el TOML de verdad (`tomllib`): un
  comentario con corchetes rompia la expresion regular anterior.

### Motivo del endurecimiento del idioma

La causa raiz del fallo en produccion fue que el plugin lee su configuracion
**solo** de `plugins.entries.<id>.settings.<clave>`. Con `language` un nivel por
encima, se ignoraba en silencio, el motor arrancaba en ingles y cada peticion
moria con `KeyError: 'en'`, tapado por el *block marker* del plugin. Ademas de
documentarlo, se cambio el valor por defecto del motor a `es` para que el fallo
no pueda repetirse en silencio.
