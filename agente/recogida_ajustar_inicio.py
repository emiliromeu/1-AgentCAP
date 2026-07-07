# Gestiona el estado del bloque "ajustar_inicio": la red de seguridad que se
# activa (vía su condicion) solo cuando, tras calendario+franjas, no dan las
# horas para completar el curso (130h). Si dan las horas, este bloque nunca
# se activa y Rosa no lo ve.
#
# A diferencia de los demás bloques, este no recoge un dato nuevo del curso —
# ajusta datos que ya existen en calendario (fecha_inicio, festivos). Por eso
# su propio estado es minimalista: solo si ya quedó "resuelto" (las horas ya
# dan tras el ajuste) y cuántos intentos se han hecho, para poder cortar el
# bucle de reintentos si se alarga demasiado.

LIMITE_INTENTOS = 3


def crear_estado():
    return {
        "resuelto": False,
        "intentos": 0,
    }


def marcar_resuelto(estado):
    estado["resuelto"] = True
    return estado


def incrementar_intentos(estado):
    estado["intentos"] += 1
    return estado


def bloque_completo(estado):
    """True en cuanto el ajuste deja las horas suficientes (o se agotan los intentos)."""
    return estado["resuelto"]
