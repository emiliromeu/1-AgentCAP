# Gestiona el estado de recogida del bloque orden de asignaturas.
# Este módulo no valida ni llama a ninguna herramienta: solo lleva la cuenta
# de si Rosa ya ha confirmado el orden de impartición o todavía está pendiente.
#
# A diferencia del calendario (4 datos) y las franjas (3 datos), aquí hay
# un único dato: el orden completo de las 16 asignaturas. Se propone entero
# y se confirma entero — no asignatura por asignatura.

_ORDEN = ["orden"]


def crear_estado():
    """
    Devuelve el estado del bloque orden YA COMPLETO.

    El orden de asignaturas lo dicta la plantilla pedagógica del sistema,
    no Rosa. Como generar_horario usa siempre la plantilla directamente
    (estado_orden no influye en la generación), marcamos este bloque como
    conseguido desde el inicio para que el flujo lo salte automáticamente
    sin preguntarle nada a Rosa.

    Si en el futuro se quiere activar el ajuste por parte de Rosa,
    basta con cambiar "conseguido": True → False.
    """
    return {
        nombre: {"conseguido": True, "valor": None}
        for nombre in _ORDEN
    }


def siguiente_dato_pendiente(estado):
    """
    Devuelve "orden" si el orden todavía no está conseguido, None si ya está confirmado.
    """
    for nombre in _ORDEN:
        if not estado[nombre]["conseguido"]:
            return nombre
    return None


def marcar_conseguido(estado, nombre_dato, valor):
    """
    Marca el orden como conseguido y guarda su valor.

    No valida el valor: esa responsabilidad es de la lógica del agente que
    comprueba los códigos antes de llegar aquí.

    El 'valor' es la lista de códigos de asignatura en orden de impartición,
    por ejemplo: ["1.1", "1.2", "1.3", ...].

    Devuelve el estado modificado (el mismo dict, actualizado en su lugar).
    """
    estado[nombre_dato]["conseguido"] = True
    estado[nombre_dato]["valor"] = valor
    return estado


def bloque_completo(estado):
    """Devuelve True si el orden está conseguido, False si todavía está pendiente."""
    return all(estado[nombre]["conseguido"] for nombre in _ORDEN)
