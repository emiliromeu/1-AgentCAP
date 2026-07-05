# Gestiona l'estat de recollida de la Prova de Foc del CAP de mercaderies.
# Rosa aporta: data del dissabte, hora d'inici i opcionalment el proveïdor.
# El proveïdor per defecte és FAST PARCMOTOR.
#
# Estat:
#   fecha      : date | None  — data del dissabte de la PF
#   hora_inicio: time | None  — hora d'inici de la sessió de 2h
#   proveedor  : str           — proveïdor extern (default FAST PARCMOTOR)
#   terminado  : bool          — True quan Rosa ha confirmat les dades

from herramientas.motor_prueba_fuego import PROVEIDOR_DEFAULT


def crear_estado():
    return {
        "fecha":       None,
        "hora_inicio": None,
        "proveedor":   PROVEIDOR_DEFAULT,
        "terminado":   False,
    }


def guardar_prueba_fuego(estado, fecha, hora_inicio, proveedor=None):
    """
    Guarda la data i hora de la Prova de Foc.
    Valida que la data sigui dissabte (weekday == 5).
    Si proveedor és None, manté el valor per defecte (FAST PARCMOTOR).
    Retorna True si s'ha guardat, False si la data no és dissabte.
    """
    if fecha.weekday() != 5:
        return False
    estado["fecha"]       = fecha
    estado["hora_inicio"] = hora_inicio
    if proveedor is not None:
        estado["proveedor"] = proveedor
    return True


def marcar_terminado(estado):
    estado["terminado"] = True
    return estado


def bloque_completo(estado):
    return estado["fecha"] is not None and estado["hora_inicio"] is not None
