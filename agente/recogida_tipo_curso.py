# Gestiona el estado de recogida del tipo de curso (primer bloque del pipeline).
#
# FASE 1 (dos ejes): un curso es la combinación de DOS ejes independientes:
#   tipo_formacio : "inicial" | "ampliacio" | "continu"
#   modalitat     : "mercancies" | "viatgers"
# De momento solo existe en la práctica el tipo "inicial" (130h) — la tool que
# usa el LLM (guardar_tipo_curso, con los valores históricos "mercancias"/
# "viatgers") sigue igual y mapea a inicial+modalitat. "ampliacio" y "continu"
# se añadirán en fases siguientes; la estructura ya queda preparada.
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
# (_CONF_CURSO, _AMPLIACION_CURS, _NOM_CURS, _MATERIAS_CURS). En fase 1 solo
# el inicial tiene configuración: su clave es el string histórico de siempre,
# así NINGÚN consumidor cambia. Cuando existan ampliacio/continu, este mapa
# será el único sitio que decida qué configuración usa cada combinación.
_CLAU_CONFIG = {
    ("inicial", "mercancies"): "mercancias",
    ("inicial", "viatgers"):   "viatgers",
}


def crear_estado():
    return {
        "tipo_formacio": None,
        "modalitat":     None,
        "terminado":     False,
    }


def guardar_tipo_curso(estado, tipo):
    """
    Punto de entrada de la tool histórica del LLM ("mercancias"/"viatgers").
    Guarda inicial+modalitat si es válido. Devuelve True si se ha guardado.
    Marca terminado automáticamente al guardar.
    """
    modalitat = _MODALITAT_DES_DE_TOOL.get(tipo)
    if modalitat is None:
        return False
    estado["tipo_formacio"] = "inicial"
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
