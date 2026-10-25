# privacy-gateway-es

**Pseudonimización de datos personales en español para [Hermes Agent](https://hermes-agent.nousresearch.com)**, antes de enviar nada a un modelo en la nube.

Es un **instalador**: descarga el plugin de terceros `privacy-gateway` en un commit fijo, le añade cobertura española real (NIF/NIE con dígito de control, CIF, teléfonos, matrículas, referencia catastral, NUSS, pasaporte) y el motor spaCy en español, lo configura, lo habilita y **verifica el circuito completo**.

> **Si eres un agente de IA, lee `PARA-AGENTES.md` antes de tocar nada.** Resumen:
> `./install.sh --profile PERFIL --dry-run`, enseña el plan al usuario, luego
> `./install.sh --profile PERFIL`, y la verificación debe terminar en
> `RESULTADO: OK`. Nunca reinicies el gateway desde dentro del agente y nunca
> imprimas el valor de `HERMES_PRIVACY_GATEWAY_KEY`.

> **English summary** — Spanish-language PII pseudonymization for the third-party
> `privacy-gateway` plugin of Hermes Agent. This repository ships an **installer**
> (not the plugin): it downloads the upstream plugin at a pinned commit, adds
> local Spanish recognizers (tax IDs validated by checksum, phone numbers, licence
> plates, cadastral references, social security numbers, passports) plus a Spanish
> spaCy model, then runs an end-to-end self-test. No third-party code is
> redistributed. MIT licensed. Contact details at the bottom.

---

## Qué es (y qué no es)

Cuando usas un agente de IA con un modelo en la nube, el prompt sale de tu máquina con lo que haya dentro. Este sistema pone una capa **antes** de la salida hacia el proveedor y otra después de la respuesta:

- **Ida**: tu texto se sustituye por alias estables (`[ES_NIF_9CF2…]`, `[PERSON_5F72…]`) y el modelo nunca ve el dato real.
- **Vuelta**: la respuesta se rehidrata con los valores originales, así que tú lees la respuesta normal.

Los alias se guardan **cifrados y en local** para poder deshacer la sustitución. Por eso es **pseudonimización, no anonimización**: el dato real no se destruye, se sustituye de forma reversible y solo dentro de tu máquina.

Esto **no es un cortafuegos de datos**. El propio plugin se define como *implementación de referencia, no un producto DLP auditado*: bloquea la petición si falla la redacción (*fail-closed*), pero si el middleware no llegara a ejecutarse, la petición saldría sin tocar. Úsalo como una red de seguridad útil, no como una frontera de confidencialidad garantizada.

## Cómo funciona

```
tu prompt
   |
   +- 1. middleware "llm_request"  -->  motor NLP (Presidio + spaCy es)
   |                                     |- reconocedores por patrón con
   |                                     |  validación de dígito de control
   |                                     +- NER español (nombres, lugares, org.)
   |                                     |
   |                                     +- almacén local cifrado
   |                                        (alias <-> valor real)
   v
proveedor en la nube  <-- texto con alias, nunca datos reales
   |
   +- 2. hook "transform_llm_output"  -->  rehidratación desde el almacén
   v
tu respuesta, con los valores originales
```

Piezas:

- **Motor NLP**: Presidio Analyzer sobre spaCy. El idioma es configurable y aquí se fija en `es`.
- **Reconocedores por patrón**: la mayoría de los datos españoles se detectan con expresión regular **más validación de dígito de control** (letra del NIF/NIE, dígito del CIF), así que no dependen del modelo estadístico y funcionan igual en cualquier máquina.
- **NER español**: `es_core_news_lg`, para nombres de persona, lugares y organizaciones.
- **Almacén de alias**: cifrado, en local, con una clave que vive en el entorno del agente (`HERMES_PRIVACY_GATEWAY_KEY`).
- **Cobertura de herramientas**: además de las llamadas al modelo, se sanea también el resultado de las herramientas (`transform_tool_result`).

### Qué detecta

| Categoría | Detalle |
| --- | --- |
| NIF / NIE | Persona física, con validación de la letra de control |
| CIF | Persona jurídica, con validación del dígito de control |
| Teléfonos | Móvil (6/7) y fijo (8/9) españoles, con y sin prefijo |
| Matrículas | Formato español (incluido el histórico) |
| Referencia catastral | 20 caracteres, validada |
| NUSS | Número de la Seguridad Social |
| Pasaporte | Formato español |
| Nombres, lugares, organizaciones | NER del modelo español |
| Correo, IBAN, tarjetas | Reconocedores estándar de Presidio |

### Qué **no** cubre

- **Las llamadas auxiliares no pasan por el plugin**: títulos automáticos, resúmenes y compresión de contexto. Si ese flujo te importa, revísalo aparte.
- **Importes y fechas** pueden pseudonimizarse según el reconocedor y el umbral. Si te molesta, ajusta `score_threshold`.
- No es anonimización irreversible, ni un producto auditado (ver arriba).

## Requisitos

- **Hermes Agent >= 0.20.4** con el gestor de plugins disponible.
- **Linux** (probado en Ubuntu 26.04) o **macOS**.
- `python3` (el que gestione Hermes).
- **Red**: el instalador descarga el plugin original y el modelo de spaCy (~600 MB).
- Sin dependencias exóticas: no hace falta `patch` ni `git`.

## Cómo se usa

```bash
# 1. Ver qué haría, sin tocar nada
./install.sh --profile trabajo --dry-run

# 2. Instalar en el perfil "trabajo"
./install.sh --profile trabajo

# 3. Comprobar el circuito completo
./verify.sh --profile trabajo
```

Sin `--profile` se instala en el perfil `default`. Lo sensato es usarlo en un **perfil de trabajo** (y dejar los personales sin la capa), que es como está montado en producción.

**Qué hace el instalador, paso a paso:**

1. Comprueba Hermes, `python3` y la integridad del paquete.
2. Mira si el core de Hermes necesita el override de `numpy` (ver el asunto de numpy más abajo). No lo toca sin permiso.
3. Descarga el plugin **original** en un commit fijo y le aplica las ediciones españolas (`scripts/extend_es.py`) más `recognizers_es.py`. Regenera `MANIFEST.sha256`.
4. Genera una clave de 32 bytes para el almacén de alias y la guarda en el `.env` **global** del agente. **Nunca la muestra.**
5. Instala el modelo `es_core_news_lg` en el entorno gestionado que **realmente** ejecuta el gateway (lo localiza leyendo el proceso en marcha, no adivinando).
6. Escribe la configuración del plugin **bajo `settings:`**.
7. Habilita el plugin en modo *fail-closed*.
8. Recarga los plugins del gateway por su socket de control, **sin reiniciar el servicio** ni matar tus sesiones.
9. Verifica el circuito: ida pseudonimizada y vuelta rehidratada. Si algo falla, te lo dice.

**Opciones:**

| Opción | Qué hace |
| --- | --- |
| `--profile NOMBRE` | Perfil de Hermes destino (por defecto `default`) |
| `--hermes-home RUTA` | Raíz de Hermes (por defecto `$HERMES_HOME` o `~/.hermes`) |
| `--patch-core` | Autoriza modificar el `pyproject.toml` del core (override de numpy) |
| `--reapply` | Solo reaplica la ampliación española (tras actualizar el plugin) |
| `--no-reload` | No recargar el gateway al terminar |
| `--dry-run` | Mostrar lo que haría, sin tocar nada |
| `--unattended` | Sin preguntas (implica `--patch-core` si hiciera falta) |

**Desinstalar:**

```bash
./uninstall.sh --profile trabajo          # deshabilita y conserva todo
./uninstall.sh --profile trabajo --purge  # además aparta el plugin
```

Ni siquiera con `--purge` se borra la clave del almacén: sin ella no se descifra ningún alias guardado, así que se avisa y se deja a tu criterio.

## Verificación

`verify.sh` no es un «hola mundo»: carga la clave como en el arranque, resuelve la configuración por la misma regla que usa Hermes, registra el plugin de verdad y comprueba que ningún dato sensible sale hacia el proveedor y que la respuesta vuelve con los valores originales. Sale **0 solo si todo pasa**:

```
RESULTADO: OK - el privacy-gateway funciona end-to-end en espanol
```

Deliberadamente **no importa** módulos del core de Hermes: importarlos puede relanzar el script dentro del runtime gestionado, con otro `site-packages`, y la comprobación sería falsa. Lee el YAML y aplica la misma regla, sin efectos secundarios.

## Configuración

Dos claves, y una trampa:

```bash
hermes config set plugins.entries.privacy-gateway.settings.language es
hermes config set plugins.entries.privacy-gateway.settings.score_threshold 0.55
```

> **La configuración va obligatoriamente bajo `settings:`.** El plugin lee
> `plugins.entries.<id>.settings.<clave>` y nada más. Si pones `language` un nivel
> por encima, la ignora **en silencio**, el motor arranca en inglés y cada petición
> muere con un error que queda tapado por el propio bloqueo de seguridad. Es la
> causa raíz de un fallo real en producción, y por eso este paquete cambia el valor
> por defecto del motor a `es`: así una configuración mal puesta ya no cae en
> silencio al inglés.

## Mantenimiento

| Situación | Qué hacer |
| --- | --- |
| Actualizaste el plugin de terceros | `./install.sh --reapply` (la actualización borra la ampliación) |
| Actualizaste Hermes | `./install.sh --patch-core` y, si toca, `--reapply` |
| Hermes cambió de entorno gestionado | Vuelve a lanzarlo: reinstala el modelo en el entorno nuevo |
| Duda de si sigue bien | `./verify.sh --profile NOMBRE` |

### El asunto de `numpy` (la trampa más probable)

`presidio-analyzer` arrastra `spaCy`, que declara `numpy<2.5.0`, mientras Hermes fija `numpy==2.5.4` para voz y wake word. El gestor de plugins rechaza entonces la dependencia. La cota de spaCy es conservadora: funciona con numpy 2.5.4 (probado en Python 3.14 cargando `es_core_news_lg` en producción).

El arreglo es un override en `[tool.uv] override-dependencies` del `pyproject.toml` **del core de Hermes**. Como toca el core, **no se aplica sin `--patch-core`**, y el instalador hace copia de seguridad del fichero. Ese parche se pierde con cada `hermes update`; el instalador lo detecta y te lo dice.

## Estructura

```
install.sh                  instalador idempotente
verify.sh                   comprobación end-to-end (0 = todo bien)
uninstall.sh                desinstalador (--purge opcional)
README.md                   este documento
PARA-AGENTES.md             instrucciones para un agente de IA
AVISO-LICENCIA.md           licencias y por qué no se redistribuye el plugin
CHANGELOG.md                cambios
overlay/
  recognizers_es.py         reconocedores españoles (código propio)
  BASE_SHA                  commit fijo del plugin original
scripts/
  extend_es.py              aplica las ediciones sobre el plugin descargado
  e2e_check.py              el corazón de la verificación
  check-core-numpy.py       detecta el override de numpy (parser TOML real)
  patch-core-numpy.py       lo aplica, con copia de seguridad
  reload-gateway.py         recarga los plugins por el socket de control
  lib.sh                    utilidades (detección del entorno del gateway)
```

## Licencia

- **Este repositorio (instalador, reconocedores y scripts): MIT** — ver `LICENSE`.
- **El plugin original** (`privacy-gateway`, de [saiteja-madha](https://github.com/saiteja-madha/hermes-privacy-gateway)) **no se redistribuye aquí**: no tiene fichero de licencia, así que sus derechos quedan reservados. Este repositorio solo contiene código propio que lo descarga y lo modifica en tu máquina. Ver `AVISO-LICENCIA.md`.
- Si eres el autor del plugin original y quieres que se cambie el enfoque o que se retire algo, escríbeme y lo arreglo.

## Contacto

**Rafael Roa** — Arquitecto Técnico e Ingeniero de Edificación, CTO de System Arquitectura / Lem3a S.L. Escribo y divulgo sobre IA aplicada, software y arquitectura digital, sin humo.

- Blog: **[rafarq.com](https://rafarq.com)**
- Podcast: **«Tecnología sin fuegos artificiales»**
- GitHub: **[@rafarq](https://github.com/rafarq)**

Si este paquete te sirve, cuéntamelo: me interesa saber en qué perfil lo usas y qué datos españoles se te escapan, para afinar los reconocedores.