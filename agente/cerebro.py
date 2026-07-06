# Bucle principal del agente: recibe el mensaje de la usuaria, decide qué herramienta llamar y devuelve la respuesta.

import os
import re
import json
from decimal import Decimal
from datetime import date, time, datetime
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

_BASE = Path(__file__).resolve().parent.parent  # agente/ → arrel del projecte

from agente.system_prompt import SYSTEM_PROMPT
from agente.recogida_calendario import (
    crear_estado as crear_estado_calendario,
    siguiente_dato_pendiente,
    marcar_conseguido as marcar_conseguido_calendario,
    bloque_completo as bloque_completo_calendario,
)
from agente.recogida_franjas import (
    crear_estado as crear_estado_franjas,
    siguiente_dato_pendiente as siguiente_pendiente_franjas,
    marcar_conseguido as marcar_conseguido_franjas,
    bloque_completo as bloque_completo_franjas,
)
from agente.recogida_orden import (
    crear_estado as crear_estado_orden,
    marcar_conseguido as marcar_conseguido_orden,
    bloque_completo as bloque_completo_orden,
)
from agente.recogida_alumnos import (
    crear_estado as crear_estado_alumnos,
    anadir_alumno as anadir_alumno_alumnos,
    marcar_terminado as marcar_terminado_alumnos,
    bloque_completo as bloque_completo_alumnos,
)
from agente.recogida_profesores import (
    crear_estado as crear_estado_profesores,
    marcar_profesor_general as marcar_profesor_general_profesores,
    anadir_excepcion as anadir_excepcion_profesores,
    marcar_terminado as marcar_terminado_profesores,
    bloque_completo as bloque_completo_profesores,
)
from agente.recogida_practicas import (
    crear_estado as crear_estado_practicas,
    guardar_profesor as guardar_profesor_practicas,
    marcar_terminado as marcar_terminado_practicas,
    bloque_completo as bloque_completo_practicas,
)
from agente.recogida_tipo_curso import (
    crear_estado as crear_estado_tipo_curso,
    guardar_tipo_curso as guardar_tipo_curso_tc,
    bloque_completo as bloque_completo_tipo_curso,
)
from agente.recogida_prueba_fuego import (
    crear_estado as crear_estado_prueba_fuego,
    marcar_terminado as marcar_terminado_prueba_fuego,
    bloque_completo as bloque_completo_prueba_fuego,
)
from herramientas.motor_prueba_fuego import crear_prueba_fuego
from datos.orden_asignaturas import ORDEN_HABITUAL_MERCANCIAS
from ensamblaje import generar_horario, aplicar_profesores
from generar_documento import generar_document
from herramientas.horarios import validar_horario
from herramientas.validar_dni import validar_documento
from herramientas.calendario import (
    parsear_fecha,
    proponer_fecha_inicio,
    validar_inicio_antes_amarillo,
    validar_verde_despues_amarillo,
)

load_dotenv()


class _DecimalEncoder(json.JSONEncoder):
    """Convierte Decimal, date y time a str para serializar resultados de herramientas."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, date):
            return obj.strftime("%d/%m/%Y")
        if isinstance(obj, time):
            return obj.strftime("%H:%M")
        return super().default(obj)


# Patrón para extraer horas HH:MM (o H:MM) de un string de franja horaria,
# ignorando palabras de relleno como "de", "a", "hasta" o separadores sueltos.
_PATRON_HORA = re.compile(r"\d{1,2}:\d{2}")


HERRAMIENTA_GUARDAR_TIPO_CURSO = {
    "name": "guardar_tipo_curso",
    "description": (
        "Guarda el tipo de curso CAP que Rosa ha elegido. "
        "Llámala cuando Rosa haya indicado claramente si el curso es de mercancías o de viajeros. "
        "Valores válidos: 'mercancias' (transport de mercaderies) o 'viatgers' (transport de viatgers)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tipo_curso": {
                "type": "string",
                "enum": ["mercancias", "viatgers"],
                "description": "Tipo de curso: 'mercancias' o 'viatgers'."
            }
        },
        "required": ["tipo_curso"]
    }
}


# Lista de herramientas que el LLM puede invocar.
# El LLM nunca ejecuta código: solo devuelve el nombre y los argumentos.
# Somos nosotros quienes llamamos a la función real en _ejecutar_herramienta().


HERRAMIENTA_VALIDAR_FECHA = {
    "name": "validar_fecha",
    "description": (
        "Valida que una fecha escrita por Rosa tenga el formato correcto (DD/MM/AAAA) "
        "y que sea una fecha real. Úsala siempre que Rosa indique una fecha: "
        "día amarillo, día verde o cualquier otra."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fecha": {
                "type": "string",
                "description": "Fecha en formato DD/MM/AAAA, por ejemplo: '30/11/2026'."
            }
        },
        "required": ["fecha"]
    }
}

HERRAMIENTA_PROPONER_INICIO = {
    "name": "proponer_inicio",
    "description": (
        "Calcula y propone una fecha de inicio del curso restando 6 semanas al día amarillo. "
        "Si la fecha calculada cae en domingo, la ajusta al lunes siguiente. "
        "Úsala cuando Rosa haya confirmado el día amarillo y quiera saber cuándo empezar."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "dia_amarillo": {
                "type": "string",
                "description": "Último día permitido del plan, en formato DD/MM/AAAA."
            }
        },
        "required": ["dia_amarillo"]
    }
}


HERRAMIENTA_VALIDAR_HORARIO = {
    "name": "validar_horario",
    "description": (
        "Valida que un horario de clase tenga formato correcto (HH:MM) y que la hora de fin "
        "sea posterior a la de inicio. Úsala siempre que Rosa indique o confirme un horario."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "hora_inicio": {
                "type": "string",
                "description": "Hora de inicio en formato HH:MM, por ejemplo: '16:00'."
            },
            "hora_fin": {
                "type": "string",
                "description": "Hora de fin en formato HH:MM, por ejemplo: '20:15'."
            }
        },
        "required": ["hora_inicio", "hora_fin"]
    }
}


HERRAMIENTA_CONFIRMAR_DATO = {
    "name": "confirmar_dato",
    "description": (
        "Llama a esta herramienta SOLO cuando Rosa haya dicho explícitamente que sí a un dato "
        "que le has mostrado para confirmar. Guarda el valor en el estado de recogida. "
        "No la llames antes de que Rosa confirme: primero muéstrale el dato y espera su respuesta."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nombre_dato": {
                "type": "string",
                "description": "Nombre del dato confirmado por Rosa.",
                "enum": [
                    "dia_amarillo", "dia_verde", "fecha_inicio", "festivos",
                    "horario_lun_jue", "horario_viernes", "horario_sabado",
                    "orden",
                ]
            },
            "valor": {
                "description": (
                    "Valor confirmado. "
                    "Fechas sueltas (dia_amarillo, dia_verde, fecha_inicio): string DD/MM/AAAA. "
                    "Festivos: array de strings DD/MM/AAAA, o [] si no hay ninguno. "
                    "Horarios: objeto {\"inicio\": \"HH:MM\", \"fin\": \"HH:MM\"}."
                ),
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                    {
                        "type": "object",
                        "properties": {
                            "inicio": {"type": "string", "description": "Hora de inicio HH:MM"},
                            "fin":    {"type": "string", "description": "Hora de fin HH:MM"}
                        },
                        "required": ["inicio", "fin"]
                    }
                ]
            }
        },
        "required": ["nombre_dato", "valor"]
    }
}

HERRAMIENTA_VALIDAR_DNI = {
    "name": "validar_dni",
    "description": (
        "Valida que un documento de identidad (DNI o NIE español) sea correcto. "
        "Úsala siempre que Rosa indique el documento de un alumno, antes de añadirlo."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "documento": {
                "type": "string",
                "description": "DNI o NIE a validar, p.ej. '12345678A' o 'X1234567L'."
            }
        },
        "required": ["documento"]
    }
}

HERRAMIENTA_ANADIR_ALUMNO = {
    "name": "anadir_alumno",
    "description": (
        "Añade un alumno a la lista del curso. Llámala cuando Rosa haya dado el nombre, "
        "el documento y el tipo de curso de un alumno y haya confirmado los datos. "
        "El despacho revalida el documento internamente: si no es válido, no lo añade."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nombre":     {"type": "string", "description": "Nombre completo del alumno."},
            "documento":  {"type": "string", "description": "DNI o NIE del alumno."},
            "tipo_curso": {
                "type": "string",
                "enum": ["completo", "ampliacion"],
                "description": "'completo' para curso completo, 'ampliacion' para ampliación."
            }
        },
        "required": ["nombre", "documento", "tipo_curso"]
    }
}

HERRAMIENTA_TERMINAR_ALUMNOS = {
    "name": "terminar_alumnos",
    "description": (
        "Marca que Rosa ha terminado de añadir alumnos. Llámala cuando Rosa diga que ya "
        "están todos, o que no hay ningún alumno apuntado. La lista puede estar vacía: "
        "eso también es válido."
    ),
    "input_schema": {
        "type": "object",
        "properties": {}
    }
}

HERRAMIENTA_MARCAR_PROFESOR_GENERAL = {
    "name": "marcar_profesor_general",
    "description": (
        "Guarda el nombre del profesor general del curso (el que imparte la mayoría de clases). "
        "Llámala cuando Rosa indique quién es el profesor principal y lo confirme."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nombre": {
                "type": "string",
                "description": "Nombre completo del profesor general del curso."
            }
        },
        "required": ["nombre"]
    }
}

HERRAMIENTA_ANADIR_EXCEPCION_PROFESOR = {
    "name": "anadir_excepcion_profesor",
    "description": (
        "Añade una excepción: una fecha concreta donde imparte un profesor distinto al general. "
        "Llámala cuando Rosa dé una fecha y el nombre del profesor de ese día. "
        "El despacho valida la fecha antes de añadirla; si no es válida, no se añade."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fecha": {
                "type": "string",
                "description": "Fecha de la excepción en formato DD/MM/AAAA."
            },
            "profesor": {
                "type": "string",
                "description": "Nombre del profesor que imparte ese día."
            }
        },
        "required": ["fecha", "profesor"]
    }
}

HERRAMIENTA_TERMINAR_PROFESORES = {
    "name": "terminar_profesores",
    "description": (
        "Marca que Rosa ha terminado de dar excepciones de profesor. Llámala cuando Rosa diga "
        "que ya están todas las excepciones, o que no hay ninguna. La lista vacía es válida."
    ),
    "input_schema": {
        "type": "object",
        "properties": {}
    }
}

HERRAMIENTA_GUARDAR_PROFESOR_PRACTICAS = {
    "name": "guardar_profesor_practicas",
    "description": (
        "Guarda el nombre del profesor que impartirá las prácticas del curso. "
        "Llámala cuando Rosa haya indicado el profesor y haya confirmado el nombre. "
        "El sistema calculará y colocará automáticamente las sesiones de prácticas."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "profesor": {
                "type": "string",
                "description": "Nombre completo del profesor que impartirá las prácticas."
            }
        },
        "required": ["profesor"]
    }
}

HERRAMIENTA_TERMINAR_PRACTICAS = {
    "name": "terminar_practicas",
    "description": (
        "Marca que Rosa ha terminado de añadir sesiones de prácticas. Llámala cuando Rosa diga "
        "que ya están todas las sesiones, o que no hay prácticas. La lista vacía es válida."
    ),
    "input_schema": {
        "type": "object",
        "properties": {}
    }
}

HERRAMIENTA_GUARDAR_PRUEBA_FUEGO = {
    "name": "guardar_prueba_fuego",
    "description": (
        "Guarda els dades de la Prova de Foc (sessió de 2h de MM.PP amb proveïdor extern): "
        "la data del dissabte i l'hora d'inici. Es poden guardar per separat: primer la data "
        "(quan Rosa la doni) i, en un torn posterior, l'hora (quan Rosa la doni). També es poden "
        "passar totes dues juntes si Rosa les dona alhora. "
        "El proveïdor és FAST PARCMOTOR per defecte; passa'l només si Rosa vol canviar-lo."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fecha": {
                "type": "string",
                "description": "Data del dissabte de la prova de foc, format DD/MM/AAAA."
            },
            "hora_inicio": {
                "type": "string",
                "description": "Hora d'inici de la sessió, format HH:MM (p.ex. '10:00')."
            },
            "proveedor": {
                "type": "string",
                "description": (
                    "Proveïdor extern. Opcional: si Rosa no l'ha canviat, no passis aquest camp "
                    "i es mantindrà FAST PARCMOTOR."
                )
            }
        },
        "required": ["fecha"]
    }
}

HERRAMIENTA_TERMINAR_PRUEBA_FUEGO = {
    "name": "terminar_prueba_fuego",
    "description": (
        "Marca la Prova de Foc com a completada. Llama-la quan les dades estiguin guardades "
        "i Rosa hagi confirmat que no vol canviar res."
    ),
    "input_schema": {
        "type": "object",
        "properties": {}
    }
}

_HERRAMIENTAS = [
    HERRAMIENTA_GUARDAR_TIPO_CURSO, HERRAMIENTA_VALIDAR_FECHA,
    HERRAMIENTA_PROPONER_INICIO, HERRAMIENTA_VALIDAR_HORARIO, HERRAMIENTA_CONFIRMAR_DATO,
    HERRAMIENTA_VALIDAR_DNI, HERRAMIENTA_ANADIR_ALUMNO, HERRAMIENTA_TERMINAR_ALUMNOS,
    HERRAMIENTA_MARCAR_PROFESOR_GENERAL, HERRAMIENTA_ANADIR_EXCEPCION_PROFESOR,
    HERRAMIENTA_TERMINAR_PROFESORES, HERRAMIENTA_GUARDAR_PROFESOR_PRACTICAS,
    HERRAMIENTA_TERMINAR_PRACTICAS, HERRAMIENTA_GUARDAR_PRUEBA_FUEGO,
    HERRAMIENTA_TERMINAR_PRUEBA_FUEGO,
]

# Etiquetas en español para mostrar en el system prompt variable
_NOMBRES_LEGIBLES = {
    "dia_amarillo": "día amarillo (último día del plan)",
    "dia_verde":    "día verde (fecha del examen)",
    "fecha_inicio": "fecha de inicio del curso",
    "festivos":     "festivos del período",
}


def _instrucciones_genericas(siguiente):
    """Instrucciones para datos que Rosa da directamente: dia_amarillo."""
    return "\n".join([
        "Pídeselo a Rosa con naturalidad, sin tecnicismos.",
        "Cuando Rosa te dé la fecha, valídala con la herramienta validar_fecha.",
        "Si es válida, repítesela para que la confirme ('¿Es el DD/MM/AAAA, correcto?').",
        f"Cuando Rosa confirme, llama a confirmar_dato con nombre_dato='{siguiente}' y el valor.",
    ])


def _instrucciones_dia_verde(estado):
    """
    Instrucciones específicas para dia_verde (examen).

    No usa _instrucciones_genericas porque este dato tiene una regla de coherencia
    con dia_amarillo que el LLM debe conocer explícitamente: si no se le dice, el
    modelo puede "inventarse" la relación al revés (rechazar exámenes posteriores
    al día amarillo, cuando es justo lo contrario lo que exige el CAP).
    """
    dia_amarillo = estado["dia_amarillo"]["valor"]
    return "\n".join([
        "Pídeselo a Rosa con naturalidad, sin tecnicismos.",
        f"IMPORTANTE — regla de coherencia: el día verde (examen) tiene que ser "
        f"POSTERIOR al día amarillo ({dia_amarillo}, el último día del curso) — "
        "nunca antes ni el mismo día. Primero termina el curso, luego se hace el examen.",
        "Cuando Rosa te dé la fecha, valídala con la herramienta validar_fecha "
        "(esto solo comprueba que sea una fecha real; NO comprueba la relación con "
        "el día amarillo — de eso ya se encarga el sistema al confirmar el dato).",
        "Si es válida, repítesela para que la confirme ('¿Es el DD/MM/AAAA, correcto?').",
        "Cuando Rosa confirme, llama a confirmar_dato con nombre_dato='dia_verde' y el valor. "
        "Si el sistema lo rechaza por no ser posterior al día amarillo, explícaselo a Rosa "
        "con el motivo que te devuelva y pídele una fecha posterior.",
    ])


def _instrucciones_festivos(estado):
    """Instrucciones para festivos: lista de fechas (posiblemente vacía), no una fecha suelta."""
    fecha_inicio = estado["fecha_inicio"]["valor"]
    dia_amarillo = estado["dia_amarillo"]["valor"]
    return "\n".join([
        f"Pregúntale a Rosa si hay festivos entre el {fecha_inicio} y el {dia_amarillo}.",
        "'Ninguno' o 'no hay' es una respuesta válida: equivale a lista vacía.",
        "Si Rosa da fechas: valida CADA UNA con validar_fecha antes de dar nada por bueno.",
        "Si alguna fecha está mal escrita, pídele que la corrija; no avances hasta que estén todas bien.",
        "Cuando todas estén validadas (o Rosa diga que no hay ninguna), repítele la lista para confirmar:",
        "  - Con fechas: 'Entonces los festivos son: [lista], ¿correcto?'",
        "  - Sin fechas: 'Entonces no hay festivos en ese período, ¿correcto?'",
        "Cuando Rosa confirme, llama a confirmar_dato con nombre_dato='festivos' y valor=array de strings ([] si no hay ninguno).",
    ])


def _instrucciones_fecha_inicio(estado):
    """Instrucciones para fecha_inicio: se propone a partir del día amarillo, no se pregunta."""
    dia_amarillo = estado["dia_amarillo"]["valor"]
    return "\n".join([
        f"Usa la herramienta proponer_inicio con dia_amarillo='{dia_amarillo}' (ya lo tienes guardado, NO se lo pidas a Rosa).",
        "Muéstrale la fecha propuesta con naturalidad: 'Propongo empezar el [fecha], ¿te va bien o prefieres otra?'.",
        "Si Rosa ACEPTA la propuesta: llama a confirmar_dato con nombre_dato='fecha_inicio' y la fecha propuesta.",
        "Si Rosa prefiere OTRA fecha: valídala con validar_fecha, confírmala con Rosa, y entonces llama a confirmar_dato con esa fecha nueva.",
    ])


def _contexto_calendario(estado):
    """Genera la parte variable del system prompt para el bloque calendario."""
    lineas = ["ESTADO DE LA RECOGIDA DEL BLOQUE CALENDARIO:"]

    for nombre in ["dia_amarillo", "dia_verde", "fecha_inicio", "festivos"]:
        etiqueta = _NOMBRES_LEGIBLES[nombre]
        entrada = estado[nombre]
        if entrada["conseguido"]:
            lineas.append(f"  - {etiqueta}: YA CONSEGUIDO → {entrada['valor']}")
        else:
            lineas.append(f"  - {etiqueta}: pendiente")

    siguiente = siguiente_dato_pendiente(estado)
    if siguiente:
        etiqueta = _NOMBRES_LEGIBLES[siguiente]
        lineas.append(f"\nAHORA TE TOCA: conseguir el {etiqueta}.")
        if siguiente == "fecha_inicio":
            lineas.append(_instrucciones_fecha_inicio(estado))
        elif siguiente == "festivos":
            lineas.append(_instrucciones_festivos(estado))
        elif siguiente == "dia_verde":
            lineas.append(_instrucciones_dia_verde(estado))
        else:
            lineas.append(_instrucciones_genericas(siguiente))
    else:
        lineas.append("\nTodos los datos del bloque calendario están conseguidos.")

    return "\n".join(lineas)


_NOMBRES_LEGIBLES_FRANJAS = {
    "horario_lun_jue": "horario de lunes a jueves",
    "horario_viernes": "horario de viernes",
    "horario_sabado":  "horario de sábados",
}

# Horarios habituales que el agente propone a Rosa como punto de partida
_HORARIOS_HABITUALES = {
    "horario_lun_jue": {"inicio": "18:00", "fin": "21:15", "dias": "lunes a jueves"},
    "horario_viernes": {"inicio": "16:00", "fin": "20:15", "dias": "viernes"},
    "horario_sabado":  {"inicio": "07:45", "fin": "14:15", "dias": "sábados"},
}


def _instrucciones_horario(nombre_dato):
    h = _HORARIOS_HABITUALES[nombre_dato]
    return "\n".join([
        f"Propón a Rosa el horario habitual de {h['dias']}: de {h['inicio']} a {h['fin']}.",
        "Pídele que lo confirme o que dé un horario distinto.",
        "Cuando Rosa indique un horario (el habitual u otro), valídalo con la herramienta validar_horario.",
        "Si no es válido, explícale el problema y pídele que lo corrija.",
        f"Si es válido, repíteselo para que confirme ('¿Entonces {h['dias']} de [inicio] a [fin], correcto?').",
        f"Cuando Rosa confirme, llama a confirmar_dato con:",
        f"  nombre_dato = '{nombre_dato}'",
        f"  valor       = un OBJETO con dos campos: inicio y fin.",
        f"                Usa los valores exactos que devolvió validar_horario.",
        f"                Ejemplo: si validar_horario devolvió inicio='18:00' y fin='21:30',",
        f"                el valor debe ser {{\"inicio\": \"18:00\", \"fin\": \"21:30\"}}",
        f"                NUNCA un string como '18:00-21:30' — siempre el objeto {{inicio, fin}}.",
        f"                OJO: aunque validar_horario usa los nombres hora_inicio/hora_fin,",
        f"                para confirmar_dato las claves son 'inicio' y 'fin' (sin el prefijo 'hora_').",
    ])


def _contexto_franjas(estado_franjas):
    """Genera la parte variable del system prompt para el bloque franjas horarias."""
    lineas = ["ESTADO DE LA RECOGIDA DE LOS HORARIOS:"]

    for nombre in ["horario_lun_jue", "horario_viernes", "horario_sabado"]:
        etiqueta = _NOMBRES_LEGIBLES_FRANJAS[nombre]
        entrada = estado_franjas[nombre]
        if entrada["conseguido"]:
            v = entrada["valor"]
            if isinstance(v, dict) and "inicio" in v and "fin" in v:
                lineas.append(f"  - {etiqueta}: YA CONSEGUIDO → de {v['inicio']} a {v['fin']}")
            else:
                lineas.append(f"  - {etiqueta}: YA CONSEGUIDO → {v} (formato pendiente de corregir)")
        else:
            lineas.append(f"  - {etiqueta}: pendiente")

    siguiente = siguiente_pendiente_franjas(estado_franjas)
    if siguiente:
        etiqueta = _NOMBRES_LEGIBLES_FRANJAS[siguiente]
        lineas.append(f"\nAHORA TE TOCA: conseguir el {etiqueta}.")
        lineas.append(_instrucciones_horario(siguiente))
    else:
        lineas.append("\nTodos los horarios están recogidos.")

    return "\n".join(lineas)


def _contexto_orden(estado_orden):
    """Genera la parte variable del system prompt para el bloque orden de asignaturas."""
    entrada = estado_orden["orden"]

    if entrada["conseguido"]:
        return "ORDEN DE ASIGNATURAS: YA CONFIRMADO."

    # Construir la lista legible del orden habitual para mostrársela a Rosa
    lineas_orden = "\n".join(
        f"  {i+1:>2}. [{codigo}]"
        for i, codigo in enumerate(ORDEN_HABITUAL_MERCANCIAS)
    )

    return "\n".join([
        "ESTADO DE LA RECOGIDA DEL ORDEN DE ASIGNATURAS:",
        "  - orden de impartición: pendiente",
        "",
        "AHORA TE TOCA: confirmar el orden de las asignaturas.",
        "Muéstrale a Rosa el orden habitual completo de forma clara y numerada:",
        lineas_orden,
        "Pregúntale si ese orden le va bien o si quiere cambiar algo.",
        "Si Rosa confirma el orden habitual, llama a confirmar_dato con nombre_dato='orden'"
        " y valor=" + repr(ORDEN_HABITUAL_MERCANCIAS) + ".",
        "(Por ahora no gestionamos reordenamientos: si Rosa pide cambios, dile que"
        " esa funcionalidad estará disponible próximamente y confirma el orden habitual.)",
    ])


def _contexto_profesores(estado_profesores):
    """Genera la parte variable del system prompt para el bloque profesores."""
    profesor_general = estado_profesores["profesor_general"]
    excepciones      = estado_profesores["excepciones"]
    terminado        = estado_profesores["terminado"]

    # Fase 3: bloque completo
    if terminado:
        n = len(excepciones)
        exc_txt = f"{n} excepción" if n == 1 else f"{n} excepciones"
        return (
            f"PROFESORES: COMPLETADO. "
            f"Profesor general: {profesor_general}. {exc_txt} registradas."
        )

    # Fase 1: todavía no se ha dado el profesor general
    if profesor_general is None:
        return "\n".join([
            "=== BLOQUE ACTUAL: PROFESORES ===",
            "(El bloque de ALUMNOS viene después de este. Ahora toca exclusivamente los PROFESORES.)",
            "",
            "ESTADO DE LA RECOGIDA DE PROFESORES:",
            "  - Profesor general: pendiente",
            "",
            "AHORA TE TOCA: preguntar quién es el profesor general del curso.",
            "Explícale a Rosa que es el profesor que dará la mayor parte de las clases.",
            "Cuando Rosa te diga el nombre, repíteselo para que confirme.",
            "Cuando Rosa confirme, llama a marcar_profesor_general con el nombre.",
        ])

    # Fase 2: profesor general dado, excepciones pendientes de cerrar
    lineas = ["=== BLOQUE ACTUAL: PROFESORES ==="]
    lineas.append("ESTADO DE LA RECOGIDA DE PROFESORES:")
    lineas.append(f"  - Profesor general: {profesor_general}")
    if not excepciones:
        lineas.append("  - Excepciones por día: ninguna todavía")
    else:
        lineas.append(f"  - Excepciones por día registradas: {len(excepciones)}")
        for exc in excepciones:
            lineas.append(f"      · {exc['fecha']} → {exc['profesor']}")

    lineas.append("\nAHORA TE TOCA: preguntar a Rosa si hay días con un profesor distinto.")
    lineas.append("\n".join([
        "Explícale que si según su planificación hay días concretos en los que dará clase",
        "un profesor diferente al general, que te los diga. Rosa ya sabe de su propia",
        "organización si hay sustituciones previstas — el agente no las adivina.",
        "",
        "Si Rosa indica una excepción: pide la fecha (DD/MM/AAAA) y el nombre del profesor.",
        "Llama a anadir_excepcion_profesor con la fecha y el profesor.",
        "  - Si la fecha no es válida, explica el problema y pide corrección. No añadas.",
        "  - Si es válida, confirma a Rosa que quedó apuntada y pregunta si hay otra.",
        "",
        "Si Rosa dice que NO hay excepciones o que ya están todas, puedes llamar a",
        "terminar_profesores. PERO además, y esto es lo más importante, dile a Rosa:",
        "  'Cuando ya no haya más profesores sustitutos que añadir, pulsa el botón",
        "  ✅ No hay más profesores sustitutos que tienes debajo del chat. No hace",
        "  falta que me lo confirmes por aquí.'",
        "El botón es la forma fiable de cerrar este paso — menciónalo siempre en algún",
        "momento de esta fase, aunque tú también llames a terminar_profesores.",
    ]))

    return "\n".join(lineas)


def _contexto_alumnos(estado_alumnos):
    """Genera la parte variable del system prompt para el bloque alumnos."""
    alumnos   = estado_alumnos["alumnos"]
    terminado = estado_alumnos["terminado"]
    n         = len(alumnos)

    if terminado:
        return f"RECOGIDA DE ALUMNOS: COMPLETA ({n} alumnos registrados)."

    hay_ampliacion = any(a["tipo_curso"] == "ampliacion" for a in alumnos)

    lineas = ["ESTADO DE LA RECOGIDA DE ALUMNOS:"]
    if n == 0:
        lineas.append("  - Alumnos recogidos hasta ahora: ninguno")
    else:
        n_comp = sum(1 for a in alumnos if a["tipo_curso"] == "completo")
        n_amp  = sum(1 for a in alumnos if a["tipo_curso"] == "ampliacion")
        lineas.append(f"  - Alumnos recogidos hasta ahora: {n} "
                      f"({n_comp} completos, {n_amp} ampliación)")
        for a in alumnos:
            lineas.append(f"      · {a['nombre']} ({a['tipo_curso']})")

    lineas.append("\nAHORA TE TOCA: recoger la lista de alumnos del curso.")

    if n == 0:
        # Primera vez que entramos: preguntar si hay alumnos y si hay ampliación
        lineas.append(
            "Haz DOS preguntas en UN solo mensaje:\n"
            "  1. ¿Quiere añadir alumnos ahora, o de momento no hay ninguno?\n"
            "     - Si Rosa dice que NO hay alumnos: dile que pulse el botón\n"
            "       ✅ Ya he añadido todos los alumnos que tiene debajo del chat\n"
            "       (también puedes llamar a terminar_alumnos, pero el botón es lo fiable).\n"
            "  2. Si sí hay alumnos: ¿todos hacen el curso COMPLETO, o hay alguno de AMPLIACIÓN?\n"
            "     Guarda mentalmente la respuesta — cambia cómo preguntas a cada alumno (ver abajo).\n"
            "\n"
            "CASO A — todos COMPLETOS (lo habitual):\n"
            "  Para cada alumno pide SOLO nombre completo + DNI/NIE.\n"
            "  Llama a anadir_alumno con tipo_curso='completo' SIEMPRE, sin preguntarlo a Rosa.\n"
            "\n"
            "CASO B — hay alumnos de AMPLIACIÓN:\n"
            "  Recoge primero todos los alumnos COMPLETOS (nombre + DNI, tipo_curso='completo').\n"
            "  Cuando Rosa indique que ya están los completos, recoge los de AMPLIACIÓN\n"
            "  (nombre + DNI, tipo_curso='ampliacion').\n"
            "  Si en cualquier momento Rosa indica el tipo al dar un alumno, respétalo.\n"
        )
    elif not hay_ampliacion:
        # Ya hay alumnos y todos son completos: seguir en modo sin preguntar tipo
        lineas.append(
            "Modo activo: TODOS COMPLETOS — no preguntes el tipo a cada alumno.\n"
            "Para cada alumno pide SOLO nombre completo + DNI/NIE.\n"
            "Llama a anadir_alumno con tipo_curso='completo' automáticamente.\n"
        )
    else:
        # Ya hay alumnos de ampliación: modo mixto
        lineas.append(
            "Modo activo: HAY AMPLIACIÓN — distingue completos y ampliación.\n"
            "Para cada alumno pide nombre + DNI/NIE e indica si es completo o ampliación.\n"
        )

    lineas.append(
        "PROCESO PARA CADA ALUMNO:\n"
        "  - Pide nombre completo y DNI/NIE.\n"
        "  - Valida el documento con validar_dni.\n"
        "      · Si NO es válido: explica el error y pide que lo corrija. No añadas el alumno.\n"
        "      · Si es válido: llama a anadir_alumno (nombre, documento, tipo_curso).\n"
        "  - Después de añadir, pregunta si hay otro alumno.\n"
        "  - Cuando Rosa diga que ya están todos, puedes llamar a terminar_alumnos.\n"
        "    PERO además, y esto es lo más importante, dile en algún momento:\n"
        "    'Cuando hayas terminado de añadir alumnos, pulsa el botón\n"
        "    ✅ Ya he añadido todos los alumnos que tienes debajo del chat.\n"
        "    No hace falta que me lo confirmes por aquí.'\n"
        "    El botón es la forma fiable de cerrar este paso."
    )

    return "\n".join(lineas)


# Tabla de comprobaciones de coherencia entre fechas.
# Cada entrada: nombre_dato → función que recibe (valor_nuevo, estado) y devuelve
# el resultado de la comprobación de coherencia (dict con 'coherente' y 'mensaje').
# Los datos ausentes (dia_amarillo, festivos) no tienen comprobación: se marcan sin más.
_COMPROBACIONES_COHERENCIA = {
    "dia_verde": lambda valor, est: validar_verde_despues_amarillo(
        valor, est["dia_amarillo"]["valor"]
    ),
    "fecha_inicio": lambda valor, est: validar_inicio_antes_amarillo(
        valor, est["dia_amarillo"]["valor"]
    ),
}


def _verificar_coherencia(nombre_dato, valor, estados):
    """
    Devuelve el resultado de coherencia si el dato tiene comprobación, None si no aplica.
    Consultar _COMPROBACIONES_COHERENCIA para ver qué datos se comprueban.
    """
    comprobacion = _COMPROBACIONES_COHERENCIA.get(nombre_dato)
    if comprobacion is None:
        return None
    return comprobacion(valor, estados["calendario"])


def _contexto_practicas(estado_practicas):
    """Genera la parte variable del system prompt para el bloque prácticas."""
    profesor = estado_practicas["profesor"]

    lineas = ["ESTADO DE LA RECOGIDA DE PRÁCTICAS:"]
    if profesor is None:
        lineas.append("  - Profesor: pendiente")
    else:
        lineas.append(f"  - Profesor recogido: {profesor}")

    lineas.append(
        "\nAHORA TE TOCA: recoger el nombre del profesor que impartirá las prácticas.\n"
        "\n"
        "El sistema calcula y coloca las sesiones de prácticas automáticamente\n"
        "(10h por alumno de curso completo + 2.5h por alumno de ampliación),\n"
        "así que Rosa solo necesita indicar el nombre del profesor.\n"
        "\n"
        "Pide a Rosa el nombre del profesor de prácticas.\n"
        "Cuando Rosa te lo dé, repíteselo para confirmar.\n"
        "\n"
        "*** IMPORTANTE — ESTE ES EL ÚLTIMO PASO ***\n"
        "Cuando Rosa confirme, llama a guardar_profesor_practicas con ese nombre.\n"
        "Esa llamada GENERA AUTOMÁTICAMENTE el documento .docx con el horario completo\n"
        "del CAP — el sistema lo hace solo, en cuanto guardas el profesor.\n"
        "Tras esa llamada, dile a Rosa:\n"
        "  '¡Listo! El horario está generado. Puedes descargarlo con el botón de abajo.'"
    )

    return "\n".join(lineas)


def _validar_fecha_pf_en_curso(nombre_dato, valor, estados):
    """
    Valida que la data de la Prova de Foc estigui dins del rang del curs.
    Firma uniforme (nombre_dato, valor, estados) com la resta de validadors.
    'valor' és el string "DD/MM/AAAA" que prové de confirmar_dato o guardar_prueba_fuego.
    """
    r = parsear_fecha(valor) if isinstance(valor, str) else {"valida": False}
    if not r["valida"]:
        return {"coherente": False, "mensaje": f"Fecha de la prueba de fuego no válida: {valor!r}"}
    fecha_date = r["fecha"]

    cal = estados["calendario"]
    inicio_str   = cal["fecha_inicio"]["valor"]
    amarillo_str = cal["dia_amarillo"]["valor"]

    r_ini = parsear_fecha(inicio_str)
    r_ama = parsear_fecha(amarillo_str)
    if not r_ini["valida"] or not r_ama["valida"]:
        return {"coherente": False, "mensaje": "No es pot verificar el rang del curs (dates invàlides)."}

    if fecha_date < r_ini["fecha"] or fecha_date > r_ama["fecha"]:
        return {
            "coherente": False,
            "mensaje": (
                f"La fecha de la prueba de fuego ({fecha_date.strftime('%d/%m/%Y')}) "
                f"está fuera del rango del curso ({inicio_str} – {amarillo_str})."
            ),
        }
    return {"coherente": True, "mensaje": ""}


def _contexto_prueba_fuego(estado_pf):
    """Genera la part variable del system prompt per al bloc prova de foc."""
    fecha = estado_pf["fecha"]
    hora  = estado_pf["hora_inicio"]
    prov  = estado_pf["proveedor"]

    if fecha is not None and hora is not None:
        return (
            f"PROVA DE FOC: COMPLETADA. "
            f"Data: {fecha.strftime('%d/%m/%Y')}, "
            f"hora: {hora.strftime('%H:%M')}, "
            f"proveïdor: {prov}."
        )

    lineas = ["=== BLOQUE ACTUAL: PRUEBA DE FUEGO ==="]
    lineas.append("ESTADO:")
    lineas.append(f"  - Fecha del sábado PF: {'PENDIENTE' if fecha is None else 'YA GUARDADA (' + fecha.strftime('%d/%m/%Y') + ')'}")
    lineas.append(f"  - Hora de inicio:      {'PENDIENTE' if hora  is None else 'YA GUARDADA (' + hora.strftime('%H:%M') + ')'}")
    lineas.append(f"  - Proveedor:           {prov}")

    if fecha is None:
        # Aún no hay fecha: pedirla (y de paso la hora, si Rosa la da junta).
        lineas.append("\n".join([
            "",
            "*** ESTE ES EL PASO ACTUAL: la Prueba de Fuego. ***",
            "No hables de franjas, alumnos, profesores ni prácticas hasta recoger la fecha",
            "Y la hora de la prueba de fuego.",
            "",
            "AHORA TE TOCA: recoger los datos de la Prueba de Fuego (Prova de Foc).",
            "",
            "La Prueba de Fuego es una sesión EXTERNA de 2h de MM.PP que Rosa programa",
            "en un sábado concreto del curso con el proveedor FAST PARCMOTOR (o similar).",
            "",
            "Pregunta a Rosa:",
            "  1. ¿En qué SÁBADO se hará la prueba de fuego?",
            "     Debe ser un sábado dentro del rango del curso.",
            "  2. ¿A qué hora empieza? (p.ej. 10:00)",
            "  3. ¿El proveedor es FAST PARCMOTOR?",
            "     Solo preguntar si Rosa quiere cambiarlo; el valor por defecto es FAST PARCMOTOR.",
            "",
            "Si Rosa te da la fecha y la hora juntas, llama a guardar_prueba_fuego con",
            "fecha (DD/MM/AAAA) y hora_inicio (HH:MM) a la vez. Pasa 'proveedor' solo si",
            "Rosa indicó uno distinto.",
            "Si Rosa solo te da la fecha por ahora, llama a guardar_prueba_fuego SOLO con",
            "fecha — el sistema la guarda y te recordará pedir la hora en el siguiente turno.",
            "",
            "Si el sistema devuelve error (no es sábado o fuera del curso), explícaselo a Rosa",
            "y pide que corrija la fecha.",
        ]))
    else:
        # *** CLAVE: la fecha ya está guardada, SOLO falta la hora. ***
        lineas.append(
            "\n".join([
                "",
                f"*** IMPORTANTE: YA TIENES LA FECHA ({fecha.strftime('%d/%m/%Y')}). "
                "SOLO TE FALTA LA HORA. ***",
                "NO hables de otra cosa (alumnos, profesores, franjas, etc.) hasta tener la hora.",
                f"Pregunta a Rosa: '¿A qué hora empieza la prueba de fuego del "
                f"{fecha.strftime('%d/%m/%Y')}?' (p.ej. 10:00)",
                "Cuando te la dé, llama a guardar_prueba_fuego SOLO con hora_inicio (HH:MM) —",
                "no hace falta que repitas la fecha, ya está guardada.",
            ])
        )

    return "\n".join(lineas)


def _contexto_tipo_curso(estado_tipo_curso):
    """Genera la parte variable del system prompt para el bloque tipo de curso."""
    tipo      = estado_tipo_curso["tipo_curso"]
    terminado = estado_tipo_curso["terminado"]

    if terminado:
        etiqueta = "MERCANCIES" if tipo == "mercancias" else "VIATGERS"
        return f"TIPUS DE CURS: COMPLETAT ({etiqueta})."

    if tipo is None:
        return (
            "ESTADO: pendiente de elegir el tipo de curso.\n"
            "\n"
            "AHORA TE TOCA: preguntar a Rosa qué tipo de curso CAP va a preparar.\n"
            "\n"
            "Hay dos opciones:\n"
            "  · MERCANCIES: Qualificació Inicial de transport de Mercaderies\n"
            "  · VIATGERS:   Qualificació Inicial de transport de Viatgers\n"
            "\n"
            "Cuando Rosa elija uno, llama a guardar_tipo_curso con 'mercancias' o 'viatgers'."
        )

    return f"TIPUS DE CURS: {tipo} (pendent de confirmar)."


BLOQUES = [
    {
        "nombre":            "tipo_curso",
        "crear_estado":      crear_estado_tipo_curso,
        "bloque_completo":   bloque_completo_tipo_curso,
        "marcar_conseguido": None,
        "contexto":          _contexto_tipo_curso,
        "validacion":        None,
    },
    {
        "nombre":            "calendario",
        "crear_estado":      crear_estado_calendario,
        "bloque_completo":   bloque_completo_calendario,
        "marcar_conseguido": marcar_conseguido_calendario,
        "contexto":          _contexto_calendario,
        "validacion":        _verificar_coherencia,
    },
    {
        "nombre":            "prueba_fuego",
        "crear_estado":      crear_estado_prueba_fuego,
        "bloque_completo":   bloque_completo_prueba_fuego,
        "marcar_conseguido": None,
        "contexto":          _contexto_prueba_fuego,
        "validacion":        _validar_fecha_pf_en_curso,
        "condicion":         lambda estados: estados["tipo_curso"]["tipo_curso"] == "mercancias",
    },
    {
        "nombre":            "franjas",
        "crear_estado":      crear_estado_franjas,
        "bloque_completo":   bloque_completo_franjas,
        "marcar_conseguido": marcar_conseguido_franjas,
        "contexto":          _contexto_franjas,
        "validacion":        None,
    },
    {
        "nombre":            "orden",
        "crear_estado":      crear_estado_orden,
        "bloque_completo":   bloque_completo_orden,
        "marcar_conseguido": marcar_conseguido_orden,
        "contexto":          _contexto_orden,
        "validacion":        None,
    },
    {
        "nombre":            "alumnos",
        "crear_estado":      crear_estado_alumnos,
        "bloque_completo":   bloque_completo_alumnos,
        "marcar_conseguido": None,
        "contexto":          _contexto_alumnos,
        "validacion":        None,
    },
    {
        "nombre":            "profesores",
        "crear_estado":      crear_estado_profesores,
        "bloque_completo":   bloque_completo_profesores,
        "marcar_conseguido": None,
        "contexto":          _contexto_profesores,
        "validacion":        None,
    },
    {
        "nombre":            "practicas",
        "crear_estado":      crear_estado_practicas,
        "bloque_completo":   bloque_completo_practicas,
        "marcar_conseguido": None,
        "contexto":          _contexto_practicas,
        "validacion":        None,
    },
]


def _construir_contexto_estado(bloque_actual, estados):
    """Elige el constructor de contexto según el bloque que está en curso."""
    bloque = next(b for b in BLOQUES if b["nombre"] == bloque_actual)
    return bloque["contexto"](estados[bloque_actual])


def _fuera_de_turno(nombre_bloque_tool, bloque_actual):
    """
    Devuelve un mensaje de rechazo si esta tool no pertenece al bloque activo,
    o None si sí coincide (vía libre).

    Evita que un bloque se complete "fuera de turno" (por ejemplo, guardar un
    alumno mientras el paso activo real sigue siendo prueba_fuego), que dejaba
    bloque_actual congelado sin que el estado interno reflejara lo mismo.
    """
    if bloque_actual == nombre_bloque_tool:
        return None
    return (
        f"Esto pertenece al paso '{nombre_bloque_tool}', pero ahora mismo el paso "
        f"activo es '{bloque_actual}'. Termina primero el paso actual antes de continuar."
    )


def _ejecutar_herramienta(nombre, argumentos, estados, bloque_actual):
    """Despacha la llamada a la función Python real y devuelve el resultado como dict."""
    if nombre == "guardar_tipo_curso":
        motivo = _fuera_de_turno("tipo_curso", bloque_actual)
        if motivo:
            return {"tipo_guardado": False, "motivo": motivo}
        tipo = argumentos["tipo_curso"]
        guardado = guardar_tipo_curso_tc(estados["tipo_curso"], tipo)
        if guardado:
            return {"tipo_guardado": True, "tipo": tipo}
        return {"tipo_guardado": False, "motivo": f"Valor no vàlid: {tipo!r}. Usa 'mercancias' o 'viatgers'."}
    if nombre == "validar_fecha":
        return parsear_fecha(argumentos["fecha"])
    if nombre == "proponer_inicio":
        return proponer_fecha_inicio(argumentos["dia_amarillo"])
    if nombre == "validar_horario":
        return validar_horario(argumentos["hora_inicio"], argumentos["hora_fin"])
    if nombre == "confirmar_dato":
        nombre_dato   = argumentos["nombre_dato"]
        valor         = argumentos["valor"]
        bloque_def    = next(b for b in BLOQUES if b["nombre"] == bloque_actual)
        # nombre_dato pertenece a un bloque concreto (p. ej. "dia_amarillo" es de calendario).
        # Si bloque_actual no es el dueño de ese dato, rechazamos con mensaje claro en vez
        # de dejar que reviente más abajo (marcar_conseguido=None o estado_bloque[nombre_dato]
        # inexistente).
        if bloque_def["marcar_conseguido"] is None or nombre_dato not in estados[bloque_actual]:
            return {
                "guardado": False,
                "nombre_dato": nombre_dato,
                "motivo": (
                    f"'{nombre_dato}' no pertenece al paso activo ('{bloque_actual}'). "
                    "Comprueba qué paso toca ahora y confirma el dato correcto."
                ),
            }
        estado_bloque = estados[bloque_actual]
        # Franges horàries: el valor SEMPRE ha de ser {"inicio": "HH:MM", "fin": "HH:MM"}.
        # El LLM a vegades confon els noms amb els paràmetres de validar_horario
        # (hora_inicio/hora_fin) o envia un string; ho acceptem igual convertint-ho.
        # Si no es pot interpretar de cap manera, rebutgem amb missatge clar.
        _NOMS_FRANJA = {"horario_lun_jue", "horario_viernes", "horario_sabado"}
        if nombre_dato in _NOMS_FRANJA:
            # Alias: hora_inicio/hora_fin (nombres de validar_horario) → inicio/fin
            if isinstance(valor, dict) and "inicio" not in valor and "fin" not in valor \
                    and "hora_inicio" in valor and "hora_fin" in valor:
                valor = {"inicio": valor["hora_inicio"], "fin": valor["hora_fin"]}
            if isinstance(valor, str):
                # Extrae las dos horas HH:MM ignorando palabras de relleno
                # ("de", "a", "hasta", "-", etc.): "de 18:00 a 21:30" → ["18:00", "21:30"]
                horas = _PATRON_HORA.findall(valor)
                if len(horas) != 2:
                    return {
                        "guardado": False,
                        "nombre_dato": nombre_dato,
                        "motivo": (
                            f"El valor '{valor}' no es un objeto válido. "
                            "El valor debe ser un objeto con dos campos: "
                            "{\"inicio\": \"HH:MM\", \"fin\": \"HH:MM\"}. "
                            "Vuelve a llamar a confirmar_dato con ese formato."
                        ),
                    }
                valor = {"inicio": horas[0], "fin": horas[1]}
            if not (isinstance(valor, dict) and "inicio" in valor and "fin" in valor):
                return {
                    "guardado": False,
                    "nombre_dato": nombre_dato,
                    "motivo": (
                        "El valor de la franja debe ser un objeto con campos 'inicio' y 'fin'. "
                        "Ejemplo: {\"inicio\": \"18:00\", \"fin\": \"21:30\"}."
                    ),
                }
        # La validación previa (coherencia de fechas para el calendario) se comprueba aquí,
        # en el despacho, no como herramienta LLM. El LLM no puede saltársela: si falla,
        # el dato no se marca y el agente recibe el mensaje de error para explicárselo a Rosa.
        if bloque_def["validacion"] is not None:
            resultado_val = bloque_def["validacion"](nombre_dato, valor, estados)
            if resultado_val is not None and not resultado_val["coherente"]:
                return {"guardado": False, "nombre_dato": nombre_dato, "motivo": resultado_val["mensaje"]}
        bloque_def["marcar_conseguido"](estado_bloque, nombre_dato, valor)
        return {"guardado": True, "nombre_dato": nombre_dato, "valor": valor}
    if nombre == "validar_dni":
        return validar_documento(argumentos["documento"])
    if nombre == "anadir_alumno":
        motivo = _fuera_de_turno("alumnos", bloque_actual)
        if motivo:
            return {"añadido": False, "motivo": motivo}
        # Doble candado: revalidamos antes de añadir aunque el LLM ya haya llamado validar_dni
        validacion = validar_documento(argumentos["documento"])
        if not validacion["valido"]:
            return {"añadido": False, "motivo": validacion["mensaje"]}
        doc_limpio = validacion["documento"]
        anadir_alumno_alumnos(estados["alumnos"], argumentos["nombre"], doc_limpio, argumentos["tipo_curso"])
        return {"añadido": True, "nombre": argumentos["nombre"], "documento": doc_limpio, "tipo_curso": argumentos["tipo_curso"]}
    if nombre == "terminar_alumnos":
        motivo = _fuera_de_turno("alumnos", bloque_actual)
        if motivo:
            return {"terminado": False, "motivo": motivo}
        marcar_terminado_alumnos(estados["alumnos"])
        return {"terminado": True, "total_alumnos": len(estados["alumnos"]["alumnos"])}
    if nombre == "marcar_profesor_general":
        motivo = _fuera_de_turno("profesores", bloque_actual)
        if motivo:
            return {"guardado": False, "motivo": motivo}
        marcar_profesor_general_profesores(estados["profesores"], argumentos["nombre"])
        return {"guardado": True, "profesor_general": argumentos["nombre"]}
    if nombre == "anadir_excepcion_profesor":
        motivo = _fuera_de_turno("profesores", bloque_actual)
        if motivo:
            return {"añadida": False, "motivo": motivo}
        # Doble candado: validamos la fecha antes de añadir
        resultado_fecha = parsear_fecha(argumentos["fecha"])
        if not resultado_fecha["valida"]:
            return {"añadida": False, "motivo": resultado_fecha["mensaje"]}
        anadir_excepcion_profesores(estados["profesores"], argumentos["fecha"], argumentos["profesor"])
        return {"añadida": True, "fecha": argumentos["fecha"], "profesor": argumentos["profesor"]}
    if nombre == "terminar_profesores":
        motivo = _fuera_de_turno("profesores", bloque_actual)
        if motivo:
            return {"terminado": False, "motivo": motivo}
        marcar_terminado_profesores(estados["profesores"])
        n = len(estados["profesores"]["excepciones"])
        return {"terminado": True, "total_excepciones": n}
    if nombre == "guardar_profesor_practicas":
        motivo = _fuera_de_turno("practicas", bloque_actual)
        if motivo:
            return {"profesor_guardado": False, "motivo": motivo}
        guardar_profesor_practicas(estados["practicas"], argumentos["profesor"])
        return {"profesor_guardado": True, "profesor": argumentos["profesor"]}
    if nombre == "terminar_practicas":
        motivo = _fuera_de_turno("practicas", bloque_actual)
        if motivo:
            return {"terminado": False, "motivo": motivo}
        marcar_terminado_practicas(estados["practicas"])
        return {"terminado": True, "profesor": estados["practicas"]["profesor"]}
    if nombre == "guardar_prueba_fuego":
        print(f"[DEBUG-PF] guardar_prueba_fuego LLAMADA: argumentos={argumentos} bloque_actual={bloque_actual!r}")
        motivo = _fuera_de_turno("prueba_fuego", bloque_actual)
        if motivo:
            print(f"[DEBUG-PF] RECHAZADA por fuera de turno: {motivo}")
            return {"guardado": False, "motivo": motivo}

        fecha_str     = argumentos.get("fecha")
        hora_str      = argumentos.get("hora_inicio")
        proveedor_arg = argumentos.get("proveedor")
        estado_pf     = estados["prueba_fuego"]

        if fecha_str is None and hora_str is None:
            print("[DEBUG-PF] RECHAZADA: ni fecha ni hora en la llamada")
            return {"guardado": False, "motivo": "Indica al menos la fecha o la hora."}

        # ── Fecha (si se proporciona en esta llamada) ───────────────────────
        if fecha_str is not None:
            r_fecha = parsear_fecha(fecha_str)
            if not r_fecha["valida"]:
                print(f"[DEBUG-PF] RECHAZADA por fecha inválida: {r_fecha['mensaje']}")
                return {"guardado": False, "motivo": r_fecha["mensaje"]}
            fecha_date = r_fecha["fecha"]
            if fecha_date.weekday() != 5:
                noms = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
                print(f"[DEBUG-PF] RECHAZADA por no ser sábado: {fecha_str} es {noms[fecha_date.weekday()]}")
                return {
                    "guardado": False,
                    "motivo": (
                        f"La fecha {fecha_str} es {noms[fecha_date.weekday()]}, no sábado. "
                        "La prueba de fuego debe programarse un sábado del curso."
                    ),
                }
            bloque_pf = next(b for b in BLOQUES if b["nombre"] == "prueba_fuego")
            cal = estados["calendario"]
            print(
                f"[DEBUG-PF] comprobando rango: fecha_inicio={cal['fecha_inicio']['valor']!r} "
                f"dia_amarillo={cal['dia_amarillo']['valor']!r}"
            )
            resultado_val = bloque_pf["validacion"]("fecha", fecha_str, estados)
            if not resultado_val["coherente"]:
                print(f"[DEBUG-PF] RECHAZADA por rango del curso: {resultado_val['mensaje']}")
                return {"guardado": False, "motivo": resultado_val["mensaje"]}
            estado_pf["fecha"] = fecha_date
            print(f"[DEBUG-PF] fecha guardada: {fecha_date}")

        # ── Hora (si se proporciona en esta llamada) ────────────────────────
        if hora_str is not None:
            if estado_pf["fecha"] is None:
                print("[DEBUG-PF] RECHAZADA: se dio la hora sin tener antes la fecha")
                return {"guardado": False, "motivo": "Primero necesito la fecha del sábado de la prueba de fuego."}
            try:
                estado_pf["hora_inicio"] = datetime.strptime(hora_str, "%H:%M").time()
                print(f"[DEBUG-PF] hora guardada: {estado_pf['hora_inicio']}")
            except ValueError:
                print(f"[DEBUG-PF] RECHAZADA por hora inválida: {hora_str!r}")
                return {"guardado": False, "motivo": f"Hora no vàlida: {hora_str!r}. Usa format HH:MM."}

        if proveedor_arg is not None:
            estado_pf["proveedor"] = proveedor_arg

        falta_fecha = estado_pf["fecha"] is None
        falta_hora  = estado_pf["hora_inicio"] is None
        print(f"[DEBUG-PF] GUARDADO OK. falta_fecha={falta_fecha} falta_hora={falta_hora}")
        return {
            "guardado":    True,
            "fecha":       estado_pf["fecha"].strftime("%d/%m/%Y") if estado_pf["fecha"] else None,
            "hora_inicio": estado_pf["hora_inicio"].strftime("%H:%M") if estado_pf["hora_inicio"] else None,
            "proveedor":   estado_pf["proveedor"],
            "falta_fecha": falta_fecha,
            "falta_hora":  falta_hora,
        }
    if nombre == "terminar_prueba_fuego":
        motivo = _fuera_de_turno("prueba_fuego", bloque_actual)
        if motivo:
            return {"terminado": False, "motivo": motivo}
        marcar_terminado_prueba_fuego(estados["prueba_fuego"])
        pf = estados["prueba_fuego"]
        return {
            "terminado":   True,
            "fecha":       pf["fecha"].strftime("%d/%m/%Y") if pf["fecha"] else None,
            "hora_inicio": pf["hora_inicio"].strftime("%H:%M") if pf["hora_inicio"] else None,
            "proveedor":   pf["proveedor"],
        }
    return {"error": f"Herramienta desconocida: {nombre}"}


_DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _imprimir_horario(horario):
    """Muestra el horario detallado por consola de forma legible."""
    ANCHO = 60
    print("\n" + "=" * ANCHO)
    print("  HORARI CAP — MERCADERIES")
    print("=" * ANCHO)
    for dia_info in horario:
        dia     = dia_info["dia"]
        nom_dia = _DIAS_ES[dia.weekday()].upper()
        print(f"\n  {nom_dia}  {dia.strftime('%d/%m/%Y')}")
        print(f"  {'─' * (ANCHO - 2)}")
        for tramo in dia_info["tramos"]:
            h_ini = tramo["inicio"].strftime("%H:%M")
            h_fin = tramo["fin"].strftime("%H:%M")
            if tramo["tipo"] == "descanso":
                print(f"  {h_ini}–{h_fin}  ── descans ──")
            else:
                codigo = f"[{tramo['codigo']}]"
                print(f"  {h_ini}–{h_fin}  {codigo:<12}  {tramo['nombre']}")
    print("\n" + "=" * ANCHO)


def crear_estado_conversacion():
    """Crea l'estat inicial per a una nova sessió (per a st.session_state)."""
    return {
        "llm_messages": [],
        "estados":       {b["nombre"]: b["crear_estado"]() for b in BLOQUES},
        "bloque_actual": "tipo_curso",
    }


def avanzar_o_generar(estados, bloque_actual):
    """
    Comprueba si el bloque actual está completo y, si lo está, avanza al siguiente
    bloque pendiente o genera el documento final si era el último.

    Se usa tanto desde procesar_turno (cuando el LLM completa un bloque llamando a
    una tool) como desde el manejador de los botones "cerrar lista" de la interfaz
    (que completan un bloque directamente por código, sin pasar por el LLM) — así
    la lógica de avance/generación vive en un único sitio.

    Devuelve:
      {
        "bloque_actual":  str,        # actualizado si avanzó, igual si no
        "avanzo":         bool,       # True si cambió de bloque o se generó el documento
        "terminado":      bool,       # True si se generó el documento
        "ruta_docx":      str | None,
        "respuesta_text": str | None, # mensaje fijo a mostrar en el chat si se generó el documento
      }
    """
    bloque_actual_def = next(b for b in BLOQUES if b["nombre"] == bloque_actual)
    if not bloque_actual_def["bloque_completo"](estados[bloque_actual]):
        return {
            "bloque_actual":  bloque_actual,
            "avanzo":         False,
            "terminado":      False,
            "ruta_docx":      None,
            "respuesta_text": None,
        }

    idx           = BLOQUES.index(bloque_actual_def)
    siguiente_idx = idx + 1
    while siguiente_idx < len(BLOQUES):
        bloque_sig = BLOQUES[siguiente_idx]
        condicion  = bloque_sig.get("condicion")
        # Salta blocs que no apliquen (condició falsa) o que ja estan complets
        if condicion is not None and not condicion(estados):
            siguiente_idx += 1
            continue
        if bloque_sig["bloque_completo"](estados[bloque_sig["nombre"]]):
            siguiente_idx += 1
            continue
        break

    if siguiente_idx < len(BLOQUES):
        return {
            "bloque_actual":  BLOQUES[siguiente_idx]["nombre"],
            "avanzo":         True,
            "terminado":      False,
            "ruta_docx":      None,
            "respuesta_text": None,
        }

    # ── Todos los bloques completos: generar el documento ──────────────────────
    pf_estat = estados["prueba_fuego"]
    pf = None
    if (estados["tipo_curso"]["tipo_curso"] == "mercancias"
            and pf_estat["fecha"] is not None):
        pf = crear_prueba_fuego(
            pf_estat["fecha"], pf_estat["hora_inicio"], pf_estat["proveedor"],
        )
    resultat_h = generar_horario(
        estados["calendario"], estados["franjas"], estados["orden"],
        tipo_curso=estados["tipo_curso"]["tipo_curso"],
        prueba_fuego=pf,
    )
    horari = aplicar_profesores(resultat_h["horario"], estados["profesores"])
    ruta_docx = generar_document(
        horari, str(_BASE / "output_cap.docx"),
        estado_alumnos=estados["alumnos"],
        estado_practicas=estados["practicas"],
        estado_calendario=estados["calendario"],
        estado_franjas=estados["franjas"],
        tipo_curso=estados["tipo_curso"]["tipo_curso"],
    )

    respuesta_text = (
        "¡Perfecto! Ya tengo todos los datos. "
        "He generado el horario completo. "
        "Puedes descargarlo con el botón que aparece abajo."
    )

    return {
        "bloque_actual":  bloque_actual,
        "avanzo":         True,
        "terminado":      True,
        "ruta_docx":      ruta_docx,
        "respuesta_text": respuesta_text,
    }


def procesar_turno(entrada, estado_conversacion, client):
    """
    Processa un torn de la conversa per a la UI de Streamlit.

    Paràmetres:
        entrada             : str  — missatge de Rosa
        estado_conversacion : dict — {"llm_messages", "estados", "bloque_actual"}
        client              : Anthropic — creat i cachejat a l'exterior

    Retorna:
        {
          "respuesta" : str,        # text del LLM per mostrar al xat
          "terminado" : bool,       # True → document generat
          "ruta_docx" : str | None, # ruta del .docx si terminado
          "estado"    : dict,       # estat actualitzat (per desar a session_state)
        }
    """
    messages      = estado_conversacion["llm_messages"]
    estados       = estado_conversacion["estados"]
    bloque_actual = estado_conversacion["bloque_actual"]

    messages.append({"role": "user", "content": entrada})

    respuesta_text = ""
    terminado      = False
    ruta_docx      = None

    # La darrera tool porta cache_control perquè Anthropic cacheiï totes les tools
    _tools_cached = _HERRAMIENTAS[:-1] + [{**_HERRAMIENTAS[-1], "cache_control": {"type": "ephemeral"}}]

    while True:
        # system com a llista: part estàtica cacheada primer, part dinàmica sense caché després
        system_blocks = [
            {"type": "text", "text": SYSTEM_PROMPT,
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": _construir_contexto_estado(bloque_actual, estados)},
        ]

        resposta = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_blocks,
            tools=_tools_cached,
            messages=messages,
        )
        u = resposta.usage
        cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
        cache_read  = getattr(u, "cache_read_input_tokens",     0) or 0
        print(
            f"[TOKENS] bloc={bloque_actual}"
            f" input={u.input_tokens} output={u.output_tokens}"
            f" cache_write={cache_write} cache_read={cache_read}"
            f" stop={resposta.stop_reason}"
        )

        if resposta.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resposta.content})

            resultats = []
            for bloque in resposta.content:
                if bloque.type == "tool_use":
                    resultat = _ejecutar_herramienta(
                        bloque.name, bloque.input, estados, bloque_actual
                    )
                    resultats.append({
                        "type":        "tool_result",
                        "tool_use_id": bloque.id,
                        "content":     json.dumps(resultat, ensure_ascii=False,
                                                  cls=_DecimalEncoder),
                    })
            messages.append({"role": "user", "content": resultats})

            resultado_avance = avanzar_o_generar(estados, bloque_actual)
            bloque_actual = resultado_avance["bloque_actual"]
            if resultado_avance["terminado"]:
                ruta_docx      = resultado_avance["ruta_docx"]
                respuesta_text = resultado_avance["respuesta_text"]
                terminado      = True
                break

        else:  # end_turn
            for bloc in resposta.content:
                if hasattr(bloc, "text"):
                    respuesta_text += bloc.text
            messages.append({"role": "assistant", "content": resposta.content})
            break

    return {
        "respuesta": respuesta_text,
        "terminado": terminado,
        "ruta_docx": ruta_docx,
        "estado": {
            "llm_messages": messages,
            "estados":       estados,
            "bloque_actual": bloque_actual,
        },
    }


def iniciar_agente():
    """Arranca el bucle conversacional en la consola."""
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    messages = []                          # historial completo de la conversación
    estados = {b["nombre"]: b["crear_estado"]() for b in BLOQUES}
    estado         = estados["calendario"]
    estado_franjas = estados["franjas"]
    estado_orden   = estados["orden"]
    bloque_actual = "tipo_curso"             # empieza por el tipo de curso

    print("Hola, soy el asistente CAP. Escribe 'salir' para terminar.\n")

    while True:
        entrada = input("Tú: ").strip()

        if entrada.lower() == "salir":
            print("¡Hasta pronto, Rosa!")
            break

        if not entrada:
            continue

        messages.append({"role": "user", "content": entrada})

        # Bucle interno: continúa mientras el modelo quiera usar herramientas
        _tools_cached = _HERRAMIENTAS[:-1] + [{**_HERRAMIENTAS[-1], "cache_control": {"type": "ephemeral"}}]
        while True:
            system_blocks = [
                {"type": "text", "text": SYSTEM_PROMPT,
                 "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": _construir_contexto_estado(bloque_actual, estados)},
            ]

            respuesta = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system_blocks,
                tools=_tools_cached,
                messages=messages
            )
            u = respuesta.usage
            cache_write = getattr(u, "cache_creation_input_tokens", 0) or 0
            cache_read  = getattr(u, "cache_read_input_tokens",     0) or 0
            print(
                f"[TOKENS] bloc={bloque_actual}"
                f" input={u.input_tokens} output={u.output_tokens}"
                f" cache_write={cache_write} cache_read={cache_read}"
                f" stop={respuesta.stop_reason}"
            )

            if respuesta.stop_reason == "tool_use":
                # Añadimos la respuesta del asistente al historial (incluye el bloque tool_use)
                messages.append({"role": "assistant", "content": respuesta.content})

                # Ejecutamos cada herramienta solicitada y recogemos los resultados
                resultados = []
                for bloque in respuesta.content:
                    if bloque.type == "tool_use":
                        resultado = _ejecutar_herramienta(bloque.name, bloque.input, estados, bloque_actual)
                        resultados.append({
                            "type": "tool_result",
                            "tool_use_id": bloque.id,
                            "content": json.dumps(resultado, ensure_ascii=False, cls=_DecimalEncoder)
                        })

                # Devolvemos los resultados al modelo como mensaje de usuario
                messages.append({"role": "user", "content": resultados})

                # Transició de bloc: si l'actual s'ha completat, avança al següent saltant
                # els blocs condicionals que no apliquen; si s'exhaureixen, genera l'horari
                bloque_actual_def = next(b for b in BLOQUES if b["nombre"] == bloque_actual)
                if bloque_actual_def["bloque_completo"](estados[bloque_actual]):
                    idx = BLOQUES.index(bloque_actual_def)
                    siguiente_idx = idx + 1
                    while siguiente_idx < len(BLOQUES):
                        bloque_sig = BLOQUES[siguiente_idx]
                        condicion  = bloque_sig.get("condicion")
                        # Salta blocs que no apliquen (condició falsa) o que ja estan complets
                        if condicion is not None and not condicion(estados):
                            siguiente_idx += 1
                            continue
                        if bloque_sig["bloque_completo"](estados[bloque_sig["nombre"]]):
                            siguiente_idx += 1
                            continue
                        break
                    if siguiente_idx < len(BLOQUES):
                        bloque_actual = BLOQUES[siguiente_idx]["nombre"]
                    else:
                        pf_estado = estados["prueba_fuego"]
                        pf = None
                        if (estados["tipo_curso"]["tipo_curso"] == "mercancias" and
                                pf_estado["fecha"] is not None):
                            pf = crear_prueba_fuego(
                                pf_estado["fecha"],
                                pf_estado["hora_inicio"],
                                pf_estado["proveedor"],
                            )
                        resultado = generar_horario(
                            estado, estado_franjas, estado_orden,
                            tipo_curso=estados["tipo_curso"]["tipo_curso"],
                            prueba_fuego=pf,
                        )
                        _imprimir_horario(resultado["horario"])
                        if resultado["pendientes"]:
                            codigos = ", ".join(resultado["pendientes"])
                            print(
                                f"\n⚠ ATENCIÓ: l'horari està INCOMPLET. "
                                f"Les matèries {codigos} no han pogut col·locar-se perquè "
                                f"no hi ha prou dies lectius entre la data d'inici i el dia groc. "
                                f"Per solucionar-ho, avança la data d'inici del curs o "
                                f"amplia el rang de dates."
                            )
                        horari_amb_professors = aplicar_profesores(
                            resultado["horario"], estados["profesores"]
                        )
                        ruta = generar_document(
                            horari_amb_professors,
                            str(_BASE / "output_cap.docx"),
                            estado_alumnos=estados["alumnos"],
                            estado_practicas=estados["practicas"],
                            estado_calendario=estados["calendario"],
                            estado_franjas=estados["franjas"],
                            tipo_curso=estados["tipo_curso"]["tipo_curso"],
                        )
                        print(f"\nDocument generat: {ruta}")
                        print("Aquí tens l'horari generat. Fins aviat, Rosa!")
                        return

            else:
                # stop_reason == "end_turn": el modelo ha terminado, mostramos la respuesta
                for bloque in respuesta.content:
                    if hasattr(bloque, "text"):
                        print(f"\nAsistente: {bloque.text}\n")

                messages.append({"role": "assistant", "content": respuesta.content})
                break  # Salimos del bucle interno y esperamos el siguiente input de Rosa


if __name__ == "__main__":
    iniciar_agente()
