# Gestiona el estado de recogida del bloque alumnos.
# A diferencia del calendario (datos fijos) y las franjas (3 horarios fijos),
# aquí la lista es VARIABLE: crece alumno a alumno y termina cuando Rosa dice
# que ya están todos — o que no hay ninguno (lista vacía válida, igual que festivos).
#
# Estado:
#   alumnos   : lista de dicts {nombre, documento, tipo_curso}. Empieza vacía.
#   terminado : False hasta que Rosa señale el fin de la lista (hay alumnos O no hay).


def crear_estado():
    """
    Devuelve el estado inicial del bloque alumnos.
    La lista empieza vacía y terminado=False: Rosa aún no ha dicho cuántos hay.
    """
    return {
        "alumnos":   [],
        "terminado": False,
    }


def anadir_alumno(estado, nombre, documento, tipo_curso):
    """
    Añade un alumno a la lista. No valida el documento: esa responsabilidad
    recae en la conexión con el cerebro, antes de llegar aquí.

    tipo_curso debe ser "completo" o "ampliacion", pero este módulo no lo impone.
    Devuelve el estado modificado (el mismo dict, actualizado en su lugar).
    """
    estado["alumnos"].append({
        "nombre":     nombre,
        "documento":  documento,
        "tipo_curso": tipo_curso,
    })
    return estado


def marcar_terminado(estado):
    """
    Marca que Rosa ha terminado de añadir alumnos.
    Se llama tanto cuando dice "ya están todos" como cuando dice "no hay alumnos".
    En ambos casos la lista queda en el estado que tenga y terminado pasa a True.
    Devuelve el estado modificado.
    """
    estado["terminado"] = True
    return estado


def bloque_completo(estado):
    """
    True si Rosa ya señaló el fin de la lista (terminado==True), sea cual sea
    el número de alumnos — incluida lista vacía. False si aún no ha terminado.
    """
    return estado["terminado"]


def obtener_alumnos(estado):
    """Devuelve una copia de la lista de alumnos recogidos hasta ahora."""
    return list(estado["alumnos"])


def num_alumnos(estado):
    """Devuelve cuántos alumnos hay en la lista."""
    return len(estado["alumnos"])
