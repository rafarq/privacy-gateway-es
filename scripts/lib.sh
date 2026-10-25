# shellcheck shell=bash
# Utilidades compartidas por install.sh y verify.sh.

# Ruta al binario uv que usa Hermes (el mas nuevo en tools/), o al del PATH.
pgw_uv() {
  local hermes_home="$1" cand
  cand="$(ls -1 "$hermes_home"/tools/uv-*/uv 2>/dev/null | sort -V | tail -1 || true)"
  if [ -n "$cand" ]; then echo "$cand"; return 0; fi
  command -v uv 2>/dev/null || true
}

# Entornos Python gestionados que ejecutan Hermes, en orden de preferencia:
# primero el que usa el gateway en marcha (leyendo /proc/PID/maps), luego el
# resto. Siempre emite el directorio del entorno (SIN '/venv' final) y sin
# duplicados, para poder componer '<env>/venv/bin/python'.
pgw_detect_envs() {
  local hermes_home="$1" pid v e norm visto=""
  _pgw_emit() {
    norm="${1%/venv}"; norm="${norm%/}"
    [ -n "$norm" ] || return 0
    case " $visto " in *" $norm "*) return 0 ;; esac
    visto="$visto $norm"; echo "$norm"
  }

  for unit in hermes-gateway.service; do
    pid="$(systemctl show -p MainPID --value "$unit" 2>/dev/null || true)"
    if [ -n "${pid:-}" ] && [ "$pid" != "0" ] && [ -r "/proc/$pid/maps" ]; then
      while read -r e; do
        [ -n "$e" ] || continue
        _pgw_emit "$e"
      done < <(grep -o "$hermes_home/installs/[^ ]*" "/proc/$pid/maps" 2>/dev/null | sed 's|/lib/.*||')
    fi
  done

  for v in "$hermes_home"/installs/*/environments/*/venv; do
    [ -x "$v/bin/python" ] || continue
    if "$v/bin/python" -c 'import presidio_analyzer' >/dev/null 2>&1; then
      _pgw_emit "$v"
    fi
  done
}

# Interprete que pueda importar TODO lo que necesita la verificacion: spaCy,
# presidio y las dependencias de Hermes (dotenv, yaml).
pgw_best_python() {
  local hermes_home="$1" env_dir py
  while read -r env_dir; do
    [ -n "$env_dir" ] || continue
    py="$env_dir/venv/bin/python"
    [ -x "$py" ] || continue
    if "$py" -c 'import spacy, presidio_analyzer, dotenv, yaml' >/dev/null 2>&1; then
      echo "$py"; return 0
    fi
  done < <(pgw_detect_envs "$hermes_home")
  return 1
}
