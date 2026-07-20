# Lógica de fechas: parseo de texto a date, propuesta de fecha de inicio y validación de días.
# Python puro con datetime — sin LLM, sin internet.

from datetime import date, datetime, timedelta

# Formato esperado en toda entrada de texto de fecha
_FORMATO = "%d/%m/%Y"

# Nombres de los días de la semana en español (weekday() devuelve 0=lunes … 6=domingo)
_NOMBRES_DIA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def parsear_fecha(texto):
    """
    Convierte un string "dd/mm/aaaa" en un objeto date.

    Devuelve:
        {'valida': True,  'fecha': <date>}                        si el formato es correcto
        {'valida': False, 'fecha': None, 'mensaje': <str>}        si hay algún problema
    """
    if not isinstance(texto, str) or not texto.strip():
        return {
            "valida": False,
            "fecha": None,
            "mensaje": "No se ha introducido ninguna fecha.",
        }

    texto = texto.strip()

    # Comprobamos la estructura antes de llamar a strptime: tres partes separadas por '/'
    # y que las tres sean dígitos. Si no, el texto ni siquiera parece una fecha.
    partes = texto.split("/")
    if len(partes) != 3 or not all(p.isdigit() for p in partes):
        return {
            "valida": False,
            "fecha": None,
            "mensaje": (
                f"'{texto}' no tiene el formato correcto. "
                "Escribe la fecha como DD/MM/AAAA, por ejemplo: 15/06/2026."
            ),
        }

    # El formato es correcto; strptime valida ahora que la fecha sea real
    # (rechaza imposibles como 31/02/2026 o 00/13/2026)
    try:
        fecha = datetime.strptime(texto, _FORMATO).date()
    except ValueError:
        return {
            "valida": False,
            "fecha": None,
            "mensaje": (
                f"'{texto}' no es una fecha real "
                "(comprueba que el día y el mes existen en ese año)."
            ),
        }

    return {"valida": True, "fecha": fecha, "mensaje": None}


def proponer_fecha_inicio(dia_amarillo_texto, semanas_antes=6):
    """
    Propone una fecha de inicio restando semanas_antes semanas al día amarillo.

    Parámetro:
        dia_amarillo_texto : string "dd/mm/aaaa" con el último día permitido del plan
        semanas_antes      : número de semanas hacia atrás (por defecto 6)

    Devuelve un dict con:
        'valida'          : False si el texto no es una fecha válida
        'fecha_propuesta' : string "dd/mm/aaaa" con la fecha sugerida
        'ajustada'        : True si la fecha se movió porque caía en domingo
        'mensaje'         : texto en español para mostrar a la usuaria
    """
    resultado = parsear_fecha(dia_amarillo_texto)
    if not resultado["valida"]:
        # Propagamos el error de parseo
        return {"valida": False, "fecha_propuesta": None, "ajustada": False, "mensaje": resultado["mensaje"]}

    dia_amarillo = resultado["fecha"]
    fecha_propuesta = dia_amarillo - timedelta(weeks=semanas_antes)

    # Si la fecha cae en domingo la movemos al lunes siguiente (no al sábado anterior)
    # porque retroceder alargaría el período visible del curso sin ganar días lectivos.
    # No comprobamos festivos aquí: aún no se conocen en este punto de la conversación.
    ajustada = fecha_propuesta.weekday() == 6
    if ajustada:
        fecha_propuesta += timedelta(days=1)

    nombre_dia = _NOMBRES_DIA[fecha_propuesta.weekday()]

    if ajustada:
        mensaje = (
            f"La fecha calculada caía en domingo, así que propongo el lunes siguiente: "
            f"{fecha_propuesta.strftime(_FORMATO)} "
            f"({semanas_antes} semanas antes del día amarillo, ajustado). "
            "¿La aceptas o prefieres otra?"
        )
    else:
        mensaje = (
            f"Propongo empezar el {nombre_dia} "
            f"{fecha_propuesta.strftime(_FORMATO)} "
            f"({semanas_antes} semanas antes del día amarillo). "
            "¿La aceptas o prefieres otra?"
        )

    return {
        "valida": True,
        "fecha_propuesta": fecha_propuesta.strftime(_FORMATO),
        "ajustada": ajustada,
        "mensaje": mensaje,
    }


def es_dia_valido(fecha, dia_amarillo, festivos):
    """
    Comprueba si una fecha concreta es un día válido para incluir en el plan.

    Reglas (en orden):
        1. No puede ser domingo.
        2. No puede ser festivo.
        3. No puede ser posterior al día amarillo.

    Parámetros:
        fecha       : objeto date con el día a comprobar
        dia_amarillo: objeto date con el último día permitido
        festivos    : lista de objetos date con los días festivos a excluir

    Devuelve:
        {'valido': True,  'mensaje': <str>}   si el día es válido
        {'valido': False, 'mensaje': <str>}   si no lo es, explicando el motivo
    """
    # Comprobación 1: domingo (weekday == 6)
    if fecha.weekday() == 6:
        return {
            "valido": False,
            "mensaje": (
                f"El {fecha.strftime(_FORMATO)} es domingo y no se puede incluir en el plan."
            ),
        }

    # Comprobación 2: festivo
    if fecha in festivos:
        return {
            "valido": False,
            "mensaje": (
                f"El {fecha.strftime(_FORMATO)} es festivo y no se puede incluir en el plan."
            ),
        }

    # Comprobación 3: supera el día amarillo
    if fecha > dia_amarillo:
        return {
            "valido": False,
            "mensaje": (
                f"El {fecha.strftime(_FORMATO)} cae después del último día permitido "
                f"({dia_amarillo.strftime(_FORMATO)}). El plan no puede extenderse más allá."
            ),
        }

    nombre_dia = _NOMBRES_DIA[fecha.weekday()]
    return {
        "valido": True,
        "mensaje": (
            f"El {nombre_dia} {fecha.strftime(_FORMATO)} es un día válido para el plan."
        ),
    }


def validar_inicio_no_domingo(fecha_inicio_texto):
    """
    Comprueba que la fecha de inicio del curso no caiga en domingo (no hay clases ese día).

    Devuelve:
        {'coherente': True,  'mensaje': <str>}  si no es domingo
        {'coherente': False, 'mensaje': <str>}  si es domingo
    """
    inicio = parsear_fecha(fecha_inicio_texto)["fecha"]

    if inicio.weekday() == 6:
        return {
            "coherente": False,
            "mensaje": (
                "El curso no puede empezar en domingo, no hay clases. "
                "¿Qué otro día prefieres?"
            ),
        }

    return {
        "coherente": True,
        "mensaje": f"{inicio.strftime(_FORMATO)} no es domingo. Correcto.",
    }


def validar_inicio_antes_amarillo(fecha_inicio_texto, dia_amarillo_texto):
    """
    Comprueba que la fecha de inicio sea estrictamente anterior al día amarillo.
    El inicio igual al amarillo también es incoherente: el curso necesita al menos un día.

    Devuelve:
        {'coherente': True,  'mensaje': <str>}  si inicio < amarillo
        {'coherente': False, 'mensaje': <str>}  si inicio >= amarillo
    """
    inicio   = parsear_fecha(fecha_inicio_texto)["fecha"]
    amarillo = parsear_fecha(dia_amarillo_texto)["fecha"]

    if inicio < amarillo:
        return {
            "coherente": True,
            "mensaje": (
                f"La fecha de inicio ({inicio.strftime(_FORMATO)}) es anterior "
                f"al último día del curso ({amarillo.strftime(_FORMATO)}). Correcto."
            ),
        }

    return {
        "coherente": False,
        "mensaje": (
            f"La fecha de inicio ({inicio.strftime(_FORMATO)}) no puede ser igual "
            f"ni posterior al último día del curso ({amarillo.strftime(_FORMATO)}). "
            "El curso tiene que empezar antes de su último día. "
            "Revisa la fecha de inicio o el último día del plan."
        ),
    }


def validar_verde_despues_amarillo(dia_verde_texto, dia_amarillo_texto):
    """
    Comprueba que el día verde (examen) sea estrictamente posterior al día amarillo.
    El verde igual al amarillo también es incoherente: el examen debe ir después del fin del curso.

    Devuelve:
        {'coherente': True,  'mensaje': <str>}  si verde > amarillo
        {'coherente': False, 'mensaje': <str>}  si verde <= amarillo
    """
    verde    = parsear_fecha(dia_verde_texto)["fecha"]
    amarillo = parsear_fecha(dia_amarillo_texto)["fecha"]

    if verde > amarillo:
        return {
            "coherente": True,
            "mensaje": (
                f"El examen ({verde.strftime(_FORMATO)}) va después del último día "
                f"del curso ({amarillo.strftime(_FORMATO)}). Correcto."
            ),
        }

    return {
        "coherente": False,
        "mensaje": (
            f"El examen ({verde.strftime(_FORMATO)}) tiene que ir después del último "
            f"día del curso ({amarillo.strftime(_FORMATO)}). En el CAP el examen siempre "
            "es posterior al fin de la teoría. "
            "Revisa la fecha del examen o el último día del plan."
        ),
    }


def validar_limite_posterior_a_inicio(fecha_limite_texto, fecha_inicio_texto):
    """
    (CAP continuo) Comprueba que la fecha límite (último día permitido para acabar
    el curso) sea estrictamente posterior al día de inicio elegido por Rosa.
    Igual o anterior es incoherente: el curso necesita al menos un día.

    Devuelve:
        {'coherente': True,  'mensaje': <str>}  si límite > inicio
        {'coherente': False, 'mensaje': <str>}  si límite <= inicio
    """
    limite = parsear_fecha(fecha_limite_texto)["fecha"]
    inicio = parsear_fecha(fecha_inicio_texto)["fecha"]

    if limite > inicio:
        return {
            "coherente": True,
            "mensaje": (
                f"La fecha límite ({limite.strftime(_FORMATO)}) va después del día "
                f"de inicio ({inicio.strftime(_FORMATO)}). Correcto."
            ),
        }

    return {
        "coherente": False,
        "mensaje": (
            f"La fecha límite ({limite.strftime(_FORMATO)}) tiene que ir después del "
            f"día de inicio ({inicio.strftime(_FORMATO)}). El curso empieza el "
            f"{inicio.strftime(_FORMATO)}, así que la fecha límite debe ser posterior. "
            "Revisa la fecha límite o el día de inicio."
        ),
    }
