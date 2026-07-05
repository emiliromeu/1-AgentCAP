"""
Estados de ejemplo para las seis bloques del agente CAP (mercancías).

Usa los mismos formatos que producen los directores en agente/recogida_*.py,
para poder probar el motor de horario, la lógica de profesores y el PDF
sin necesidad de conversar con el agente.

Uso:
    from datos_ejemplo import estados_ejemplo
    estados = estados_ejemplo()
    estado_calendario = estados["calendario"]
    ...

O importar los seis directamente:
    from datos_ejemplo import (
        ESTADO_CALENDARIO, ESTADO_FRANJAS, ESTADO_ORDEN,
        ESTADO_ALUMNOS, ESTADO_PROFESORES, ESTADO_PRACTICAS,
    )
"""

from datos.orden_asignaturas import ORDEN_HABITUAL_MERCANCIAS


# ── 1. CALENDARIO ─────────────────────────────────────────────────────────────
# Estructura: dict de cuatro entradas {"conseguido": bool, "valor": ...}
# Festivos: lista de strings "DD/MM/AAAA"

ESTADO_CALENDARIO = {
    "dia_amarillo": {"conseguido": True,  "valor": "17/04/2026"},
    "dia_verde":    {"conseguido": True,  "valor": "30/04/2026"},
    "fecha_inicio": {"conseguido": True,  "valor": "02/03/2026"},
    "festivos":     {"conseguido": True,  "valor": []},
}


# ── 2. FRANJAS HORARIAS ───────────────────────────────────────────────────────
# Estructura: dict de tres entradas {"conseguido": bool, "valor": {"inicio": "HH:MM", "fin": "HH:MM"}}

ESTADO_FRANJAS = {
    "horario_lun_jue": {"conseguido": True, "valor": {"inicio": "18:00", "fin": "21:15"}},
    "horario_viernes": {"conseguido": True, "valor": {"inicio": "16:00", "fin": "20:15"}},
    "horario_sabado":  {"conseguido": True, "valor": {"inicio": "07:45", "fin": "14:15"}},
}


# ── 3. ORDEN DE ASIGNATURAS ───────────────────────────────────────────────────
# Estructura: {"orden": {"conseguido": bool, "valor": [lista de códigos]}}

ESTADO_ORDEN = {
    "orden": {"conseguido": True, "valor": list(ORDEN_HABITUAL_MERCANCIAS)},
}


# ── 4. ALUMNOS ────────────────────────────────────────────────────────────────
# Estructura: {"alumnos": [lista de dicts], "terminado": bool}
# Cada alumno: {"nombre": str, "documento": str, "tipo_curso": "completo"|"ampliacion"}
# 5 alumnos de curso completo + 1 de ampliación

ESTADO_ALUMNOS = {
    "alumnos": [
        {"nombre": "Mohamed Amakran",     "documento": "51808749F", "tipo_curso": "completo"},
        {"nombre": "Ana Serrano Vidal",   "documento": "38476512P", "tipo_curso": "completo"},
        {"nombre": "Carlos Romero Puig",  "documento": "47293018M", "tipo_curso": "completo"},
        {"nombre": "Laura Fernández Bajo","documento": "29381047G", "tipo_curso": "completo"},
        {"nombre": "Jordi Puig Palau",    "documento": "52038471R", "tipo_curso": "completo"},
        {"nombre": "Fatima Hadj Benali",  "documento": "X1234567L", "tipo_curso": "ampliacion"},
    ],
    "terminado": True,
}


# ── 5. PROFESORES ─────────────────────────────────────────────────────────────
# Estructura: {"profesor_general": str, "excepciones": [lista de dicts], "terminado": bool}
# Cada excepción: {"fecha": "DD/MM/AAAA", "profesor": str}

ESTADO_PROFESORES = {
    "profesor_general": "Marta Quero",
    "excepciones": [
        {"fecha": "10/03/2026", "profesor": "Pedro Pastor"},
        {"fecha": "11/03/2026", "profesor": "Pedro Pastor"},
    ],
    "terminado": True,
}


# ── 6. PRÁCTICAS ──────────────────────────────────────────────────────────────
# Estructura: {"profesor": str, "terminado": bool}
# Rosa solo indica el profesor; el sistema calcula las sesiones con colocar_practicas.

ESTADO_PRACTICAS = {
    "profesor":  "Pere Romeu",
    "terminado": True,
}


# ── ACCESO AGRUPADO ───────────────────────────────────────────────────────────

def estados_ejemplo():
    """
    Devuelve los seis estados listos para pasar al motor o al cerebro.
    Cada estado es una copia nueva para evitar mutaciones entre pruebas.
    """
    import copy
    return {
        "calendario": copy.deepcopy(ESTADO_CALENDARIO),
        "franjas":    copy.deepcopy(ESTADO_FRANJAS),
        "orden":      copy.deepcopy(ESTADO_ORDEN),
        "alumnos":    copy.deepcopy(ESTADO_ALUMNOS),
        "profesores": copy.deepcopy(ESTADO_PROFESORES),
        "practicas":  copy.deepcopy(ESTADO_PRACTICAS),
    }
