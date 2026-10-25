#!/usr/bin/env python3
"""Anade el override de numpy al core de Hermes, de forma idempotente.

spaCy 3.8.16 (dependencia de presidio-analyzer, que necesita privacy-gateway)
declara numpy<2.5.0, mientras Hermes fija numpy==2.5.4 para voz/wake. uv permite
sobreescribir esa cota con [tool.uv] override-dependencies. El cap de spaCy es
conservador: spaCy 3.8.16 funciona con numpy 2.5.4 (probado en Python 3.14 con
es_core_news_lg).

Uso: patch-core-numpy.py RUTA/pyproject.toml
Sale 0 si lo aplica o si ya estaba; != 0 si no encuentra donde insertarlo.
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER = "privacy-gateway-es: override de numpy"
ENTRY = '  "numpy==2.5.4",'
NOTE = (
    f"  # {MARKER} para que uv acepte spaCy (numpy<2.5.0) junto al pin\n"
    "  # numpy==2.5.4 de voz/wake. Quitar cuando spaCy suba la cota.\n"
)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2

    path = Path(argv[1])
    if not path.is_file():
        print(f"no existe {path}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")

    if MARKER in text:
        print("override de numpy ya presente; nada que hacer")
        return 0

    if "override-dependencies" not in text:
        print("no encuentro [tool.uv] override-dependencies en el pyproject", file=sys.stderr)
        return 1

    nuevo, n = re.subn(
        r"(override-dependencies\s*=\s*\[\n)",
        r"\1" + NOTE + ENTRY + "\n",
        text,
        count=1,
    )
    if n != 1:
        print("no he podido localizar el inicio de override-dependencies", file=sys.stderr)
        return 1

    backup = path.with_suffix(path.suffix + f".bak-pgwnumpy-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(path, backup)

    if '"numpy==2.5.4"' in nuevo:
        # El pin directo ya existe en [project]; el override es lo nuevo.
        pass
    path.write_text(nuevo, encoding="utf-8")
    print(f"override anadido. Copia de seguridad: {backup.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
