# Aviso de licencia y atribución

## Licencia de este repositorio

Todo el código de este repositorio (el instalador `install.sh`, `verify.sh`,
`uninstall.sh`, los scripts de `scripts/`, los reconocedores españoles
`overlay/recognizers_es.py` y la documentación) es **MIT**, en nombre de
Rafael Roa (Lem3a S.L.). Ver `LICENSE`.

## Código de terceros (plugin `privacy-gateway`)

- Origen: https://github.com/saiteja-madha/hermes-privacy-gateway
- Commit base: `032bda954ad89599c16b655c9b3d11c91083f3e3` (v0.1.1)
- Autor: Saiteja Madha y colaboradores.

**Este paquete no redistribuye el código original.** El instalador lo descarga
desde el repositorio del autor, fija ese commit y le aplica las modificaciones
**en tu máquina**.

Las modificaciones no viajan como parche ni como copia: `scripts/extend_es.py`
**no contiene código del original**, solo describe las cuatro ediciones (anclas y
reemplazos) que hay que hacer sobre los ficheros ya descargados. Es la forma de
compartir una ampliación sin repartir el trabajo de otro.

**Aviso importante**: en el momento de preparar este paquete, el repositorio
original **no incluía fichero de licencia**. Sin licencia explícita, los derechos
quedan reservados por defecto. Consecuencias:

- **Uso personal o interno**: sin problema.
- **Redistribución del código original** (el plugin o una copia modificada, y por
  extensión un fichero de parche con sus líneas dentro): requeriría permiso del
  autor. Por eso aquí **no se reparte nada suyo**.
- Si el autor publica una licencia, todo encaja sin fricción; si prefiere que no
  se amplíe su trabajo, escríbeme y lo retiro.

## Modelo spaCy

`es_core_news_lg` se descarga de los releases oficiales de Explosion y se
distribuye bajo **CC BY-SA 3.0**. **No se incluye** en este paquete: se descarga
durante la instalación, en tu máquina.

## Componentes que instala Hermes

`presidio-analyzer`, `spaCy` y demás dependencias las instala el gestor de
plugins de Hermes desde PyPI, con sus propias licencias (MIT y Apache-2.0, en
general). Este repositorio no las empaqueta ni las modifica, salvo el override de
`numpy` descrito en el README, que se aplica solo con `--patch-core` y sobre tu
propia instalación.