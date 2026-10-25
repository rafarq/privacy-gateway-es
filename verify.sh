#!/usr/bin/env bash
# Verificacion end-to-end del privacy-gateway espanol.
#   ./verify.sh [--profile NOMBRE] [--hermes-home RUTA]
# Sale 0 solo si todas las comprobaciones pasan.

set -euo pipefail
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
. "$PKG_DIR/scripts/lib.sh"

PROFILE="default"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
while [ $# -gt 0 ]; do
  case "$1" in
    --profile)     PROFILE="$2"; shift 2 ;;
    --hermes-home) HERMES_HOME="$2"; shift 2 ;;
    -h|--help)     sed -n '2,4p' "$0"; exit 0 ;;
    *) echo "Opcion desconocida: $1" >&2; exit 2 ;;
  esac
done

PROFILE_HOME="$HERMES_HOME"
[ "$PROFILE" = "default" ] || PROFILE_HOME="$HERMES_HOME/profiles/$PROFILE"

PY="$(pgw_best_python "$HERMES_HOME" || true)"
if [ -z "$PY" ]; then
  echo "No encuentro un interprete con spaCy y presidio. Ajusto con el del sistema." >&2
  PY="$(command -v python3)"
  "${PY}" -c 'import spacy, presidio_analyzer' 2>/dev/null || {
    echo "AVISO: al interprete del sistema le faltan spaCy o presidio." >&2
    echo "       Instala el modelo con: $(pgw_uv "$HERMES_HOME" || echo uv) pip install --no-deps \\" >&2
    echo "         https://github.com/explosion/spacy-models/releases/download/es_core_news_lg-3.8.0/es_core_news_lg-3.8.0-py3-none-any.whl" >&2
  }
fi

echo "==> Verificacion con: $PY"
exec "$PY" "$PKG_DIR/scripts/e2e_check.py" "$HERMES_HOME" "$PROFILE_HOME"
