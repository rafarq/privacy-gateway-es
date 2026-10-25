# PARA-AGENTES.md — instrucciones para un agente de IA

Este fichero existe para que **un agente de Hermes** (u otro agente de codigo)
pueda instalar este paquete sin leer todo el README. Si eres el agente: lee esto
entero antes de ejecutar nada. Si eres una persona, ve a `README.md`.

## Que es esto

`privacy-gateway-es` es un **instalador** de pseudonimizacion de datos personales
espanoles para Hermes. **No contiene el plugin**: descarga el plugin de terceros
`privacy-gateway` desde su repositorio, en el commit fijo `032bda95`, y le aplica
las ediciones necesarias para anadir cobertura espanola (NIF/NIE con digito de
control, CIF, telefonos ES, matricula, referencia catastral, NUSS, pasaporte) y
el motor spaCy `es_core_news_lg`.

No redistribuyas el plugin original: no tiene licencia. Ver `AVISO-LICENCIA.md`.

## Orden de acciones (no te saltes pasos)

1. **Comprueba los requisitos**: Hermes >= 0.20.4 instalado, `python3` y red.
   Pregunta al usuario en que **perfil** quiere instalarlo si no te lo ha dicho
   (por defecto `default`; lo habitual es un perfil de trabajo).

2. **Ensena primero el plan**, sin tocar nada:

   > ./install.sh --profile PERFIL --dry-run

   Revisa la salida y presentasela al usuario. Si algo no cuadra (entorno
   detectado, commit base, ruta del perfil), para y consulta.

3. **Instala**:

   > ./install.sh --profile PERFIL

   `--unattended` evita preguntas, pero **implica autorizar parchear el core de
   Hermes** (ver la trampa de numpy mas abajo). No lo uses sin permiso explicito.

4. **Verifica**. El instalador ya llama a `verify.sh` en su paso 9; si lo
   ejecutas aparte, la salida debe terminar exactamente en:

   > RESULTADO: OK - el privacy-gateway funciona end-to-end en espanol

   Cualquier `FALLO` es un fallo real: no lo presentes como exito.

5. **El gateway debe recargar los plugins**. El instalador lo hace por el socket
   de control, sin reiniciar el servicio. Si el paso 8 avisa de que no pudo, el
   cambio **no** estara activo hasta que el usuario reinicie el gateway.

## Reglas duras (violarlas rompe cosas)

- **Nunca reinicies ni pares el gateway desde dentro del propio agente.** El
  proceso que te ejecuta muere con el. Pide al usuario que lo haga en otra
  terminal, o usa la recarga por socket, que es lo que hace este paquete.
- **Nunca imprimas la clave** `HERMES_PRIVACY_GATEWAY_KEY`. El instalador la
  genera y la escribe en el `.env` **global** de Hermes sin mostrarla. Si tienes
  que comprobar que existe, comprueba el nombre o su longitud, no el valor.
- **La configuracion del plugin va bajo `settings:`**, o sea
  `plugins.entries.privacy-gateway.settings.<clave>`. Si la pones un nivel por
  encima, el plugin la ignora en silencio y el motor arranca en ingles. Es la
  causa raiz de un fallo en produccion; no la reintroduzcas.
- **No borres alias ni el almacen.** Es pseudonimizacion: los alias cifrados
  permiten rehidratar. `uninstall.sh` sin `--purge` conserva todo a proposito.
- **`--patch-core` solo con permiso del usuario.** Toca el `pyproject.toml` del
  core de Hermes.

## Trampa de numpy (la mas probable)

`presidio-analyzer` arrastra `spaCy`, que declara `numpy<2.5.0`, y Hermes fija
`numpy==2.5.4`. El gestor de plugins rechaza la dependencia. El arreglo es un
override en `[tool.uv] override-dependencies` del core de Hermes, y **toca el
core**, asi que no se aplica sin `--patch-core`.

- Sintoma: `hermes plugins install` o `enable` falla citando `numpy`.
- Que hace el paquete: lo detecta (`scripts/check-core-numpy.py`), te lo dice y
  lo aplica solo si le das `--patch-core` (`scripts/patch-core-numpy.py`, con
  copia de seguridad del fichero).
- **Tras cada `hermes update` se pierde**: vuelve a lanzar
  `./install.sh --patch-core` y despues `./install.sh --reapply`.

## Si algo va mal

- **`RuntimeError: spaCy model 'es_core_news_lg' is not installed`**: el modelo
  esta en un entorno gestionado distinto del que ejecuta el gateway. Vuelve a
  lanzar `./install.sh --profile PERFIL` (localiza el entorno del gateway leyendo
  su proceso en marcha) y **no** reinicies el gateway dentro del agente.
- **El plugin bloquea peticiones**: es *fail-closed*, es lo esperado si el motor
  no arranca. Mira `verify.sh`, que imprime la causa real del fallo del motor.
- **`verify.sh` falla al importar `spacy` o `presidio`**: estas ejecutandolo con
  un interprete equivocado. Deja que lo elija el propio script; no fuerces un
  `python3` del PATH.
- **Tras actualizar el plugin de terceros** (no Hermes): `./install.sh --reapply`
  reaplica las ediciones, porque una actualizacion del plugin borra la ampliacion.

## Ficheros que importan

- `install.sh` — instalador idempotente. Opciones: `--profile`, `--hermes-home`,
  `--patch-core`, `--reapply`, `--no-reload`, `--dry-run`, `--unattended`.
- `verify.sh` — comprobacion end-to-end. Sale 0 solo si todo pasa.
- `uninstall.sh` — deshabilita; `--purge` aparta el plugin (no borra la clave).
- `scripts/extend_es.py` — aplica las ediciones espanolas sobre el plugin ya
  descargado. No contiene codigo del original: anclas y reemplazos, idempotente.
  Si un ancla no aparece, aborta en vez de dejar el fichero a medias.
- `scripts/e2e_check.py` — el corazon de la verificacion. **No importa modulos
  del core de Hermes a proposito**: importarlos relanza el script dentro del
  runtime gestionado, con otro `site-packages`, y la comprobacion seria falsa.
  No lo "mejores" anadiendo `from hermes_cli import ...`.
- `overlay/` — `recognizers_es.py` (codigo propio) y el commit base.
- `README.md` — version para humanos. `AVISO-LICENCIA.md` — por que no se
  redistribuye el plugin.
