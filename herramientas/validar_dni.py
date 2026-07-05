# Valida DNI y NIE españoles usando el algoritmo del módulo 23.
# Sin LLM, sin conexiones externas: aritmética pura sobre la cadena del documento.

import re

# Tabla oficial de letras de control: el índice es el resto de dividir entre 23
_LETRAS = "TRWAGMYFPDXBNJZSQVHLCKE"

# Sustitución de la letra inicial del NIE por su valor numérico equivalente
_NIE_INICIAL = {"X": "0", "Y": "1", "Z": "2"}

# Patrones de formato válido (tras limpiar la entrada)
_PATRON_DNI = re.compile(r"^\d{8}[A-Z]$")
_PATRON_NIE = re.compile(r"^[XYZ]\d{7}[A-Z]$")


def _letra_correcta(numero_str):
    """Devuelve la letra de control que corresponde a un número dado como string."""
    return _LETRAS[int(numero_str) % 23]


def validar_documento(documento):
    """
    Valida un DNI o NIE español.

    Parámetro:
        documento: string con el DNI o NIE (admite espacios, guiones, mayúsculas o minúsculas).

    Devuelve un dict con:
        'valido'    : True si el documento es correcto, False en caso contrario
        'tipo'      : "DNI", "NIE" o None si el formato no es reconocible
        'documento' : el documento limpio (sin espacios ni guiones, en mayúsculas)
        'mensaje'   : texto en español explicando el resultado
    """
    # Paso 1: limpiar la entrada
    doc = documento.strip().replace(" ", "").replace("-", "").upper()

    # Paso 2: detectar tipo y validar formato antes de cualquier cálculo
    if _PATRON_DNI.match(doc):
        tipo = "DNI"
    elif _PATRON_NIE.match(doc):
        tipo = "NIE"
    else:
        # El formato no encaja con ningún documento conocido; explicamos por qué
        return _resultado_error_formato(doc)

    # Paso 3: extraer la parte numérica y la letra que trae el documento
    letra_documento = doc[-1]

    if tipo == "DNI":
        numero_str = doc[:8]
    else:
        # NIE: sustituimos la letra inicial (X→0, Y→1, Z→2) y concatenamos con los 7 dígitos
        numero_str = _NIE_INICIAL[doc[0]] + doc[1:8]

    # Paso 4: calcular la letra correcta con el módulo 23
    letra_correcta = _letra_correcta(numero_str)

    # Paso 5: comparar
    if letra_documento == letra_correcta:
        return {
            "valido": True,
            "tipo": tipo,
            "documento": doc,
            "mensaje": (
                f"El {tipo} {doc} es válido. "
                f"La letra de control '{letra_documento}' es correcta."
            ),
        }
    else:
        return {
            "valido": False,
            "tipo": tipo,
            "documento": doc,
            "mensaje": (
                f"El {tipo} {doc} no es válido. "
                f"La letra '{letra_documento}' no corresponde a este número: "
                f"la letra correcta sería '{letra_correcta}'."
            ),
        }


def _resultado_error_formato(doc):
    """
    Construye el resultado de error cuando el formato del documento no es válido.
    Se llama solo cuando el documento no encaja con ningún patrón conocido.
    """
    # Intentamos dar una pista específica sobre qué falla en el formato
    if len(doc) == 0:
        detalle = "El documento está vacío."
    elif len(doc) < 9:
        detalle = f"Faltan caracteres: tiene {len(doc)} pero debe tener 9."
    elif len(doc) > 9:
        detalle = f"Tiene demasiados caracteres: {len(doc)} en vez de 9."
    elif doc[0].isalpha() and doc[0] not in _NIE_INICIAL:
        detalle = (
            f"Si es un NIE, la primera letra debe ser X, Y o Z, no '{doc[0]}'."
        )
    elif not doc[-1].isalpha():
        detalle = "El último carácter debe ser una letra de control, no un número."
    elif not doc[:-1].isdigit() and doc[0] not in _NIE_INICIAL:
        detalle = "Los 8 caracteres centrales deben ser todos dígitos."
    else:
        detalle = "La estructura no corresponde a un DNI (8 dígitos + letra) ni a un NIE (X/Y/Z + 7 dígitos + letra)."

    return {
        "valido": False,
        "tipo": None,
        "documento": doc,
        "mensaje": f"Formato de documento incorrecto. {detalle}",
    }



