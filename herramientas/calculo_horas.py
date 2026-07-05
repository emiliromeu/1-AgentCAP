# Valida que el total de horas del plan sume exactamente 130,0 y que cada asignatura cuadre con sus horas oficiales.

from decimal import Decimal, ROUND_HALF_UP
from datos.asignaturas import ASIGNATURAS

# Total de horas que debe sumar el plan según la normativa del CAP
TOTAL_OFICIAL = Decimal("130.0")

# Índice de asignaturas oficiales por código para búsqueda rápida
_ASIGNATURAS_POR_CODIGO = {a["codigo"]: a for a in ASIGNATURAS}


def _a_decimal(valor):
    """Convierte un número a Decimal de forma segura, pasando primero por str para evitar
    errores de representación de coma flotante (ej. 0.1 + 0.2 != 0.3 con float)."""
    return Decimal(str(valor))


def validar_total(asignaturas_asignadas):
    """
    Comprueba si la suma de horas de todas las asignaturas asignadas es exactamente 130,0.

    Parámetro:
        asignaturas_asignadas: lista de dicts con al menos la clave 'horas'
                               (puede ser int, float o Decimal).

    Devuelve un dict con:
        'cuadra'     : True si el total es exactamente 130,0
        'total'      : Decimal con la suma calculada
        'diferencia' : Decimal (positivo = sobran horas, negativo = faltan horas)
        'mensaje'    : texto en español para mostrar a la usuaria
    """
    # Sumamos usando Decimal para evitar errores de coma flotante
    total = sum(_a_decimal(a["horas"]) for a in asignaturas_asignadas)

    diferencia = total - TOTAL_OFICIAL
    cuadra = diferencia == Decimal("0")

    # Construimos el mensaje según el caso
    if cuadra:
        mensaje = (
            f"Las horas cuadran perfectamente: el plan suma exactamente {total} horas, "
            "que es lo que exige el CAP."
        )
    elif diferencia > 0:
        mensaje = (
            f"El plan tiene {total} horas en total, pero el CAP exige exactamente 130,0. "
            f"Sobran {diferencia} horas. Tienes que restar esas horas de alguna asignatura."
        )
    else:
        # diferencia es negativo, lo mostramos como positivo con abs()
        mensaje = (
            f"El plan tiene {total} horas en total, pero el CAP exige exactamente 130,0. "
            f"Faltan {abs(diferencia)} horas. Tienes que añadir esas horas en alguna asignatura."
        )

    return {
        "cuadra": cuadra,
        "total": total,
        "diferencia": diferencia,
        "mensaje": mensaje,
    }


def validar_asignaturas(asignaturas_asignadas):
    """
    Compara las horas asignadas a cada asignatura con sus horas oficiales del CAP.

    Parámetro:
        asignaturas_asignadas: lista de dicts con 'codigo' y 'horas'.

    Devuelve un dict con:
        'todas_cuadran' : True si todas las asignaturas tienen exactamente las horas correctas
        'errores'       : lista de dicts describiendo cada discrepancia encontrada
        'mensaje'       : texto en español para mostrar a la usuaria
    """
    errores = []

    for asignatura in asignaturas_asignadas:
        codigo = asignatura["codigo"]
        horas_asignadas = _a_decimal(asignatura["horas"])

        # Buscamos la asignatura en el catálogo oficial
        oficial = _ASIGNATURAS_POR_CODIGO.get(codigo)

        if oficial is None:
            # El código no existe en el catálogo oficial
            errores.append({
                "codigo": codigo,
                "nombre": asignatura.get("nombre", "Desconocida"),
                "horas_asignadas": horas_asignadas,
                "horas_oficiales": None,
                "diferencia": None,
                "descripcion": (
                    f"La asignatura con código '{codigo}' no existe en el plan oficial del CAP."
                ),
            })
            continue

        horas_oficiales = _a_decimal(oficial["horas"])
        diferencia = horas_asignadas - horas_oficiales

        # Solo registramos como error si las horas no coinciden exactamente
        if diferencia != Decimal("0"):
            if diferencia > 0:
                descripcion = (
                    f"'{oficial['nombre']}' tiene asignadas {horas_asignadas} horas, "
                    f"pero le corresponden {horas_oficiales}. Sobran {diferencia} horas."
                )
            else:
                descripcion = (
                    f"'{oficial['nombre']}' tiene asignadas {horas_asignadas} horas, "
                    f"pero le corresponden {horas_oficiales}. Faltan {abs(diferencia)} horas."
                )

            errores.append({
                "codigo": codigo,
                "nombre": oficial["nombre"],
                "horas_asignadas": horas_asignadas,
                "horas_oficiales": horas_oficiales,
                "diferencia": diferencia,
                "descripcion": descripcion,
            })

    todas_cuadran = len(errores) == 0

    # Construimos el mensaje resumen
    if todas_cuadran:
        mensaje = (
            "Todas las asignaturas tienen exactamente las horas que les corresponden según el CAP."
        )
    else:
        lineas = [
            f"Hay {len(errores)} asignatura(s) con horas incorrectas:",
            "",
        ]
        for e in errores:
            lineas.append(f"  • {e['descripcion']}")
        lineas.append("")
        lineas.append("Corrígelas antes de generar el PDF.")
        mensaje = "\n".join(lineas)

    return {
        "todas_cuadran": todas_cuadran,
        "errores": errores,
        "mensaje": mensaje,
    }
