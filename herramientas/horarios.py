# Validación de franjas horarias del día.
# Tema distinto de las fechas (calendario.py): aquí tratamos horas HH:MM,
# no días del mes. Python puro determinista, sin LLM.

from datetime import datetime

# Formato esperado en toda entrada de texto de hora
_FORMATO = "%H:%M"


def validar_horario(hora_inicio_texto, hora_fin_texto):
    """
    Valida que dos textos representen un horario de clase coherente.

    Comprobaciones en orden:
        1. Formato y validez: ambas horas deben ser HH:MM reales (00-23 h, 00-59 min).
           Si alguna falla, se devuelve error inmediatamente sin seguir.
        2. Coherencia: la hora de fin debe ser ESTRICTAMENTE posterior al inicio.
           Iguales tampoco es válido: "de 16:00 a 16:00" no es un horario.

    Parámetros:
        hora_inicio_texto : string "HH:MM" con la hora de inicio
        hora_fin_texto    : string "HH:MM" con la hora de fin

    Devuelve un dict:
        'valido'  : True si el horario es correcto, False si hay algún problema
        'inicio'  : objeto time con la hora de inicio (o None si es inválido)
        'fin'     : objeto time con la hora de fin (o None si es inválido)
        'mensaje' : texto en español explicando el resultado o el error

    Se devuelven objetos time (no strings) para que FRANJAS_SEMANALES pueda
    usarlos directamente sin necesidad de un segundo parseo.
    """
    # ── Paso 1: parsear y validar formato de cada hora ────────────────────────

    inicio = _parsear_hora(hora_inicio_texto)
    if inicio is None:
        return {
            "valido": False,
            "inicio": None,
            "fin": None,
            "mensaje": (
                f"'{hora_inicio_texto}' no es una hora válida. "
                "Escríbela en formato HH:MM, por ejemplo: 16:00 o 07:45. "
                "La hora debe estar entre 00 y 23, y los minutos entre 00 y 59."
            ),
        }

    fin = _parsear_hora(hora_fin_texto)
    if fin is None:
        return {
            "valido": False,
            "inicio": None,
            "fin": None,
            "mensaje": (
                f"'{hora_fin_texto}' no es una hora válida. "
                "Escríbela en formato HH:MM, por ejemplo: 20:15 o 14:15. "
                "La hora debe estar entre 00 y 23, y los minutos entre 00 y 59."
            ),
        }

    # ── Paso 2: comprobar que fin > inicio ────────────────────────────────────

    if fin <= inicio:
        if fin == inicio:
            detalle = (
                f"La hora de inicio y la de fin son iguales ({hora_inicio_texto}). "
                "Un horario necesita una duración mínima."
            )
        else:
            detalle = (
                f"La hora de fin ({hora_fin_texto}) es anterior a la de inicio "
                f"({hora_inicio_texto})."
            )
        return {
            "valido": False,
            "inicio": None,
            "fin": None,
            "mensaje": (
                f"{detalle} "
                "Revisa el horario: la hora de fin tiene que ser posterior a la de inicio."
            ),
        }

    return {
        "valido": True,
        "inicio": inicio,
        "fin": fin,
        "mensaje": (
            f"Horario válido: de {hora_inicio_texto} a {hora_fin_texto}."
        ),
    }


def _parsear_hora(texto):
    """
    Convierte "HH:MM" en un objeto time, o devuelve None si el formato es inválido.

    Comprueba primero la estructura (dos partes separadas por ':' con solo dígitos)
    para dar un error más claro que el que daría strptime solo.
    """
    if not isinstance(texto, str) or not texto.strip():
        return None

    texto = texto.strip()
    partes = texto.split(":")

    # Estructura básica: exactamente dos partes, ambas numéricas
    if len(partes) != 2 or not all(p.isdigit() for p in partes):
        return None

    try:
        return datetime.strptime(texto, _FORMATO).time()
    except ValueError:
        # strptime rechaza horas > 23 o minutos > 59
        return None
