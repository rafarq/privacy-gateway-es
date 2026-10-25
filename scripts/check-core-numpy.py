#!/usr/bin/env python3
"""Comprueba si el core de Hermes ya tiene el override de numpy para spaCy.

Parsea el pyproject con tomllib y mira [tool.uv] override-dependencies. No vale
buscar '"numpy==2.5.4"' en el texto: ese pin aparece tambien en los extras de
voz/wake, y el propio listado de overrides lleva comentarios con corchetes
('see the cryptography pin in [project].dependencies'), asi que un regex se
cortaria antes de tiempo.

Uso: check-core-numpy.py RUTA/pyproject.toml
Sale 0 si hay override de numpy; 1 si no.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def overrides_tomllib(text: str) -> list[str] | None:
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:
        return None
    try:
        datos = tomllib.loads(text)
    except Exception:
        return None
    return (datos.get("tool", {}).get("uv", {}) or {}).get("override-dependencies")


def overrides_manual(text: str) -> list[str]:
    """Plan B sin tomllib: lee desde 'override-dependencies = [' hasta ']' solo."""
    lineas = text.splitlines()
    salida: list[str] = []
    dentro = False
    for linea in lineas:
        if not dentro:
            if re.search(r"override-dependencies\s*=\s*\[", linea):
                dentro = True
                resto = linea.split("[", 1)[1]
                if resto.strip() == "]":
                    return []
            continue
        if linea.strip() == "]":
            return salida
        salida.append(linea)
    return salida


def tiene_numpy(text: str) -> bool:
    entradas = overrides_tomllib(text)
    if entradas is None:
        entradas = overrides_manual(text)
    for e in entradas or []:
        if str(e).strip().strip('"').startswith("numpy"):
            return True
    return False


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    return 0 if tiene_numpy(Path(argv[1]).read_text(encoding="utf-8")) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
