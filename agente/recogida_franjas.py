# Gestiona el estado de recogida del bloque franjas horarias: la opción de
# días de la semana (solo se pregunta en el CAP continuo) y los tres horarios.
# Este módulo no valida ni llama a ninguna herramienta: solo lleva la cuenta
# de qué datos tiene Rosa ya confirmados y cuál toca pedir a continuación.
#
# Formato del valor de cada horario: {"inicio": "HH:MM", "fin": "HH:MM"}
# Se almacena como strings (igual que las fechas en recogida_calendario.py).
# La conversión a objetos time se hace en el motor, no aquí.
#
# FASE 3b — días de la semana: el estado incluye "dias_semana"
# ({"opcion": 1-6, "dias": [weekdays]}). En el inicial se fija solo con la
# opción 5 (lunes-sábado, el comportamiento histórico) al guardarse el tipo
# de curso; en el continuo Rosa elige una de las 6 opciones y los horarios
# de los grupos de días EXCLUIDOS quedan conseguidos con valor None (el
# motor traduce valor None a "día sin clase", como el domingo).

# Orden oficial en que se recogen los horarios.
# Lunes-jueves primero porque es el bloque más largo y el más representativo;
# viernes y sábado después porque tienen franjas distintas que pueden sorprender.
_ORDEN = ["horario_lun_jue", "horario_viernes", "horario_sabado"]

# Las 6 opciones de días del CAP continuo (Rosa elige UNA).
OPCIONES_DIAS = {
    1: {"dias": [0, 1, 2, 3],       "etiqueta": "De lunes a jueves"},
    2: {"dias": [0, 1, 2, 3, 4],    "etiqueta": "De lunes a viernes"},
    3: {"dias": [0, 1, 2, 3, 5],    "etiqueta": "De lunes a jueves y sábado"},
    4: {"dias": [4, 5],             "etiqueta": "Viernes y sábados"},
    5: {"dias": [0, 1, 2, 3, 4, 5], "etiqueta": "De lunes a sábado"},
    6: {"dias": [5],                "etiqueta": "Solo sábados"},
}

# Qué días de la semana cubre cada grupo de horario. Ninguna de las 6
# opciones parte el grupo lunes-jueves: un grupo está activo si CUALQUIERA
# de sus días está en la opción, e inactivo si ninguno lo está.
_GRUPOS_DIAS = {
    "horario_lun_jue": {0, 1, 2, 3},
    "horario_viernes": {4},
    "horario_sabado":  {5},
}


def crear_estado():
    """
    Devuelve el estado inicial del bloque franjas: opción de días y los tres
    horarios, todos pendientes.

    Estructura de cada entrada:
        'conseguido' : False hasta que Rosa confirme el dato
        'valor'      : None hasta que se guarde
                       (horarios: {"inicio": "HH:MM", "fin": "HH:MM"};
                        dias_semana: {"opcion": int, "dias": [int]})
    """
    estado = {
        nombre: {"conseguido": False, "valor": None}
        for nombre in _ORDEN
    }
    estado["dias_semana"] = {"conseguido": False, "valor": None}
    return estado


def elegir_dias(estado, opcion):
    """
    Guarda la opción de días elegida (1-6) y ajusta los tres horarios:
      - grupos SIN días activos → conseguido con valor None (no se preguntan
        y el motor los tratará como días sin clase);
      - grupos CON días activos que estaban desactivados por una elección
        anterior → vuelven a pendiente (permite corregir la opción).
    Devuelve True si la opción es válida y se ha guardado.
    """
    conf = OPCIONES_DIAS.get(opcion)
    if conf is None:
        return False
    dias = set(conf["dias"])
    estado["dias_semana"] = {
        "conseguido": True,
        "valor": {"opcion": opcion, "dias": conf["dias"]},
    }
    for nombre, grupo in _GRUPOS_DIAS.items():
        activo = bool(grupo & dias)
        if not activo:
            estado[nombre] = {"conseguido": True, "valor": None}
        elif estado[nombre]["conseguido"] and estado[nombre]["valor"] is None:
            # Estaba excluido por una opción anterior: vuelve a pendiente
            estado[nombre] = {"conseguido": False, "valor": None}
    return True


def fijar_dias_todos(estado):
    """
    Fija los días al comportamiento histórico (opción 5, lunes a sábado) SIN
    pasar por el menú — es lo que hace el inicial (y la ampliación en el
    futuro), donde los días no se eligen.
    """
    elegir_dias(estado, 5)
    return estado


def dias_activos(estado):
    """Lista de weekdays con clase según la opción guardada (None si no hay opción)."""
    ds = estado.get("dias_semana", {})
    if not ds.get("conseguido") or not ds.get("valor"):
        return None
    return list(ds["valor"]["dias"])


def grupo_activo(estado, nombre):
    """False si el grupo de horario quedó excluido por la opción de días."""
    return not (estado[nombre]["conseguido"] and estado[nombre]["valor"] is None)


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
    """
    True si la opción de días y los tres horarios están conseguidos.

    Estados antiguos (sesiones guardadas antes de FASE 3b, o los de ejemplo)
    no tienen "dias_semana": se tratan como conseguido (comportamiento
    histórico de días fijos) — la migración de persistencia lo añade al cargar.
    """
    dias_ok = estado.get("dias_semana", {"conseguido": True})["conseguido"]
    return dias_ok and all(estado[nombre]["conseguido"] for nombre in _ORDEN)
