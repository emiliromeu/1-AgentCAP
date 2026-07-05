# Gestiona el estado de recogida de los cuatro datos del bloque calendario.
# Este módulo no valida ni llama a ninguna herramienta: solo lleva la cuenta
# de qué datos tiene Rosa ya confirmados y cuál toca pedir a continuación.

# Orden oficial en que se recogen los datos. Es importante mantenerlo:
# el día amarillo y el día verde se necesitan antes de calcular el inicio,
# y los festivos son lo último porque pueden ser muchos o ninguno.
_ORDEN = ["dia_amarillo", "dia_verde", "fecha_inicio", "festivos"]


def crear_estado():
    """
    Devuelve el estado inicial del bloque calendario: los cuatro datos pendientes.

    Estructura de cada entrada:
        'conseguido' : False hasta que Rosa confirme el dato
        'valor'      : None hasta que se guarde el valor real
    """
    return {
        nombre: {"conseguido": False, "valor": None}
        for nombre in _ORDEN
    }


def siguiente_dato_pendiente(estado):
    """
    Devuelve el nombre del primer dato que aún falta, siguiendo el orden oficial.
    Devuelve None si los cuatro datos están ya conseguidos.
    """
    for nombre in _ORDEN:
        if not estado[nombre]["conseguido"]:
            return nombre
    return None


def marcar_conseguido(estado, nombre_dato, valor):
    """
    Marca un dato como conseguido y guarda su valor.

    No valida el valor: esa responsabilidad es de las herramientas de calendario
    que se llaman antes de llegar aquí.

    Devuelve el estado modificado (el mismo dict, actualizado en su lugar).
    """
    estado[nombre_dato]["conseguido"] = True
    estado[nombre_dato]["valor"] = valor
    return estado


def bloque_completo(estado):
    """Devuelve True si los cuatro datos están conseguidos, False si falta alguno."""
    return all(estado[nombre]["conseguido"] for nombre in _ORDEN)
