#!/usr/bin/env bash
# =============================================================================
#  privacy-gateway-es — instalador
#
#  Instala el plugin privacy-gateway (terceros) con la ampliacion espanola:
#  reconocedores locales de NIF/CIF, telefonos ES, matriculas, referencia
#  catastral, NUSS y pasaporte, y el motor spaCy en espanol.
#
#  No redistribuye codigo de terceros: descarga el plugin original desde su
#  repositorio, en un commit fijo, y le aplica las ediciones y los ficheros de
#  este paquete (scripts/extend_es.py + overlay/recognizers_es.py).
#  Ver AVISO-LICENCIA.md.
#
#  Uso:
#    ./install.sh [opciones]
#
#  Opciones:
#    --profile NOMBRE     Perfil de Hermes destino (por defecto: default)
#    --hermes-home RUTA   Raiz de Hermes (por defecto: $HERMES_HOME o ~/.hermes)
#    --patch-core         Autoriza parchear el core de Hermes (override de numpy)
#                         si el gestor de plugins rechaza la dependencia
#    --reapply            Solo reaplicar la ampliacion espanola (tras actualizar
#                         el plugin de terceros)
#    --no-reload          No intentar recargar el gateway al terminar
#    --dry-run            Mostrar lo que haria, sin tocar nada
#    --unattended         Sin preguntas (implica --patch-core si hiciera falta)
#    -h | --help          Esta ayuda
# =============================================================================

set -euo pipefail

# --- constantes del paquete ---------------------------------------------------
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERLAY="$PKG_DIR/overlay"
# shellcheck source=scripts/lib.sh
. "$PKG_DIR/scripts/lib.sh"
UPSTREAM_REPO="https://github.com/saiteja-madha/hermes-privacy-gateway"
BASE_SHA="$(cat "$OVERLAY/BASE_SHA" 2>/dev/null || echo "")"
MODEL_NAME="es_core_news_lg"
MODEL_VER="3.8.0"
MODEL_URL="https://github.com/explosion/spacy-models/releases/download/${MODEL_NAME}-${MODEL_VER}/${MODEL_NAME}-${MODEL_VER}-py3-none-any.whl"

# --- opciones -----------------------------------------------------------------
PROFILE="default"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
DO_PATCH_CORE=0
REAPPLY=0
DO_RELOAD=1
DRY=0
UNATTENDED=0

while [ $# -gt 0 ]; do
  case "$1" in
    --profile)      PROFILE="$2"; shift 2 ;;
    --hermes-home)  HERMES_HOME="$2"; shift 2 ;;
    --patch-core)   DO_PATCH_CORE=1; shift ;;
    --reapply)      REAPPLY=1; shift ;;
    --no-reload)    DO_RELOAD=0; shift ;;
    --dry-run)      DRY=1; shift ;;
    --unattended)   UNATTENDED=1; DO_PATCH_CORE=1; shift ;;
    -h|--help)      sed -n '2,27p' "$0"; exit 0 ;;
    *) echo "Opcion desconocida: $1" >&2; exit 2 ;;
  esac
done

# --- log ----------------------------------------------------------------------
c_ok=$'\033[32m'; c_warn=$'\033[33m'; c_err=$'\033[31m'; c_dim=$'\033[2m'; c_rst=$'\033[0m'
step() { printf '\n%s==> %s%s\n' "$c_dim" "$*" "$c_rst"; }
ok()   { printf '  %s✓%s %s\n' "$c_ok" "$c_rst" "$*"; }
warn() { printf '  %s!%s %s\n' "$c_warn" "$c_rst" "$*"; }
die()  { printf '\n%sERROR:%s %s\n' "$c_err" "$c_rst" "$*" >&2; exit 1; }
run()  { if [ "$DRY" = 1 ]; then printf '  %s[dry-run]%s %s\n' "$c_dim" "$c_rst" "$*"; else "$@"; fi; }

# =============================================================================
step "0. Comprobaciones previas"
# =============================================================================
[ -n "$BASE_SHA" ] || die "falta overlay/BASE_SHA (paquete incompleto)"
[ -f "$OVERLAY/recognizers_es.py" ] || die "falta overlay/recognizers_es.py"
[ -f "$PKG_DIR/scripts/extend_es.py" ] || die "falta scripts/extend_es.py (paquete incompleto)"
command -v hermes  >/dev/null || die "'hermes' no esta en el PATH"
command -v python3 >/dev/null || die "falta python3"

PROFILE_HOME="$HERMES_HOME"
[ "$PROFILE" = "default" ] || PROFILE_HOME="$HERMES_HOME/profiles/$PROFILE"
[ -d "$PROFILE_HOME" ] || die "no existe el perfil '$PROFILE' ($PROFILE_HOME)"

PLUGIN_DIR="$PROFILE_HOME/plugins/privacy-gateway"
CONFIG_YAML="$PROFILE_HOME/config.yaml"
GLOBAL_ENV="$HERMES_HOME/.env"
HERMES_AGENT="$HERMES_HOME/hermes-agent"

HERMES_VER="$(hermes --version 2>/dev/null | head -1 || echo '?')"
ok "hermes: $HERMES_VER"
ok "perfil destino: $PROFILE ($PROFILE_HOME)"
ok "commit base del plugin: ${BASE_SHA:0:12}"
if [ "$DRY" = 1 ]; then warn "modo dry-run: no se escribira nada"; fi

# =============================================================================
step "1. Dependencia numpy del core (spaCy exige numpy<2.5)"
# =============================================================================
# presidio-analyzer -> spaCy 3.8.16 declara numpy<2.5.0, mientras Hermes fija
# numpy==2.5.4 para voz/wake. Sin un override, el gestor de plugins rechaza la
# dependencia y 'hermes plugins enable' falla. El cap de spaCy es conservador:
# spaCy 3.8.16 funciona con numpy 2.5.4 (verificado en Python 3.14).
CORE_PYPROJECT="$HERMES_AGENT/pyproject.toml"
if [ -f "$CORE_PYPROJECT" ]; then
  # OJO: '"numpy==2.5.4"' aparece ya en los extras de voz/wake de Hermes, asi que
  # no sirve como senal. Comprobamos la lista override-dependencies de verdad.
  if python3 "$PKG_DIR/scripts/check-core-numpy.py" "$CORE_PYPROJECT" >/dev/null 2>&1; then
    ok "override de numpy ya presente en el core"
    CORE_NEEDS_PATCH=0
  else
    CORE_NEEDS_PATCH=1
  fi
else
  warn "no encuentro $CORE_PYPROJECT (¿Hermes instalado de otra forma?)"
  CORE_NEEDS_PATCH=0
fi

if [ "$CORE_NEEDS_PATCH" = 1 ]; then
  if [ "$DO_PATCH_CORE" = 1 ]; then
    run python3 "$PKG_DIR/scripts/patch-core-numpy.py" "$CORE_PYPROJECT"
  else
    warn "el core de Hermes NO tiene el override de numpy."
    warn "si 'hermes plugins enable' falla por numpy, reejecuta con --patch-core."
  fi
fi

# =============================================================================
step "2. Instalacion del plugin original (commit fijo)"
# =============================================================================
if [ "$REAPPLY" = 1 ]; then
  [ -d "$PLUGIN_DIR" ] || die "--reapply: el plugin no esta instalado en $PLUGIN_DIR"
  ok "modo reapply: conservo el plugin instalado"
elif [ "$DRY" = 1 ]; then
  EXTRA=""
  if [ -d "$PLUGIN_DIR" ]; then EXTRA=" --force"; fi
  printf '  %s[dry-run]%s hermes plugins install %s --ref %s --yes-deps --no-enable%s\n' \
    "$c_dim" "$c_rst" "$UPSTREAM_REPO" "${BASE_SHA:0:12}" "$EXTRA"
  ok "plugin se instalaria en el commit base"
else
  if [ -d "$PLUGIN_DIR" ]; then
    warn "ya existe $PLUGIN_DIR; reinstalo en el commit base (tus ficheros siguen)"
  fi
  install_plugin() {
    if [ -d "$PLUGIN_DIR" ]; then
      hermes plugins install "$UPSTREAM_REPO" --ref "$BASE_SHA" --force --yes-deps --no-enable
    else
      hermes plugins install "$UPSTREAM_REPO" --ref "$BASE_SHA" --yes-deps --no-enable
    fi
  }
  if OUT="$(install_plugin 2>&1)"; then
    ok "plugin instalado en el commit base ${BASE_SHA:0:12}"
  else
    printf '%s\n' "$OUT" >&2
    if printf '%s' "$OUT" | grep -qi 'numpy'; then
      die "el gestor de plugins rechaza numpy. Reejecuta con --patch-core y vuelve a lanzar."
    fi
    die "no se pudo instalar el plugin"
  fi
fi

# =============================================================================
step "3. Ampliacion espanola (ediciones + reconocedores)"
# =============================================================================
[ "$DRY" = 1 ] || [ -d "$PLUGIN_DIR" ] || die "no existe $PLUGIN_DIR tras la instalacion"

# Las ediciones se aplican con scripts/extend_es.py, que NO contiene codigo del
# original: solo anclas y reemplazos. Asi se pueden distribuir sin redistribuir
# el plugin de terceros (no tiene licencia). Es idempotente.
if [ "$DRY" = 1 ]; then
  printf '  %s[dry-run]%s python3 scripts/extend_es.py %s\n' "$c_dim" "$c_rst" "$PLUGIN_DIR"
  printf '  %s[dry-run]%s cp overlay/recognizers_es.py %s/recognizers_es.py\n' "$c_dim" "$c_rst" "$PLUGIN_DIR"
else
  python3 "$PKG_DIR/scripts/extend_es.py" "$PLUGIN_DIR" || die "no he podido aplicar la ampliacion espanola"
  cp "$OVERLAY/recognizers_es.py" "$PLUGIN_DIR/recognizers_es.py"
  ok "ampliacion aplicada (gancho de reconocedores, nlp.yaml en es, default es)"
fi

if [ "$DRY" = 0 ]; then
  # Portabilidad Linux (sha256sum) / macOS (shasum -a 256).
  if command -v sha256sum >/dev/null; then SUM="sha256sum"; else SUM="shasum -a 256"; fi
  ( cd "$PLUGIN_DIR" && find . -type f \
      -not -path './.git/*' -not -name 'MANIFEST.sha256' -not -path './__pycache__/*' \
      -print | sed 's|^\./||' | sort | xargs $SUM > MANIFEST.sha256 )
  ok "MANIFEST.sha256 regenerado"
fi

# =============================================================================
step "4. Clave del almacen de alias"
# =============================================================================
# El plugin la lee de os.environ. Hermes solo vuelca a os.environ el .env GLOBAL
# (el .env de un perfil no global no llega al proceso). Por eso va al global.
if [ -f "$GLOBAL_ENV" ] && grep -q '^HERMES_PRIVACY_GATEWAY_KEY=' "$GLOBAL_ENV"; then
  ok "HERMES_PRIVACY_GATEWAY_KEY ya definida en $GLOBAL_ENV"
else
  if [ "$DRY" = 1 ]; then
    printf '  %s[dry-run]%s generaria clave de 32 bytes y la anadiria a %s\n' "$c_dim" "$c_rst" "$GLOBAL_ENV"
  else
    KEY="$(python3 -c 'import base64,secrets;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
    touch "$GLOBAL_ENV"; chmod 600 "$GLOBAL_ENV"
    printf '\n# privacy-gateway: protege el almacen local de alias.\n# NO la pierdas: sin ella el almacen no se puede descifrar.\nHERMES_PRIVACY_GATEWAY_KEY=%s\n' "$KEY" >> "$GLOBAL_ENV"
    unset KEY
    ok "clave generada y anadida a $GLOBAL_ENV (permisos 600) — valor NO mostrado"
    warn "guarda copia de esa clave aparte: sin ella no se recupera el almacen"
  fi
fi

# =============================================================================
step "5. Modelo spaCy en espanol (${MODEL_NAME} ${MODEL_VER})"
# =============================================================================
UV="$(pgw_uv "$HERMES_HOME")"
[ -n "$UV" ] && ok "uv: $UV" || warn "sin uv; usare pip del entorno"

# Entornos gestionados que ejecutan Hermes (el del gateway en marcha primero:
# el orden importa y ya viene sin duplicados de pgw_detect_envs).
ENVS="$(pgw_detect_envs "$HERMES_HOME" || true)"
if [ -z "$ENVS" ]; then
  warn "no he localizado el entorno gestionado del gateway."
  warn "instala el modelo a mano en el entorno que ejecuta Hermes:"
  warn "  $UV pip install --no-deps $MODEL_URL"
  TARGET_ENV=""
else
  ok "entornos detectados:"; echo "$ENVS" | sed 's/^/      /'
  TARGET_ENV="$(echo "$ENVS" | head -1)"
fi

if [ -n "$TARGET_ENV" ]; then
  PY="$TARGET_ENV/venv/bin/python"
  if [ "$DRY" = 0 ] && "$PY" -c "import spacy.util,sys; sys.exit(0 if spacy.util.is_package('$MODEL_NAME') else 1)" 2>/dev/null; then
    ok "$MODEL_NAME ya instalado en $TARGET_ENV"
  else
    if [ -n "$UV" ]; then
      run "$UV" pip install --python "$PY" --no-deps "$MODEL_URL"
    else
      run "$TARGET_ENV/venv/bin/pip" install --no-deps "$MODEL_URL"
    fi
    if [ "$DRY" = 1 ]; then
      ok "$MODEL_NAME se instalaria en $TARGET_ENV/venv"
    else
      ok "modelo instalado en $TARGET_ENV/venv"
    fi
  fi
fi

# =============================================================================
step "6. Configuracion del plugin (claves bajo 'settings:')"
# =============================================================================
# El plugin lee SOLO plugins.entries.<id>.settings.<clave>. Si language queda un
# nivel por encima, se ignora en silencio, el motor arranca en ingles y cada
# peticion falla con KeyError 'en' (el plugin lo tapa con el block marker).
if [ "$DRY" = 1 ]; then
  printf '  %s[dry-run]%s hermes config set plugins.entries.privacy-gateway.settings.language es --force\n' "$c_dim" "$c_rst"
  printf '  %s[dry-run]%s hermes config set plugins.entries.privacy-gateway.settings.score_threshold 0.55 --force\n' "$c_dim" "$c_rst"
else
  HERMES_HOME="$PROFILE_HOME" hermes config set plugins.entries.privacy-gateway.settings.language es --force >/dev/null
  HERMES_HOME="$PROFILE_HOME" hermes config set plugins.entries.privacy-gateway.settings.score_threshold 0.55 --force >/dev/null
  ok "settings.language=es y settings.score_threshold=0.55"
fi

# =============================================================================
step "7. Habilitacion del plugin"
# =============================================================================
enable_plugin() {
  HERMES_HOME="$PROFILE_HOME" hermes plugins enable privacy-gateway --no-allow-tool-override
}

if [ "$DRY" = 1 ]; then
  printf '  %s[dry-run]%s hermes plugins enable privacy-gateway --no-allow-tool-override\n' "$c_dim" "$c_rst"
else
  if OUT="$(enable_plugin 2>&1)"; then
    ok "plugin habilitado (fail-closed: solo permite override de herramientas si lo autorizas)"
  else
    if printf '%s' "$OUT" | grep -qi 'numpy'; then
      if [ "$DO_PATCH_CORE" = 1 ]; then
        warn "el gestor de plugins rechaza numpy; aplico el override del core y reintento"
        python3 "$PKG_DIR/scripts/patch-core-numpy.py" "$CORE_PYPROJECT"
        enable_plugin || die "sigue fallando la habilitacion: $OUT"
        ok "plugin habilitado tras el override de numpy"
      else
        printf '%s\n' "$OUT" >&2
        die "bloqueado por la dependencia numpy. Reejecuta con --patch-core (parchea el core de Hermes) y vuelve a lanzar."
      fi
    else
      printf '%s\n' "$OUT" >&2
      die "no se pudo habilitar el plugin"
    fi
  fi
fi

# =============================================================================
step "8. Recarga del gateway"
# =============================================================================
if [ "$DRY" = 1 ]; then
  printf '  %s[dry-run]%s recargaria los plugins por el socket de control (sin reiniciar el servicio)\n' "$c_dim" "$c_rst"
elif [ "$DO_RELOAD" = 0 ]; then
  warn "recarga no solicitada. Reinicia tu gateway para activar los cambios."
else
  if python3 "$PKG_DIR/scripts/reload-gateway.py" "$HERMES_HOME" "$PROFILE_HOME" 2>/dev/null; then
    ok "plugins recargados en el gateway (sin reiniciar el servicio)"
  else
    warn "no he podido recargar por el socket de control."
    warn "para activar los cambios, reinicia el servicio del gateway desde OTRA terminal."
  fi
fi

# =============================================================================
step "9. Verificacion"
# =============================================================================
if [ "$DRY" = 1 ]; then
  warn "dry-run: omito la verificacion"
else
  bash "$PKG_DIR/verify.sh" --profile "$PROFILE" --hermes-home "$HERMES_HOME" || \
    die "la verificacion ha fallado; revisa la salida de arriba"
fi

printf '\n%sInstalacion completada.%s Perfil: %s\n' "$c_ok" "$c_rst" "$PROFILE"
cat <<'FIN'

Notas:
  - Prompts/respuestas y llamadas auxiliares (titulos, resumenes, compresion)
    NO pasan por este plugin. Es pseudonimizacion, no un cortafuegos de datos.
  - El README del plugin lo dice claro: es una implementacion de referencia, no
    un producto DLP auditado.
FIN
