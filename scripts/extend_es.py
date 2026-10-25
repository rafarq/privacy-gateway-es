#!/usr/bin/env python3
"""Ampliacion espanola del privacy-gateway: aplica las ediciones sobre el plugin.

Este script es el equivalente funcional de un parche, pero **no contiene codigo
del proyecto original**: solo describe, con anclas exactas, las cuatro ediciones
que hay que hacer sobre los ficheros descargados. Asi este paquete se puede
distribuir sin redistribuir codigo de terceros, que no tiene licencia.

Ediciones:
  1. privacy.py   - engancha los reconocedores espanoles (recognizers_es.py).
  2. nlp.yaml     - motor spaCy en espanol (es_core_news_lg).
  3. plugin.yaml  - idioma por defecto del motor: en -> es.
  4. __init__.py  - idioma por defecto en el arranque: en -> es.

Uso: extend_es.py RUTA_DEL_PLUGIN

Es idempotente: si una edicion ya esta aplicada, la salta. Si un ancla no
aparece exactamente una vez, aborta sin dejar el fichero a medias (se escribe
con fichero temporal y renombrado atomico).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# --- 1. privacy.py: gancho de reconocedores espanoles -------------------------
HOOK_ES = '''        if language.startswith("es"):
            # Local extension (not upstream): Presidio's Spanish recognizers miss
            # company NIF/CIF, every Spanish phone format, plates, cadastral
            # references, NUSS and passports. See recognizers_es.py.
            try:
                from .recognizers_es import es_recognizers
            except ImportError:  # direct development import outside the package
                from recognizers_es import es_recognizers

            for es_recognizer in es_recognizers(language):
                self.analyzer.registry.add_recognizer(es_recognizer)

'''

EDICIONES = [
    {
        "fichero": "privacy.py",
        "que": "gancho de los reconocedores espanoles",
        "ya": "from .recognizers_es import es_recognizers",
        "ancla": "\n    @staticmethod\n    def remove_high_confidence_secrets(",
        "reemplazo": "\n" + HOOK_ES + "    @staticmethod\n"
                     "    def remove_high_confidence_secrets(",
    },
    {
        "fichero": "nlp.yaml",
        "que": "motor spaCy en espanol",
        "ya": "lang_code: es",
        "ancla": "  - lang_code: en\n    model_name: en_core_web_lg\n",
        "reemplazo": "  - lang_code: es\n    model_name: es_core_news_lg\n",
    },
    {
        "fichero": "plugin.yaml",
        "que": "idioma por defecto en el manifiesto (en -> es)",
        "ya": None,  # se comprueba con el ancla del bloque de abajo
        "ancla": ("  language:\n    type: str\n    default: en\n"
                  "    description: Language passed to Presidio Analyzer.\n"),
        "reemplazo": ("  language:\n    type: str\n    default: es\n"
                      "    description: Language passed to Presidio Analyzer.\n"),
    },
    {
        "fichero": "__init__.py",
        "que": "idioma por defecto en el arranque (en -> es)",
        "ya": '_config(ctx, "language", "es")',
        "ancla": 'language=str(_config(ctx, "language", "en")),',
        "reemplazo": 'language=str(_config(ctx, "language", "es")),',
    },
]


def escribir_atomico(destino: Path, texto: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(destino.parent), prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(texto)
    os.replace(tmp, destino)


def aplicar(plugin: Path) -> int:
    errores: list[str] = []

    for ed in EDICIONES:
        destino = plugin / ed["fichero"]
        if not destino.is_file():
            errores.append(f"{ed['fichero']}: no existe")
            continue

        texto = destino.read_text(encoding="utf-8")

        if ed["ya"] and ed["ya"] in texto:
            print(f"  ok   {ed['fichero']}: ya aplicado ({ed['que']})")
            continue

        veces = texto.count(ed["ancla"])
        if veces == 0:
            if ed["fichero"] == "plugin.yaml" and "default: es" in texto and "language:" in texto:
                print(f"  ok   {ed['fichero']}: ya aplicado ({ed['que']})")
                continue
            errores.append(
                f"{ed['fichero']}: no encuentro el ancla para '{ed['que']}'. "
                "El plugin original habra cambiado: este paquete esta anclado al "
                "commit indicado en overlay/BASE_SHA."
            )
            continue
        if veces > 1:
            errores.append(
                f"{ed['fichero']}: el ancla para '{ed['que']}' aparece {veces} veces; "
                "no toco nada para no equivocarme."
            )
            continue

        escribir_atomico(destino, texto.replace(ed["ancla"], ed["reemplazo"], 1))
        print(f"  ok   {ed['fichero']}: {ed['que']}")

    if errores:
        print("\nFALLO: no he podido aplicar la ampliacion:", file=sys.stderr)
        for e in errores:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    plugin = Path(argv[1]).resolve()
    if not (plugin / "__init__.py").is_file():
        print(f"FALLO: {plugin} no parece el plugin privacy-gateway", file=sys.stderr)
        return 2
    print(f"Aplicando la ampliacion espanola en {plugin}")
    return aplicar(plugin)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
