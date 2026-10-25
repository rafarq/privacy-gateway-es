#!/usr/bin/env python3
"""Recarga los plugins del gateway de Hermes por su socket de control.

El plugin privacy-gateway cachea el motor NLP en una variable global del modulo
(_ENGINE). Tras cambiar la configuracion hay que invalidarla: recargar plugins
borra el modulo de sys.modules y el motor se reconstruye en la siguiente
peticion, sin reiniciar el servicio ni matar las sesiones en curso.

Uso: reload-gateway.py HERMES_HOME PERFIL_HOME
Sale 0 si lo consigue; != 0 para que el instalador sugiera reiniciar el gateway.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SNIPPET = r'''
import os, sys
from pathlib import Path
from gateway.control_socket import reload_gateway_plugins

root = Path(sys.argv[1]); prof = Path(sys.argv[2])
verbose = os.environ.get("PGW_VERBOSE") == "1"
malo = False
for home in (root, prof):
    try:
        res = reload_gateway_plugins(root, profile_home=home)
    except TypeError:
        res = reload_gateway_plugins(home)
    if verbose or not isinstance(res, dict):
        print(f"{home}: {res}")
        continue
    recargado = bool(res.get("reloaded"))
    plugins = res.get("plugins") or []
    pgw = "privacy-gateway" in plugins
    print(f"  {'ok ' if recargado else 'mal'} {home} — recargado={recargado}, "
          f"{len(plugins)} plugins, privacy-gateway={'si' if pgw else 'no'}")
    malo = malo or not recargado
sys.exit(1 if malo else 0)
'''


def candidate_pythons(hermes_home: Path):
    for venv in sorted(hermes_home.glob("installs/*/environments/*/venv/bin/python")):
        yield venv
    yield Path(sys.executable)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2

    hermes_home = Path(argv[1]).resolve()
    profile_home = Path(argv[2]).resolve()
    agent = hermes_home / "hermes-agent"

    env = dict(os.environ)
    env["HERMES_HOME"] = str(hermes_home)
    env["PYTHONPATH"] = os.pathsep.join([str(agent), str(hermes_home)])

    for py in candidate_pythons(hermes_home):
        if not py.is_file():
            continue
        try:
            probe = subprocess.run(
                [str(py), "-c", "import gateway.control_socket"],
                env=env, capture_output=True, timeout=60,
            )
        except Exception:
            continue
        if probe.returncode != 0:
            continue

        res = subprocess.run(
            [str(py), "-c", SNIPPET, str(hermes_home), str(profile_home)],
            env=env, capture_output=True, text=True, timeout=120,
        )
        if res.returncode == 0:
            sys.stdout.write(res.stdout)
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
