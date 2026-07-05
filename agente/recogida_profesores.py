# Gestiona el estado de recogida del bloque profesores.
# Recoge dos cosas:
#   1. El profesor general del curso (un único nombre, obligatorio).
#   2. Una lista de excepciones por día: fechas donde imparte otro profesor.
#      La lista puede estar vacía (todo el curso lo da el profesor general).
#
# El profesor es una etiqueta informativa; no afecta a la colocación del horario.
# La validación de fechas de excepción se hace en la conexión con el cerebro,
# no aquí: este módulo solo almacena lo que recibe.
#
# Estado:
#   profesor_general : None hasta que Rosa lo dé; luego el nombre (string).
#   excepciones      : lista de dicts {fecha, profesor}. Empieza vacía.
#   terminado        : False hasta que Rosa señale que no hay más excepciones.


def crear_estado():
    """
    Devuelve el estado inicial del bloque profesores.
    El profesor general está pendiente, no hay excepciones y Rosa aún no ha terminado.
    """
    return {
        "profesor_general": None,
        "excepciones":      [],
        "terminado":        False,
    }


def marcar_profesor_general(estado, nombre):
    """
    Guarda el nombre del profesor general del curso.
    No valida el nombre: esa responsabilidad recae en quien llame a esta función.
    Devuelve el estado modificado (el mismo dict, actualizado en su lugar).
    """
    estado["profesor_general"] = nombre
    return estado


def anadir_excepcion(estado, fecha_texto, nombre_profesor):
    """
    Añade una excepción por día: una fecha concreta donde imparte otro profesor.
    fecha_texto es un string "DD/MM/AAAA" — la validación va en la conexión con el cerebro.
    Devuelve el estado modificado.
    """
    estado["excepciones"].append({
        "fecha":    fecha_texto,
        "profesor": nombre_profesor,
    })
    return estado


def marcar_terminado(estado):
    """
    Marca que Rosa ha terminado de dar excepciones (o que no hay ninguna).
    Se llama tanto cuando Rosa dice "ya están todas" como cuando dice "no hay excepciones".
    Devuelve el estado modificado.
    """
    estado["terminado"] = True
    return estado


def bloque_completo(estado):
    """
    True cuando el profesor general está dado Y Rosa ha señalado el fin de las excepciones.
    Hace falta el profesor general (no puede ser None); lista vacía de excepciones es válida.
    """
    return estado["profesor_general"] is not None and estado["terminado"]


def obtener_profesor_general(estado):
    """Devuelve el nombre del profesor general, o None si aún no se ha dado."""
    return estado["profesor_general"]


def obtener_excepciones(estado):
    """Devuelve una copia de la lista de excepciones recogidas hasta ahora."""
    return list(estado["excepciones"])


def num_excepciones(estado):
    """Devuelve cuántas excepciones hay en la lista."""
    return len(estado["excepciones"])
