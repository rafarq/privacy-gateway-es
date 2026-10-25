"""Identificadores espanoles que Presidio no cubre de fabrica.

Presidio + `es_core_news_lg` ya detectan DNI (`EsNifRecognizer`), NIE
(`EsNieRecognizer`), email, IBAN, tarjeta, URLs, IPs y MACs, y el NER aporta
PERSON/LOCATION/ORG. Lo que queda fuera, y es PII corriente en obra industrial,
es:

  * NIF de empresa / CIF (p. ej. ``B93133742``) — el ``EsNifRecognizer`` de
    Presidio no lo reconoce.
  * Telefono espanol en cualquier formato (movil, fijo, con o sin ``+34`` y
    separadores): el ``PhoneRecognizer`` de Presidio necesita un formato que
    aqui no se da, asi que los deja pasar.
  * Matricula de vehiculo, referencia catastral, NUSS (numero de afiliacion a
    la Seguridad Social) y pasaporte.

Criterio: los que tienen digito de control se **validan** y un candidato que no
cuadra se descarta -- asi un valor inventado no se pseudonimiza y no se generan
falsos positivos. Los que no lo tienen (matricula, catastro, pasaporte) llevan
score mas bajo y contexto, para no dispararse con cualquier codigo alfanumerico.

Este modulo es una **ampliacion local** del plugin `privacy-gateway`
(terceros). Un update del plugin la sobrescribe: conservar copia fuera.
"""

from __future__ import annotations

import re

from presidio_analyzer import Pattern, PatternRecognizer

__all__ = ["es_recognizers"]

_LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"
_LETRAS_CONTROL_CIF = "JABCDEFGHI"


def dni_valido(valor: str) -> bool:
    valor = valor.strip().upper()
    return bool(re.fullmatch(r"\d{8}[A-Z]", valor)) and (
        _LETRAS_DNI[int(valor[:8]) % 23] == valor[8]
    )


def nie_valido(valor: str) -> bool:
    valor = valor.strip().upper()
    if not re.fullmatch(r"[XYZ]\d{7}[A-Z]", valor):
        return False
    prefijo = {"X": "0", "Y": "1", "Z": "2"}[valor[0]]
    return _LETRAS_DNI[int(prefijo + valor[1:8]) % 23] == valor[8]


def nif_cif_valido(valor: str) -> bool:
    """NIF de persona juridica (CIF) con digito de control, o DNI/NIE.

    Se acepta tambien el NIF de persona fisica porque el patron puede alcanzar
    un DNI pegado a texto; el validador decide.
    """
    valor = valor.strip().upper()
    if dni_valido(valor) or nie_valido(valor):
        return True
    if not re.fullmatch(r"[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]", valor):
        return False
    digitos, control = valor[1:8], valor[8]
    suma = 0
    for indice, digito in enumerate(digitos):
        producto = int(digito) * (2 if indice % 2 == 0 else 1)
        suma += producto // 10 + producto % 10
    digito_control = (10 - suma % 10) % 10
    letra_control = _LETRAS_CONTROL_CIF[digito_control]
    if valor[0] in "ABEH":
        return control == str(digito_control)
    if valor[0] in "KPQS":
        return control == letra_control
    return control in (str(digito_control), letra_control)


def telefono_es_valido(valor: str) -> bool:
    """Telefono espanol: 9 digitos empezando por 6, 7, 8 o 9.

    Descarta secuencias degeneradas (``600000000``, ``666666666``) que en la
    practica son importes, numeros de referencia o relleno.
    """
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) == 11 and digitos.startswith("34"):
        digitos = digitos[2:]
    if len(digitos) != 9 or digitos[0] not in "6789":
        return False
    if len(set(digitos)) < 3:
        return False
    return True


class _ValidatedRecognizer(PatternRecognizer):
    """`PatternRecognizer` que pasa cada candidato por un validador propio."""

    def __init__(
        self,
        *,
        entity: str,
        name: str,
        regex: str,
        supported_language: str,
        score: float,
        validator=None,
        context: list[str] | None = None,
    ) -> None:
        super().__init__(
            supported_language=supported_language,
            supported_entity=entity,
            name=name,
            patterns=[Pattern(name=name, regex=regex, score=score)],
            context=context,
        )
        self._validator = validator

    def analyze(self, text, entities, nlp_artifacts=None, regex_flags=None):
        resultados = super().analyze(text, entities, nlp_artifacts, regex_flags)
        if self._validator is None:
            return resultados
        return [
            resultado
            for resultado in resultados
            if self._validator(text[resultado.start : resultado.end])
        ]


# --------------------------------------------------------------------- patrones
# El NIF de empresa va primero y excluye el prefijo de DNI/NIE para no robar
# spans validos al EsNifRecognizer de Presidio.
_RE_NIF_EMPRESA = r"\b[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]\b"
_RE_TELEFONO = r"(?:(?:\+|00)34[\s.\-]?)?(?:[6789]\d{2}[\s.\-]?\d{3}[\s.\-]?\d{3})\b"
_RE_MATRICULA = r"\b\d{4}[\s\-]?[BCDFGHJKLMNPRSTVWXYZ]{3}\b"
_RE_CATASTRO = r"\b\d{7}\s?[A-Za-z]{2}\s?\d{4}\s?[A-Za-z0-9]{4,5}\s?[A-Za-z]{2}\b"
_RE_NUSS = r"\b\d{2}[\s/\-]?\d{7,8}[\s/\-]?\d{2}\b"
_RE_PASAPORTE = r"\b[A-Z]{3}\d{6}\b"


def es_recognizers(language: str = "es") -> list[PatternRecognizer]:
    """Recognizers de PII espanola para el idioma indicado."""
    return [
        # --- con digito de control: alta confianza ---
        _ValidatedRecognizer(
            entity="ES_NIF",
            name="EsNifEmpresaRecognizer",
            regex=_RE_NIF_EMPRESA,
            supported_language=language,
            score=0.85,
            validator=nif_cif_valido,
        ),
        _ValidatedRecognizer(
            entity="PHONE_NUMBER",
            name="EsTelefonoRecognizer",
            regex=_RE_TELEFONO,
            supported_language=language,
            score=0.8,
            validator=telefono_es_valido,
            context=["telefono", "movil", "fax", "contacto", "llamar"],
        ),
        # --- sin digito de control: patron estricto + contexto, score menor ---
        _ValidatedRecognizer(
            entity="ES_VEHICLE_ID",
            name="EsMatriculaRecognizer",
            regex=_RE_MATRICULA,
            supported_language=language,
            score=0.6,
            context=["matricula", "vehiculo", "coche", "furgoneta", "camion"],
        ),
        _ValidatedRecognizer(
            entity="ES_CATASTRO",
            name="EsReferenciaCatastralRecognizer",
            regex=_RE_CATASTRO,
            supported_language=language,
            score=0.6,
            context=["catastral", "catastro", "parcela", "referencia"],
        ),
        _ValidatedRecognizer(
            entity="ES_NUSS",
            name="EsNumeroSeguridadSocialRecognizer",
            regex=_RE_NUSS,
            supported_language=language,
            score=0.55,
            context=[
                "afiliacion",
                "seguridad social",
                "nuss",
                "cotizacion",
                "nomina",
            ],
        ),
        _ValidatedRecognizer(
            entity="ES_PASSPORT",
            name="EsPasaporteRecognizer",
            regex=_RE_PASAPORTE,
            supported_language=language,
            score=0.55,
            context=["pasaporte", "documento de viaje"],
        ),
    ]
