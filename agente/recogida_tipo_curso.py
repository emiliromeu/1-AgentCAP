# Gestiona el estado de recogida del tipo de curso (primer bloque del pipeline).
# Rosa elige entre "mercancias" (transport de mercaderies) o "viatgers" (transport de viatgers).
# En cuanto guarda el tipo, el bloque se considera completo.
#
# Estado:
#   tipo_curso : str | None  — "mercancias" o "viatgers", hasta que Rosa lo elija.
#   terminado  : bool        — True en cuanto se guarda el tipo.

_TIPOS_VALIDS = {"mercancias", "viatgers"}


def crear_estado():
    return {
        "tipo_curso": None,
        "terminado":  False,
    }


def guardar_tipo_curso(estado, tipo):
    """
    Guarda el tipo de curso si es válido. Devuelve True si se ha guardado, False si no.
    Marca terminado automáticamente al guardar.
    """
    if tipo not in _TIPOS_VALIDS:
        return False
    estado["tipo_curso"] = tipo
    estado["terminado"]  = True
    return True


def marcar_terminado(estado):
    estado["terminado"] = True
    return estado


def bloque_completo(estado):
    return estado["tipo_curso"] is not None
