# Gestiona el estado de recogida de los tres datos del bloque franjas horarias.
# Este módulo no valida ni llama a ninguna herramienta: solo lleva la cuenta
# de qué horarios tiene Rosa ya confirmados y cuál toca pedir a continuación.
#
# Formato del valor de cada horario: {"inicio": "HH:MM", "fin": "HH:MM"}
# Se almacena como strings (igual que las fechas en recogida_calendario.py).
# La conversión a objetos time se hace en el motor, no aquí.

# Orden oficial en que se recogen los horarios.
# Lunes-jueves primero porque es el bloque más largo y el más representativo;
# viernes y sábado después porque tienen franjas distintas que pueden sorprender.
_ORDEN = ["horario_lun_jue", "horario_viernes", "horario_sabado"]


def crear_estado():
    """
    Devuelve el estado inicial del bloque franjas: los tres horarios pendientes.

    Estructura de cada entrada:
        'conseguido' : False hasta que Rosa confirme el horario
        'valor'      : None hasta que se guarde el dict {"inicio": "HH:MM", "fin": "HH:MM"}
    """
    return {
        nombre: {"conseguido": False, "valor": None}
        for nombre in _ORDEN
    }


def siguiente_dato_pendiente(estado):
    """
    Devuelve el nombre del primer horario que aún falta, siguiendo el orden oficial.
    Devuelve None si los tres horarios están ya conseguidos.
    """
    for nombre in _ORDEN:
        if not estado[nombre]["conseguido"]:
            return nombre
    return None


def marcar_conseguido(estado, nombre_dato, valor):
    """
    Marca un horario como conseguido y guarda su valor.

    No valida el valor: esa responsabilidad es de las herramientas de franjas
    que se llaman antes de llegar aquí.

    Devuelve el estado modificado (el mismo dict, actualizado en su lugar).
    """
    estado[nombre_dato]["conseguido"] = True
    estado[nombre_dato]["valor"] = valor
    return estado


def bloque_completo(estado):
    """Devuelve True si los tres horarios están conseguidos, False si falta alguno."""
    return all(estado[nombre]["conseguido"] for nombre in _ORDEN)
