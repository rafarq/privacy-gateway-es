#!/usr/bin/env python3
"""Verificacion end-to-end del privacy-gateway con la ampliacion espanola.

Ejercita el camino real del plugin dentro del entorno Python que usa el gateway:
carga la clave como en el arranque, lee la configuracion por la MISMA ruta que
usa Hermes para los plugins, registra el plugin y comprueba ida y vuelta de la
pseudonimizacion.

Deliberadamente NO importa hermes_cli ni gateway: importar esos modulos puede
relanzar el script dentro del runtime gestionado de Hermes (venv_sync.relaunch),
con un interprete aislado (-I) y otro site-packages, lo que invalidaria la
comprobacion y ademas podria disparar una sincronizacion de venv. La
configuracion se lee del YAML aplicando la regla de Hermes
(plugins.entries.<id>.settings.<clave>, ver hermes_cli/plugins.py).

La salida va a stdout en texto plano; el codigo de salida es 0 solo si todo pasa.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from pathlib import Path

TEXTO = (
    "Cliente: Rafael Roa, DNI 12345678Z, movil 655123456, "
    "correo rafael.roa@example.com. Obra industrial en Malaga, "
    "CIF B93133742, presupuesto 125.000 euros, 250 m2."
)

PLUGIN_ID = "privacy-gateway"
CLAVES = ("language", "score_threshold")

fallos: list[str] = []


def check(cond: bool, msg: str, detalle: str = "") -> None:
    if cond:
        print(f"  OK   {msg}")
    else:
        print(f"  FALLO {msg}" + (f"  [{detalle}]" if detalle else ""))
        fallos.append(msg)


class Ctx:
    """ctx minimo con la misma interfaz que usa el plugin."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.mw: dict = {}
        self.hooks: dict = {}

    def get_config(self, key, default=None):
        return self.cfg.get(key, default)

    def register_middleware(self, name, fn):
        self.mw[name] = fn

    def register_hook(self, name, fn):
        self.hooks[name] = fn


def _leer_env(ficheros: tuple[Path, ...]) -> dict:
    """Lee pares CLAVE=valor de los .env, con la tolerancia de python-dotenv."""
    out: dict = {}
    for f in ficheros:
        if not f.is_file():
            continue
        for linea in f.read_text(encoding="utf-8", errors="replace").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, _, v = linea.partition("=")
            k = k.strip().removeprefix("export ").strip()
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                v = v[1:-1]
            if k:
                out[k] = v
    return out


def entrada_plugin(datos: dict) -> dict:
    plugins = datos.get("plugins") or {}
    entries = plugins.get("entries") or {}
    return entries.get(PLUGIN_ID) or {}


def main(argv: list[str]) -> int:
    hermes_home = Path(argv[1]).resolve() if len(argv) > 1 else Path.home() / ".hermes"
    profile_home = Path(argv[2]).resolve() if len(argv) > 2 else hermes_home
    plugin = profile_home / "plugins" / PLUGIN_ID

    print(f"hermes_home : {hermes_home}")
    print(f"perfil      : {profile_home}")
    print(f"plugin      : {plugin}")
    print(f"interprete  : {sys.executable}")

    if not (plugin / "__init__.py").is_file():
        print("FALLO: el plugin no esta instalado en esa ruta")
        return 1

    # 1) Clave. El gateway la carga del .env de Hermes; aqui se lee igual.
    os.environ.setdefault("HERMES_HOME", str(hermes_home))
    clave = os.environ.get("HERMES_PRIVACY_GATEWAY_KEY", "")
    if not clave:
        env = _leer_env((hermes_home / ".env", profile_home / ".env"))
        clave = env.get("HERMES_PRIVACY_GATEWAY_KEY", "")
        if clave:
            os.environ["HERMES_PRIVACY_GATEWAY_KEY"] = clave
            print("  (clave leida del .env)")
    check(bool(clave), "HERMES_PRIVACY_GATEWAY_KEY disponible para el plugin",
          f"{len(clave)} chars")

    # 2) Configuracion, por la ruta real del plugin: plugins.entries.<id>.settings.
    try:
        import yaml  # type: ignore
    except Exception:
        print("FALLO: falta PyYAML en este interprete")
        return 1

    raiz_cfg = profile_home / "config.yaml"
    datos = {}
    if raiz_cfg.is_file():
        datos = yaml.safe_load(raiz_cfg.read_text(encoding="utf-8")) or {}
    entrada = entrada_plugin(datos)
    settings = entrada.get("settings") or {}
    cfg = {k: settings[k] for k in CLAVES if k in settings}
    print(f"  config resuelta: {cfg}")

    check(str(cfg.get("language", "es")) == "es",
          "language resuelve a 'es' por la ruta settings.", str(cfg.get("language")))
    sueltas = [k for k in CLAVES if k in entrada]
    check(not sueltas,
          "no hay claves de idioma fuera de 'settings:' (trampa de anidado)",
          f"fuera de settings: {sueltas}")

    # 3) Ampliacion espanola presente en el plugin instalado.
    check((plugin / "recognizers_es.py").is_file(),
          "recognizers_es.py instalado")
    privacy_py = plugin / "privacy.py"
    if privacy_py.is_file():
        cuerpo = privacy_py.read_text(encoding="utf-8", errors="replace")
        check("recognizers_es" in cuerpo, "privacy.py engancha los reconocedores es")
    else:
        check(False, "privacy.py presente")
    if (plugin / "nlp.yaml").is_file():
        nlp = (plugin / "nlp.yaml").read_text(encoding="utf-8", errors="replace")
        check("lang_code: es" in nlp and "es_core_news_lg" in nlp,
              "nlp.yaml apunta al modelo espanol")

    # 4) Carga y registro del plugin. Al importarlo asi, sus imports absolutos
    #    ('from privacy import ...') necesitan su directorio en sys.path.
    sys.path.insert(0, str(plugin))
    spec = importlib.util.spec_from_file_location(
        "pgw_plugin",
        plugin / "__init__.py",
        submodule_search_locations=[str(plugin)],
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pgw_plugin"] = mod
    spec.loader.exec_module(mod)  # type: ignore

    ctx = Ctx({"language": cfg.get("language", "es"),
               "score_threshold": float(cfg.get("score_threshold", 0.55) or 0.55)})
    mod.register(ctx)
    check({"llm_request", "tool_request"} <= set(ctx.mw), "middleware registrado")
    check({"transform_llm_output", "transform_tool_result"} <= set(ctx.hooks),
          "hooks registrados")

    # 5) Ida: nada de PII debe salir hacia el proveedor.
    req = {"messages": [{"role": "user", "content": TEXTO}]}
    resultado = ctx.mw["llm_request"](request=req)
    salida = resultado["request"]["messages"][0]["content"]
    print(f"\n  --- sale hacia el proveedor ---\n  {salida}\n")

    # El motor NLP es perezoso: si falla, se ve aqui. Mostrar la causa real
    # (el sintoma seria solo el block marker).
    err = getattr(mod, "_ENGINE_ERROR", None)
    if err is not None:
        print(f"  error del motor: {err!r}")
        traceback.print_exception(type(err), err, err.__traceback__)
    check(err is None, "el motor NLP arranca en 'es'", repr(err))
    check("PRIVACY_GATEWAY_BLOCKED" not in salida, "no hay block marker", salida[:80])

    for etiqueta, valor in [
        ("nombre", "Rafael Roa"),
        ("DNI", "12345678Z"),
        ("movil", "655123456"),
        ("email", "rafael.roa@example.com"),
        ("CIF", "B93133742"),
    ]:
        check(valor not in salida, f"{etiqueta} pseudonimizado", valor)
    check("125.000 euros" in salida, "los importes no se tocan")
    check("250 m2" in salida, "las superficies no se tocan")
    check("Malaga" in salida, "el toponimo no se toca")

    # 6) Vuelta: la respuesta del modelo se rehidrata al valor original.
    vuelta = ctx.hooks["transform_llm_output"](f"Confirmado: {salida}", request={}) or ""
    print(f"  --- vuelve al usuario ---\n  {vuelta}\n")
    for etiqueta, valor in [("nombre", "Rafael Roa"), ("DNI", "12345678Z"),
                            ("email", "rafael.roa@example.com"),
                            ("CIF", "B93133742")]:
        check(valor in vuelta, f"{etiqueta} restituido al usuario")

    # 7) Resultado de herramienta: tambien se sanea.
    tr = ctx.hooks["transform_tool_result"]("Contacto 655123456, DNI 12345678Z")
    check("655123456" not in tr and "12345678Z" not in tr,
          "resultado de herramienta saneado", tr)

    print()
    if fallos:
        print(f"RESULTADO: FALLO ({len(fallos)} comprobaciones)")
        for f in fallos:
            print(f"   - {f}")
        return 1
    print("RESULTADO: OK - el privacy-gateway funciona end-to-end en espanol")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        print("RESULTADO: FALLO (excepcion)")
        raise SystemExit(2)
