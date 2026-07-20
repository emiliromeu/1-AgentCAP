# Gestiona el estado de recogida del tipo de curso (primer bloque del pipeline).
#
# Dos ejes: un curso es la combinación de DOS ejes independientes:
#   tipo_formacio : "inicial" | "ampliacio" | "continu"
#   modalitat     : "mercancies" | "viatgers"
# FASE 3a: existen "inicial" (130h) y "continu" (35h, plantillas separadas).
# "ampliacio" como curso propio aún no tiene configuración — la tool lo
# rechaza con motivo claro (hoy la ampliación es un tipo de alumno dentro
# del inicial, no un curso).
#
# Estado:
#   tipo_formacio : str | None — "inicial" / "ampliacio" / "continu".
#   modalitat     : str | None — "mercancies" / "viatgers".
#   terminado     : bool       — True en cuanto se guarda el curso.

TIPUS_FORMACIO_VALIDS = {"inicial", "ampliacio", "continu"}
MODALITATS_VALIDES = {"mercancies", "viatgers"}

# La tool histórica del LLM habla en "mercancias"/"viatgers" (castellano/catalán
# mezclados, así nació) — se traduce aquí, en un único punto, al eje nuevo.
_MODALITAT_DES_DE_TOOL = {"mercancias": "mercancies", "viatgers": "viatgers"}

# Clave de configuración que consumen ensamblaje.py y generar_documento.py
# (_CONF_CURSO, _AMPLIACION_CURS, _NOM_CURS, _MATERIAS_CURS). Para el inicial
# es el string histórico de siempre (ningún consumidor viejo cambia); el
# continuo usa claves propias que apuntan a sus plantillas/catálogos separados.
# Este mapa es el ÚNICO sitio que decide qué configuración usa cada combinación.
_CLAU_CONFIG = {
    ("inicial", "mercancies"): "mercancias",
    ("inicial", "viatgers"):   "viatgers",
    ("continu", "mercancies"): "continu_mercancies",
    ("continu", "viatgers"):   "continu_viatgers",
}


def crear_estado():
    return {
        "tipo_formacio": None,
        "modalitat":     None,
        "terminado":     False,
    }


def guardar_tipo_curso(estado, tipo, tipo_formacio="inicial"):
    """
    Punto de entrada de la tool del LLM. `tipo` es la modalidad histórica
    ("mercancias"/"viatgers"); `tipo_formacio` es "inicial" o "continu"
    (por defecto "inicial", el comportamiento histórico).

    Solo guarda combinaciones CON configuración (las de _CLAU_CONFIG): así
    "ampliacio" — o cualquier valor futuro sin plantillas — se rechaza aquí
    y el flujo nunca llega a la generación con una clave inexistente.
    Devuelve True si se ha guardado; marca terminado automáticamente.
    """
    modalitat = _MODALITAT_DES_DE_TOOL.get(tipo)
    if modalitat is None or (tipo_formacio, modalitat) not in _CLAU_CONFIG:
        return False
    estado["tipo_formacio"] = tipo_formacio
    estado["modalitat"]     = modalitat
    estado["terminado"]     = True
    return True


def clau_curs(estado):
    """
    La clave de configuración del curso elegido, o None si la combinación no
    tiene configuración (aún). Es el ÚNICO puente entre los dos ejes y los
    diccionarios de configuración históricos.
    """
    return _CLAU_CONFIG.get((estado["tipo_formacio"], estado["modalitat"]))


def marcar_terminado(estado):
    estado["terminado"] = True
    return estado


def bloque_completo(estado):
    return estado["tipo_formacio"] is not None and estado["modalitat"] is not None
