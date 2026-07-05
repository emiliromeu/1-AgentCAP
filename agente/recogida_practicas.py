# Gestiona el estado de recogida del bloque prácticas.
# Rosa solo aporta el PROFESOR que hará las prácticas.
# El sistema calcula y coloca las sesiones automáticamente con colocar_practicas
# (10h por alumno completo + 2.5h por alumno de ampliación).
#
# Estado:
#   profesor  : str | None  — nombre del profesor, hasta que Rosa lo indique.
#   terminado : bool        — True cuando Rosa ha confirmado el profesor.


def crear_estado():
    return {
        "profesor":  None,
        "terminado": False,
    }


def guardar_profesor(estado, profesor):
    """Guarda el nombre del profesor de prácticas."""
    estado["profesor"] = profesor
    return estado


def marcar_terminado(estado):
    estado["terminado"] = True
    return estado


def bloque_completo(estado):
    """True si el profesor está recogido y Rosa ha confirmado."""
    return estado["terminado"] and estado["profesor"] is not None
