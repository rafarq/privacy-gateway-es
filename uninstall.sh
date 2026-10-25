#!/usr/bin/env bash
# Desinstala la ampliacion espanola del privacy-gateway.
#   ./uninstall.sh [--profile NOMBRE] [--hermes-home RUTA] [--purge] [--dry-run]
#     --purge   Borra tambien el directorio del plugin y la clave del .env
# Por defecto solo deshabilita el plugin y conserva los ficheros y la clave.

set -euo pipefail
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROFILE="default"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PURGE=0; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --profile)     PROFILE="$2"; shift 2 ;;
    --hermes-home) HERMES_HOME="$2"; shift 2 ;;
    --purge)       PURGE=1; shift ;;
    --dry-run)     DRY=1; shift ;;
    -h|--help)     sed -n '2,5p' "$0"; exit 0 ;;
    *) echo "Opcion desconocida: $1" >&2; exit 2 ;;
  esac
done

PROFILE_HOME="$HERMES_HOME"
[ "$PROFILE" = "default" ] || PROFILE_HOME="$HERMES_HOME/profiles/$PROFILE"
PLUGIN_DIR="$PROFILE_HOME/plugins/privacy-gateway"
GLOBAL_ENV="$HERMES_HOME/.env"
run() { if [ "$DRY" = 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

echo "==> Deshabilitando el plugin en el perfil '$PROFILE'"
if [ "$DRY" = 1 ]; then
  echo "  [dry-run] hermes plugins disable privacy-gateway"
else
  HERMES_HOME="$PROFILE_HOME" hermes plugins disable privacy-gateway 2>/dev/null || \
    echo "  (no estaba habilitado o no se pudo deshabilitar)"
fi

if [ "$PURGE" = 1 ]; then
  if [ -d "$PLUGIN_DIR" ]; then
    BK="$PLUGIN_DIR.bak-$(date +%Y%m%d-%H%M%S)"
    run mv "$PLUGIN_DIR" "$BK"
    echo "  plugin movido a $BK"
  fi
  if [ -f "$GLOBAL_ENV" ] && grep -q '^HERMES_PRIVACY_GATEWAY_KEY=' "$GLOBAL_ENV"; then
    echo "  AVISO: la clave HERMES_PRIVACY_GATEWAY_KEY sigue en $GLOBAL_ENV."
    echo "         Borrala a mano si de verdad quieres perder el almacen de alias."
    echo "         (No la toco: sin ella no se descifra ningun alias guardado.)"
  fi
fi

echo "==> Reinicia el gateway para que el cambio surta efecto:"
echo "      reinicia el servicio del gateway desde OTRA terminal (no desde el agente)"
