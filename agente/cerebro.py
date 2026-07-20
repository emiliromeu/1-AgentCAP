# Bucle principal del agente: recibe el mensaje de la usuaria, decide qué herramienta llamar y devuelve la respuesta.

import re
import json
from decimal import Decimal
from datetime import date, time, datetime, timedelta
from pathlib import Path
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
    elegir_dias as elegir_dias_franjas,
    fijar_dias_todos as fijar_dias_todos_franjas,
    grupo_activo as grupo_activo_franjas,
    OPCIONES_DIAS,
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
    bloque_completo as bloque_completo_practicas,
)
from agente.recogida_tipo_curso import (
    crear_estado as crear_estado_tipo_curso,
    guardar_tipo_curso as guardar_tipo_curso_tc,
    bloque_completo as bloque_completo_tipo_curso,
    clau_curs,
)
from agente.recogida_prueba_fuego import (
    crear_estado as crear_estado_prueba_fuego,
    bloque_completo as bloque_completo_prueba_fuego,
)
from agente.recogida_ajustar_inicio import (
    crear_estado as crear_estado_ajustar_inicio,
    marcar_resuelto as marcar_resuelto_ajustar_inicio,
    incrementar_intentos as incrementar_intentos_ajustar_inicio,
    bloque_completo as bloque_completo_ajustar_inicio,
    LIMITE_INTENTOS as LIMITE_INTENTOS_AJUSTAR_INICIO,
)
from herramientas.motor_prueba_fuego import crear_prueba_fuego
from herramientas.motor_horario import construir_franjas_semanales, horas_clase_de_dia
from datos.orden_asignaturas import ORDEN_HABITUAL_MERCANCIAS
from ensamblaje import generar_horario, aplicar_profesores, horas_totales_plantilla, horas_colocadas
from generar_documento import generar_document
from herramientas.horarios import validar_horario
from herramientas.validar_dni import validar_documento
from herramientas.calendario import (
    parsear_fecha,
    proponer_fecha_inicio,
    validar_inicio_antes_amarillo,
    validar_inicio_no_domingo,
    validar_verde_despues_amarillo,
    validar_limite_posterior_a_inicio,
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
        "Guarda el curso CAP que Rosa ha elegido, con sus DOS ejes: "
        "el tipo de formación ('inicial' de 130h o 'continu' de 35h) y la "
        "modalidad ('mercancias' o 'viatgers'). Llámala cuando Rosa haya "
        "indicado claramente AMBAS cosas. La ampliación no es un tipo de "
        "curso propio: es un tipo de alumno dentro del inicial."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tipo_curso": {
                "type": "string",
                "enum": ["mercancias", "viatgers"],
                "description": "Modalidad: 'mercancias' o 'viatgers'."
            },
            "tipo_formacio": {
                "type": "string",
                "enum": ["inicial", "continu"],
                "description": (
                    "Tipo de formación: 'inicial' (130 horas) o "
                    "'continu' (formació contínua, 35 horas)."
                )
            }
        },
        "required": ["tipo_curso", "tipo_formacio"]
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

HERRAMIENTA_AJUSTAR_FECHA_INICIO = {
    "name": "ajustar_fecha_inicio",
    "description": (
        "Aplica una nueva fecha de inicio (más temprana que la actual) y los "
        "festivos del nuevo tramo añadido, para intentar cubrir las horas que "
        "faltan para completar el curso. Llámala SOLO cuando tengas AMBOS datos: "
        "la fecha que Rosa haya confirmado (la propuesta u otra) Y su respuesta "
        "sobre festivos en el nuevo tramo (aunque sea 'ninguno' -> lista vacía). "
        "No la llames con uno solo de los dos datos."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nueva_fecha_inicio": {
                "type": "string",
                "description": "Nueva fecha de inicio del curso, formato DD/MM/AAAA."
            },
            "festivos_nuevos": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Festivos en el tramo NUEVO añadido (entre la nueva fecha y la "
                    "fecha de inicio anterior), formato DD/MM/AAAA. Lista vacía si "
                    "Rosa dice que no hay ninguno."
                )
            }
        },
        "required": ["nueva_fecha_inicio", "festivos_nuevos"]
    }
}

HERRAMIENTA_ELEGIR_DIAS_SEMANA = {
    "name": "elegir_dias_semana",
    "description": (
        "Guarda la opción de días de la semana que Rosa ha elegido para el "
        "CAP CONTINUO (solo existe en el continuo; el inicial siempre es de "
        "lunes a sábado y NO usa esta herramienta). Llámala cuando Rosa haya "
        "elegido una de las 6 opciones del menú."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "opcion": {
                "type": "integer",
                "enum": [1, 2, 3, 4, 5, 6],
                "description": (
                    "Opción elegida: 1=lunes a jueves, 2=lunes a viernes, "
                    "3=lunes a jueves y sábado, 4=viernes y sábados, "
                    "5=lunes a sábado, 6=solo sábados."
                )
            }
        },
        "required": ["opcion"]
    }
}


_HERRAMIENTAS = [
    HERRAMIENTA_GUARDAR_TIPO_CURSO, HERRAMIENTA_VALIDAR_FECHA,
    HERRAMIENTA_PROPONER_INICIO, HERRAMIENTA_VALIDAR_HORARIO, HERRAMIENTA_CONFIRMAR_DATO,
    HERRAMIENTA_VALIDAR_DNI, HERRAMIENTA_ANADIR_ALUMNO, HERRAMIENTA_TERMINAR_ALUMNOS,
    HERRAMIENTA_MARCAR_PROFESOR_GENERAL, HERRAMIENTA_ANADIR_EXCEPCION_PROFESOR,
    HERRAMIENTA_TERMINAR_PROFESORES, HERRAMIENTA_GUARDAR_PROFESOR_PRACTICAS,
    HERRAMIENTA_GUARDAR_PRUEBA_FUEGO, HERRAMIENTA_AJUSTAR_FECHA_INICIO,
    HERRAMIENTA_ELEGIR_DIAS_SEMANA,
]

# Tools de validación pura (sin efectos secundarios): siempre disponibles, en cualquier bloque.
_VALIDACIONES_GLOBALES = {"validar_fecha", "validar_dni", "validar_horario", "proponer_inicio"}

# Qué tools (con efectos) pertenecen a cada bloque. Se usa para enviar al LLM SOLO las
# relevantes al bloque activo — así no puede ni intentar actuar sobre un bloque que no toca
# todavía (refuerza al guard _fuera_de_turno con una barrera estructural, no solo de rechazo).
_TOOLS_POR_BLOQUE = {
    "tipo_curso":     {"guardar_tipo_curso"},
    "calendario":     {"confirmar_dato"},
    "prueba_fuego":   {"guardar_prueba_fuego"},
    "franjas":        {"confirmar_dato", "elegir_dias_semana"},
    "ajustar_inicio": {"ajustar_fecha_inicio"},
    "orden":          {"confirmar_dato"},
    "alumnos":        {"anadir_alumno", "terminar_alumnos"},
    "profesores":     {"marcar_profesor_general", "anadir_excepcion_profesor", "terminar_profesores"},
    "practicas":      {"guardar_profesor_practicas"},
}


def _herramientas_para_bloque(bloque_actual):
    """
    Devuelve solo las tools relevantes para bloque_actual (+ las de validación pura).
    La última lleva cache_control para que Anthropic cachee el bloque de tools.
    """
    nombres = _VALIDACIONES_GLOBALES | _TOOLS_POR_BLOQUE.get(bloque_actual, set())
    seleccionadas = [h for h in _HERRAMIENTAS if h["name"] in nombres]
    return seleccionadas[:-1] + [{**seleccionadas[-1], "cache_control": {"type": "ephemeral"}}]

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


# Etiquetas del continuo (fecha límite en vez de día amarillo; sin día verde).
_NOMBRES_LEGIBLES_CONTINU = {
    "fecha_inicio": "día de inicio del curso",
    "dia_amarillo": "fecha límite (último día permitido para acabar el curso)",
    "festivos":     "festivos del período",
}


def _instr_inicio_continuo():
    """Continuo: Rosa ELIGE el día de inicio (sin cálculo ni proponer_inicio)."""
    return "\n".join([
        "Pregúntale a Rosa qué día quiere EMPEZAR el curso. Ella lo elige libremente.",
        "NO uses proponer_inicio ni calcules nada: en el continuo la fecha de inicio la decide Rosa.",
        "Cuando te dé la fecha, valídala con validar_fecha (solo comprueba que sea una fecha real).",
        "Si es válida, repítesela para confirmar ('¿Empezamos el DD/MM/AAAA, correcto?').",
        "Cuando Rosa confirme, llama a confirmar_dato con nombre_dato='fecha_inicio' y la fecha.",
    ])


def _instr_fecha_limite_continuo(estado):
    """Continuo: Rosa da la fecha límite (tope). Se guarda en dia_amarillo."""
    inicio = estado["fecha_inicio"]["valor"]
    return "\n".join([
        "Pregúntale a Rosa la FECHA LÍMITE: el último día permitido para tener el curso acabado.",
        f"Tiene que ser POSTERIOR al día de inicio ({inicio}).",
        "Cuando te dé la fecha, valídala con validar_fecha; repítela para confirmar; y con "
        "confirmar_dato guarda nombre_dato='dia_amarillo' con esa fecha "
        "(es el tope que usa el sistema para comprobar si caben las horas).",
        "Si el sistema la rechaza por no ser posterior al inicio, explícaselo a Rosa y pídele otra.",
    ])


def _contexto_calendario(estados):
    """Genera la parte variable del system prompt para el bloque calendario.

    Ramifica según tipo_formacio (recibe TODOS los estados, ver _construir_contexto_estado):
      - inicial: día amarillo → día verde (examen) → fecha inicio (calculada) → festivos.
      - continuo: día de inicio (Rosa elige) → fecha límite → festivos. Sin día verde
                  (pre-marcado N/A al guardar el tipo)."""
    estado   = estados["calendario"]
    continuo = estados["tipo_curso"]["tipo_formacio"] == "continu"

    if continuo:
        orden    = ["fecha_inicio", "dia_amarillo", "festivos"]
        etiquetas = _NOMBRES_LEGIBLES_CONTINU
    else:
        orden    = ["dia_amarillo", "dia_verde", "fecha_inicio", "festivos"]
        etiquetas = _NOMBRES_LEGIBLES

    lineas = ["ESTADO DE LA RECOGIDA DEL BLOQUE CALENDARIO:"]
    for nombre in orden:
        entrada = estado[nombre]
        if entrada["conseguido"]:
            lineas.append(f"  - {etiquetas[nombre]}: YA CONSEGUIDO → {entrada['valor']}")
        else:
            lineas.append(f"  - {etiquetas[nombre]}: pendiente")

    siguiente = next((n for n in orden if not estado[n]["conseguido"]), None)
    if siguiente is None:
        lineas.append("\nTodos los datos del bloque calendario están conseguidos.")
        return "\n".join(lineas)

    lineas.append(f"\nAHORA TE TOCA: conseguir el {etiquetas[siguiente]}.")
    if continuo:
        if siguiente == "fecha_inicio":
            lineas.append(_instr_inicio_continuo())
        elif siguiente == "dia_amarillo":
            lineas.append(_instr_fecha_limite_continuo(estado))
        else:  # festivos (reutiliza el helper: usa fecha_inicio y dia_amarillo=límite)
            lineas.append(_instrucciones_festivos(estado))
    else:
        if siguiente == "fecha_inicio":
            lineas.append(_instrucciones_fecha_inicio(estado))
        elif siguiente == "festivos":
            lineas.append(_instrucciones_festivos(estado))
        elif siguiente == "dia_verde":
            lineas.append(_instrucciones_dia_verde(estado))
        else:
            lineas.append(_instrucciones_genericas(siguiente))

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
    """Genera la parte variable del system prompt para el bloque franjas horarias.

    FASE 3b: si la opción de días está pendiente (solo pasa en el CAP continuo
    — en el inicial se fija sola a lunes-sábado), lo primero es el menú de las
    6 opciones. Después, los horarios: solo los de los grupos de días activos
    (los excluidos figuran como NO APLICA y no se preguntan)."""
    dias_sem = estado_franjas.get("dias_semana", {"conseguido": True, "valor": None})

    # Paso previo (solo continuo): elegir la opción de días
    if not dias_sem["conseguido"]:
        lineas = [
            "ESTADO: pendiente de elegir los DÍAS DE LA SEMANA del curso continuo.",
            "",
            "AHORA TE TOCA: preguntar a Rosa qué días de la semana tendrá clase",
            "este curso. Muéstrale este menú (numerado, tal cual):",
            "",
        ]
        for n, conf in OPCIONES_DIAS.items():
            lineas.append(f"  {n}. {conf['etiqueta']}")
        lineas += [
            "",
            "Cuando Rosa elija una opción (por número o describiéndola), llama a",
            "elegir_dias_semana con el número de la opción (1-6).",
            "Después se pedirán SOLO los horarios de los días incluidos en la opción.",
        ]
        return "\n".join(lineas)

    lineas = ["ESTADO DE LA RECOGIDA DE LOS HORARIOS:"]
    if dias_sem["valor"]:
        opc = dias_sem["valor"]["opcion"]
        lineas.insert(0, f"DÍAS DEL CURSO: opción {opc} — {OPCIONES_DIAS[opc]['etiqueta']}.\n")

    for nombre in ["horario_lun_jue", "horario_viernes", "horario_sabado"]:
        etiqueta = _NOMBRES_LEGIBLES_FRANJAS[nombre]
        entrada = estado_franjas[nombre]
        if entrada["conseguido"]:
            v = entrada["valor"]
            if v is None:
                lineas.append(f"  - {etiqueta}: NO APLICA (esos días no tienen clase en este curso)")
            elif isinstance(v, dict) and "inicio" in v and "fin" in v:
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
            "(El bloque de ALUMNOS ya se completó antes de este — no vuelvas a preguntar "
            "por alumnos. Ahora toca exclusivamente los PROFESORES.)",
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
def _validar_fecha_inicio_calendario(valor, est):
    """Fecha de inicio: primero que no sea domingo, luego que sea anterior al día amarillo."""
    r_domingo = validar_inicio_no_domingo(valor)
    if not r_domingo["coherente"]:
        return r_domingo
    return validar_inicio_antes_amarillo(valor, est["dia_amarillo"]["valor"])


# Cada entrada: nombre_dato → función que recibe (valor_nuevo, estado) y devuelve
# el resultado de la comprobación de coherencia (dict con 'coherente' y 'mensaje').
# Los datos ausentes (dia_amarillo, festivos) no tienen comprobación: se marcan sin más.
_COMPROBACIONES_COHERENCIA = {
    "dia_verde": lambda valor, est: validar_verde_despues_amarillo(
        valor, est["dia_amarillo"]["valor"]
    ),
    "fecha_inicio": _validar_fecha_inicio_calendario,
}


def _verificar_coherencia(nombre_dato, valor, estados):
    """
    Devuelve el resultado de coherencia si el dato tiene comprobación, None si no aplica.

    Ramifica según tipo_formacio, porque en el continuo el ORDEN de recogida es
    distinto (inicio primero, luego fecha límite):
      - continuo: fecha_inicio → solo que no sea domingo (aún no hay tope que comparar);
                  dia_amarillo (fecha límite) → posterior al día de inicio.
      - inicial : como siempre (dia_verde > amarillo; fecha_inicio no-domingo y < amarillo).
    """
    if estados["tipo_curso"]["tipo_formacio"] == "continu":
        if nombre_dato == "fecha_inicio":
            return validar_inicio_no_domingo(valor)
        if nombre_dato == "dia_amarillo":
            return validar_limite_posterior_a_inicio(
                valor, estados["calendario"]["fecha_inicio"]["valor"]
            )
        return None

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
            "QUÉ ES LA PRUEBA DE FUEGO (para que no la confundas con otra cosa):",
            "La Prueba de Fuego es un EXAMEN puntual — una única sesión de evaluación de 2h",
            "de MM.PP con un proveedor externo (FAST PARCMOTOR), en UN sábado concreto del",
            "curso, a UNA hora concreta de inicio.",
            "",
            "*** NO ES el horario semanal de las clases (eso son las 'franjas horarias' —",
            "un bloque DISTINTO y POSTERIOR, con horas que se repiten cada semana, p.ej.",
            "'de 18:00 a 21:15 lunes a jueves'). NO preguntes '¿a qué hora empiezan y",
            "terminan las clases?' — esa pregunta es de franjas, no de aquí. ***",
            "",
            "AHORA TE TOCA: recoger los dos datos de la Prueba de Fuego (el EXAMEN).",
            "Pregunta a Rosa, con estas palabras o muy parecidas:",
            "  1. '¿Qué día (sábado) es la prueba de fuego (el examen)?'",
            "     Debe ser un sábado dentro del rango del curso.",
            "  2. '¿A qué hora empieza la prueba de fuego (el examen)?' (p.ej. 10:00)",
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
                "Esto es la hora de INICIO del EXAMEN de ese día concreto — NO el horario",
                "semanal de las clases (eso es franjas, y viene después).",
                f"Pregunta a Rosa: '¿A qué hora empieza la prueba de fuego (el examen) del "
                f"{fecha.strftime('%d/%m/%Y')}?' (p.ej. 10:00)",
                "Cuando te la dé, llama a guardar_prueba_fuego SOLO con hora_inicio (HH:MM) —",
                "no hace falta que repitas la fecha, ya está guardada.",
            ])
        )

    return "\n".join(lineas)


def _contexto_tipo_curso(estado_tipo_curso):
    """Genera la parte variable del system prompt para el bloque tipo de curso.

    Dos ejes: tipo_formacio (inicial 130h / continu 35h) + modalitat
    (mercancies / viatgers). La tool los guarda juntos en una llamada."""
    tipo_formacio = estado_tipo_curso["tipo_formacio"]
    modalitat     = estado_tipo_curso["modalitat"]
    terminado     = estado_tipo_curso["terminado"]

    if terminado:
        etiq_form = "CONTINU 35h" if tipo_formacio == "continu" else "INICIAL 130h"
        etiq_mod  = "MERCANCIES" if modalitat == "mercancies" else "VIATGERS"
        return f"TIPUS DE CURS: COMPLETAT ({etiq_form} de {etiq_mod})."

    if modalitat is None or tipo_formacio is None:
        return (
            "ESTADO: pendiente de elegir el curso.\n"
            "\n"
            "AHORA TE TOCA: preguntar a Rosa qué curso CAP va a preparar. Son DOS\n"
            "datos (puedes preguntarlos juntos o por separado, como fluya):\n"
            "\n"
            "  1. TIPO DE FORMACIÓN:\n"
            "     · INICIAL: Qualificació Inicial, 130 horas (el de siempre)\n"
            "     · CONTINU: Formació Contínua, 35 horas\n"
            "     (Si Rosa menciona 'ampliación': NO es un curso propio, es un tipo\n"
            "      de alumno dentro del inicial — acláraselo y sigue con estos dos.)\n"
            "\n"
            "  2. MODALIDAD:\n"
            "     · MERCANCIES: transport de Mercaderies\n"
            "     · VIATGERS:   transport de Viatgers\n"
            "\n"
            "Cuando tengas AMBOS datos claros, llama a guardar_tipo_curso con\n"
            "tipo_formacio ('inicial' o 'continu') y tipo_curso ('mercancias' o 'viatgers')."
        )

    return f"TIPUS DE CURS: {tipo_formacio} de {modalitat} (pendent de confirmar)."


def _contexto_ajustar_inicio(estados):
    """
    Genera la parte variable del system prompt para el bloque "ajustar_inicio".

    A diferencia de los demás _contexto_*, recibe TODOS los estados (ver el
    caso especial en _construir_contexto_estado) porque necesita calendario +
    franjas + orden + prueba_fuego para calcular cuántas horas faltan y
    proponer una fecha.

    CLAVE: el cálculo (horas que faltan, fecha propuesta) se hace AQUÍ, dentro
    de esta función, ANTES de construir el texto — nunca al revés. El LLM NO
    calcula nada: solo comunica a Rosa los valores que este bloque ya calculó.
    Como se recalcula de cero en cada llamada (sin caché), cada vuelta del
    bucle de reintentos ve automáticamente la fecha/horas ya actualizadas.
    """
    estado_aj       = estados["ajustar_inicio"]
    fecha_actual    = estados["calendario"]["fecha_inicio"]["valor"]
    horas_faltantes = _calcular_horas_faltantes(estados)
    nueva_fecha, dias_necesarios = _proponer_nueva_fecha_inicio(estados, horas_faltantes)
    nueva_fecha_str = nueva_fecha.strftime("%d/%m/%Y")

    frase_ejemplo = (
        f"«Con estas fechas faltan {horas_faltantes:.1f} horas. Propongo adelantar el "
        f"inicio al {nueva_fecha_str}. ¿Te va bien, o prefieres otra fecha? ¿Hay festivos "
        f"entre el {nueva_fecha_str} y el {fecha_actual}?»"
    )

    return "\n".join([
        "=== BLOQUE ACTUAL: AJUSTAR FECHA DE INICIO (faltan horas para completar el curso) ===",
        "",
        "*** ESTE ES EL PASO ACTUAL. NO preguntes por alumnos, profesores, prácticas ni nada",
        f"más. Tu única tarea ahora: proponle a Rosa la fecha {nueva_fecha_str} y esperar su",
        "respuesta. No avances a ningún otro tema hasta que esto quede resuelto. ***",
        "",
        "El SISTEMA (no tú) ya ha calculado estos datos — no tienes que calcular nada:",
        f"  - Horas que faltan para completar el curso (130h): {horas_faltantes:.1f}h",
        f"  - Fecha de inicio actual: {fecha_actual}",
        f"  - NUEVA fecha de inicio propuesta: {nueva_fecha_str} "
        f"({dias_necesarios} días lectivos más, adelantando el inicio, más 1 día "
        "laborable de margen para que Rosa no vaya justa).",
        f"  - Intentos de ajuste hasta ahora: {estado_aj['intentos']} de {LIMITE_INTENTOS_AJUSTAR_INICIO}.",
        "",
        "*** TÚ NO CALCULAS NADA. Estos valores ya están calculados por el sistema — tu único",
        "trabajo es comunicárselos a Rosa, con tus propias palabras o muy parecidas a estas: ***",
        f"  {frase_ejemplo}",
        "",
        "AHORA TE TOCA:",
        "1. Dile a Rosa la frase de arriba (con tu propio tono, cercano y sin tecnicismos).",
        "2. Espera su respuesta: qué fecha confirma (la propuesta u otra) y si hay festivos "
        "en el tramo nuevo (aunque sea 'ninguno').",
        "3. Solo cuando tengas AMBOS datos (fecha + festivos, aunque sea lista vacía), llama "
        "a ajustar_fecha_inicio con nueva_fecha_inicio y festivos_nuevos.",
        "4. Si el sistema te devuelve que TODAVÍA faltan horas, aquí mismo (en el próximo turno) "
        "verás la nueva propuesta ya recalculada — coméntasela a Rosa igual que antes, y repite "
        "desde el paso 1.",
        "5. Si el sistema te indica que se ha llegado al límite de intentos, dile a Rosa "
        "exactamente lo que te indique el mensaje del sistema — no sigas insistiendo con más "
        "propuestas por tu cuenta.",
    ])


def _te_prueba_fuego(estados):
    """FASE 1 (dos ejes): la prueba de fuego es SOLO del inicial de
    mercancías. Hoy equivale exactamente a la condición histórica
    (tipo_curso == "mercancias", porque solo existe el inicial) y deja
    preparado que ampliacio/continu de mercancías NO la tengan. Único
    sitio del código que define esta regla."""
    return (
        estados["tipo_curso"]["tipo_formacio"] == "inicial"
        and estados["tipo_curso"]["modalitat"] == "mercancies"
    )


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
        "condicion":         _te_prueba_fuego,
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
        "nombre":            "ajustar_inicio",
        "crear_estado":      crear_estado_ajustar_inicio,
        "bloque_completo":   bloque_completo_ajustar_inicio,
        "marcar_conseguido": None,
        "contexto":          _contexto_ajustar_inicio,
        "validacion":        None,
        # Solo se activa si, con calendario+franjas ya dados, NO dan las horas
        # para completar el curso (130h). Si dan, se salta y Rosa nunca lo ve.
        "condicion":         lambda estados: _calcular_horas_faltantes(estados) > 0.01,
    },
    {
        "nombre":            "orden",
        "crear_estado":      crear_estado_orden,
        "bloque_completo":   bloque_completo_orden,
        "marcar_conseguido": marcar_conseguido_orden,
        "contexto":          _contexto_orden,
        "validacion":        None,
        # El continuo no confirma orden de asignaturas (su plantilla ya lo fija).
        "condicion":         lambda estados: estados["tipo_curso"]["tipo_formacio"] != "continu",
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
        # El continuo no tiene prácticas aparte (van incluidas en las asignaturas):
        # al saltarse este bloque, tras profesores se genera el documento directamente.
        "condicion":         lambda estados: estados["tipo_curso"]["tipo_formacio"] != "continu",
    },
]


def _construir_contexto_estado(bloque_actual, estados):
    """Elige el constructor de contexto según el bloque que está en curso."""
    # Caso especial: "ajustar_inicio" y "calendario" reciben TODOS los estados
    # (no solo su porción). ajustar_inicio los necesita para calcular horas que
    # faltan; calendario para ramificar según tipo_formacio (inicial vs continuo).
    # Los otros bloques siguen recibiendo solo su propia porción, sin cambios.
    if bloque_actual == "ajustar_inicio":
        return _contexto_ajustar_inicio(estados)
    if bloque_actual == "calendario":
        return _contexto_calendario(estados)
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
        tipo          = argumentos["tipo_curso"]
        # Sesiones antiguas pueden llamar sin tipo_formacio: el histórico era inicial.
        tipo_formacio = argumentos.get("tipo_formacio", "inicial")
        guardado = guardar_tipo_curso_tc(estados["tipo_curso"], tipo, tipo_formacio)
        if guardado:
            # FASE 3b: el paso de días de la semana solo existe en el continuo.
            # En el inicial se fija aquí a lunes-sábado (comportamiento
            # histórico) y Rosa nunca ve el menú de opciones.
            if tipo_formacio != "continu":
                fijar_dias_todos_franjas(estados["franjas"])
            else:
                # El continuo NO tiene examen: el día verde se pre-marca N/A para
                # que el bloque calendario no lo pregunte y se complete sin él.
                estados["calendario"]["dia_verde"] = {"conseguido": True, "valor": None}
            return {"tipo_guardado": True, "tipo": tipo, "tipo_formacio": tipo_formacio}
        if tipo_formacio == "ampliacio":
            return {"tipo_guardado": False, "motivo": (
                "L'ampliació no és un tipus de curs propi: és un tipus d'alumne "
                "dins del curs inicial. Tria 'inicial' o 'continu'."
            )}
        return {"tipo_guardado": False, "motivo": (
            f"Combinació no vàlida: {tipo_formacio!r} + {tipo!r}. "
            "tipo_formacio: 'inicial' o 'continu'; tipo_curso: 'mercancias' o 'viatgers'."
        )}
    if nombre == "elegir_dias_semana":
        motivo = _fuera_de_turno("franjas", bloque_actual)
        if motivo:
            return {"dias_guardados": False, "motivo": motivo}
        if estados["tipo_curso"]["tipo_formacio"] != "continu":
            return {"dias_guardados": False, "motivo": (
                "La opció de dies només existeix al CAP CONTINU. Aquest curs és "
                "inicial: sempre va de dilluns a dissabte, no cal triar res."
            )}
        opcion = argumentos["opcion"]
        if not elegir_dias_franjas(estados["franjas"], opcion):
            return {"dias_guardados": False, "motivo": f"Opció no vàlida: {opcion!r}. Usa 1-6."}
        conf = OPCIONES_DIAS[opcion]
        return {
            "dias_guardados": True,
            "opcion": opcion,
            "etiqueta": conf["etiqueta"],
            "dias": conf["dias"],
        }

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
        if nombre_dato == "dias_semana":
            return {
                "guardado": False,
                "nombre_dato": nombre_dato,
                "motivo": (
                    "La opció de dies no es confirma amb confirmar_dato: "
                    "usa la herramienta elegir_dias_semana amb l'opció 1-6."
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

    if nombre == "ajustar_fecha_inicio":
        print(f"[DEBUG-AJUSTE] ajustar_fecha_inicio LLAMADA: argumentos={argumentos} bloque_actual={bloque_actual!r}")
        motivo = _fuera_de_turno("ajustar_inicio", bloque_actual)
        if motivo:
            print(f"[DEBUG-AJUSTE] RECHAZADA por fuera de turno: {motivo}")
            return {"aplicado": False, "motivo": motivo}

        nueva_fecha_str = argumentos["nueva_fecha_inicio"]
        festivos_nuevos = argumentos["festivos_nuevos"]
        estado_aj       = estados["ajustar_inicio"]

        r_fecha = parsear_fecha(nueva_fecha_str)
        if not r_fecha["valida"]:
            print(f"[DEBUG-AJUSTE] RECHAZADA por fecha inválida: {r_fecha['mensaje']}")
            return {"aplicado": False, "motivo": r_fecha["mensaje"]}

        for f in festivos_nuevos:
            r_f = parsear_fecha(f)
            if not r_f["valida"]:
                print(f"[DEBUG-AJUSTE] RECHAZADA por festivo inválido: {f!r} -> {r_f['mensaje']}")
                return {"aplicado": False, "motivo": f"El festivo '{f}' no es una fecha válida: {r_f['mensaje']}"}

        r_domingo = validar_inicio_no_domingo(nueva_fecha_str)
        if not r_domingo["coherente"]:
            print(f"[DEBUG-AJUSTE] RECHAZADA por domingo: {r_domingo['mensaje']}")
            return {"aplicado": False, "motivo": r_domingo["mensaje"]}

        resultado_val = validar_inicio_antes_amarillo(
            nueva_fecha_str, estados["calendario"]["dia_amarillo"]["valor"]
        )
        if not resultado_val["coherente"]:
            print(f"[DEBUG-AJUSTE] RECHAZADA por incoherente con día amarillo: {resultado_val['mensaje']}")
            return {"aplicado": False, "motivo": resultado_val["mensaje"]}

        # ── Aplicar: nueva fecha de inicio + unión de festivos (nunca se pierden los anteriores)
        estados["calendario"]["fecha_inicio"]["valor"] = nueva_fecha_str
        festivos_actuales = set(estados["calendario"]["festivos"]["valor"])
        estados["calendario"]["festivos"]["valor"] = sorted(festivos_actuales | set(festivos_nuevos))
        incrementar_intentos_ajustar_inicio(estado_aj)

        horas_faltantes = _calcular_horas_faltantes(estados)
        print(
            f"[DEBUG-AJUSTE] aplicado: nueva_fecha={nueva_fecha_str} festivos_nuevos={festivos_nuevos} "
            f"intentos={estado_aj['intentos']} horas_faltantes={horas_faltantes}"
        )

        if horas_faltantes <= 0.01:
            marcar_resuelto_ajustar_inicio(estado_aj)
            print("[DEBUG-AJUSTE] RESUELTO: las horas ya dan.")
            return {"aplicado": True, "horas_suficientes": True}

        if estado_aj["intentos"] >= LIMITE_INTENTOS_AJUSTAR_INICIO:
            marcar_resuelto_ajustar_inicio(estado_aj)  # desbloqueamos igualmente, con aviso
            print(f"[DEBUG-AJUSTE] LÍMITE de {LIMITE_INTENTOS_AJUSTAR_INICIO} intentos alcanzado, se desbloquea con aviso.")
            return {
                "aplicado":           True,
                "horas_suficientes":  False,
                "horas_faltantes":    horas_faltantes,
                "limite_alcanzado":   True,
                "motivo": (
                    f"Tras {estado_aj['intentos']} intentos, todavía faltan {horas_faltantes:.1f}h. "
                    "Dile a Rosa que revise las fechas con calma (por ejemplo, dando de una vez "
                    "todos los festivos del periodo ampliado) fuera de esta conversación, o que "
                    "continúe si quiere — el sistema seguirá avisando si el horario queda incompleto."
                ),
            }

        nueva_propuesta, _dias = _proponer_nueva_fecha_inicio(estados, horas_faltantes)
        return {
            "aplicado":              True,
            "horas_suficientes":     False,
            "horas_faltantes":       horas_faltantes,
            "nueva_fecha_propuesta": nueva_propuesta.strftime("%d/%m/%Y"),
            "intentos":              estado_aj["intentos"],
        }

    return {"error": f"Herramienta desconocida: {nombre}"}


def crear_estado_conversacion():
    """Crea l'estat inicial per a una nova sessió (per a st.session_state)."""
    return {
        "llm_messages": [],
        "estados":       {b["nombre"]: b["crear_estado"]() for b in BLOQUES},
        "bloque_actual": "tipo_curso",
    }


def _calcular_horas_faltantes(estados):
    """
    Calcula cuántas horas faltan para completar el curso (130h), generando el
    horario con el calendario/franjas/orden/prueba_fuego actuales.

    Compartida por la Parte A (aviso final si el curso se generaría incompleto)
    y por el bloque "ajustar_inicio" de la Parte B (red de seguridad temprana,
    justo tras franjas). Requiere que calendario y franjas estén ya completos
    — ambos lo están siempre que se llame desde estos dos sitios.
    """
    # FASE 1 (dos ejes): la clave de configuración se deriva de
    # tipo_formacio+modalitat (clau_curs) — para el inicial es el string
    # histórico, así ensamblaje/generar_documento no cambian nada.
    tipo_curso = clau_curs(estados["tipo_curso"])
    pf_estat = estados["prueba_fuego"]
    pf = None
    if _te_prueba_fuego(estados) and pf_estat["fecha"] is not None:
        pf = crear_prueba_fuego(pf_estat["fecha"], pf_estat["hora_inicio"], pf_estat["proveedor"])
    resultat_h = generar_horario(
        estados["calendario"], estados["franjas"], estados["orden"],
        tipo_curso=tipo_curso, prueba_fuego=pf,
    )
    horas_totales = horas_totales_plantilla(tipo_curso)
    horas_puestas = horas_colocadas(resultat_h["horario"])
    return horas_totales - horas_puestas


def _proponer_nueva_fecha_inicio(estados, horas_faltantes):
    """
    Calcula una fecha de inicio más temprana que cubra las horas que faltan.

    Simula día a día HACIA ATRÁS (no un promedio) desde la fecha de inicio
    actual, sumando las horas netas reales de cada día según su franja
    (lunes-jueves, viernes y sábado dan horas distintas), saltando domingos y
    festivos ya conocidos, hasta acumular las horas que faltan. Después añade
    1 día LABORABLE (lunes-viernes) de margen, saltando fines de semana y
    festivos si el margen cae justo ahí.

    Devuelve (nueva_fecha: date, dias_lectivos_anadidos: int).
    """
    franjas = construir_franjas_semanales(estados["franjas"])
    horas_por_weekday = {}
    for wd in range(7):
        franja = franjas.get(wd)
        horas_por_weekday[wd] = horas_clase_de_dia(franja["inicio"], franja["fin"]) if franja else 0.0

    fecha_inicio_actual = parsear_fecha(estados["calendario"]["fecha_inicio"]["valor"])["fecha"]
    festivos_actuales = {
        parsear_fecha(f)["fecha"] for f in estados["calendario"]["festivos"]["valor"]
    }

    acumulado      = 0.0
    dias_contados  = 0
    cursor         = fecha_inicio_actual - timedelta(days=1)
    while acumulado < horas_faltantes:
        if cursor.weekday() != 6 and cursor not in festivos_actuales:
            h = horas_por_weekday.get(cursor.weekday(), 0.0)
            if h > 0:
                acumulado     += h
                dias_contados += 1
        cursor -= timedelta(days=1)
    nueva_fecha_sin_margen = cursor + timedelta(days=1)

    # Margen: 1 día laborable (lunes-viernes) más — salta sábado/domingo/festivo
    margen = nueva_fecha_sin_margen - timedelta(days=1)
    while margen.weekday() >= 5 or margen in festivos_actuales:  # 5=sábado, 6=domingo
        margen -= timedelta(days=1)

    # Red de seguridad extra: el curso nunca puede empezar en domingo. El bucle
    # de arriba ya lo evita (weekday() != 6 al contar días, weekday() >= 5 en el
    # margen), pero esta guarda deja la garantía explícita e inmune a cualquier
    # cambio futuro en la lógica de arriba.
    while margen.weekday() == 6:
        margen -= timedelta(days=1)

    return margen, dias_contados


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
    print(f"[DEBUG-AVANCE] bloque_actual={bloque_actual!r} completo -> buscando siguiente desde idx={siguiente_idx}")
    while siguiente_idx < len(BLOQUES):
        bloque_sig = BLOQUES[siguiente_idx]
        condicion  = bloque_sig.get("condicion")
        aplica     = condicion(estados) if condicion is not None else True
        completo   = bloque_sig["bloque_completo"](estados[bloque_sig["nombre"]])
        print(
            f"[DEBUG-AVANCE]   evaluando '{bloque_sig['nombre']}' (idx={siguiente_idx}): "
            f"tiene_condicion={condicion is not None} aplica={aplica} completo={completo} "
            f"-> {'SALTA (no aplica)' if condicion is not None and not aplica else ('SALTA (ya completo)' if completo else 'SE ELIGE ESTE')}"
        )
        # Salta blocs que no apliquen (condició falsa) o que ja estan complets
        if condicion is not None and not aplica:
            siguiente_idx += 1
            continue
        if completo:
            siguiente_idx += 1
            continue
        break
    print(f"[DEBUG-AVANCE] resultado: siguiente_idx={siguiente_idx} -> "
          f"{BLOQUES[siguiente_idx]['nombre'] if siguiente_idx < len(BLOQUES) else '(NINGUNO: genera documento)'}")

    if siguiente_idx < len(BLOQUES):
        return {
            "bloque_actual":  BLOQUES[siguiente_idx]["nombre"],
            "avanzo":         True,
            "terminado":      False,
            "ruta_docx":      None,
            "respuesta_text": None,
        }

    # ── Todos los bloques completos: generar el documento ──────────────────────
    # FASE 1 (dos ejes): clave de configuración derivada de tipo_formacio+
    # modalitat — para el inicial, el string histórico de siempre.
    tipo_curso = clau_curs(estados["tipo_curso"])

    # ── Red de seguridad final (Parte A): ¿dan las horas para completar el curso?
    # Si el bloque "ajustar_inicio" (Parte B) ya hizo su trabajo justo tras franjas,
    # esto no debería disparar nunca — se deja como último resguardo, por si acaso.
    horas_faltantes = _calcular_horas_faltantes(estados)
    print(f"[DEBUG-HORAS] tipo_curso={tipo_curso} horas_faltantes={horas_faltantes}")
    if horas_faltantes > 0.01:  # margen para redondeos de coma flotante
        mensaje_aviso = (
            "He revisado las fechas y con este calendario no dan las horas "
            f"suficientes para completar el curso — faltan {horas_faltantes:.1f} horas. "
            "Necesitamos ajustar las fechas para que quepa todo el temario."
        )
        return {
            "bloque_actual":       bloque_actual,
            "avanzo":              False,
            "terminado":           False,
            "ruta_docx":           None,
            "respuesta_text":      mensaje_aviso,
            "horas_insuficientes": True,
        }

    pf_estat = estados["prueba_fuego"]
    pf = None
    if _te_prueba_fuego(estados) and pf_estat["fecha"] is not None:
        pf = crear_prueba_fuego(
            pf_estat["fecha"], pf_estat["hora_inicio"], pf_estat["proveedor"],
        )
    resultat_h = generar_horario(
        estados["calendario"], estados["franjas"], estados["orden"],
        tipo_curso=tipo_curso,
        prueba_fuego=pf,
    )
    horari = aplicar_profesores(resultat_h["horario"], estados["profesores"])
    ruta_docx = generar_document(
        horari, str(_BASE / "output_cap.docx"),
        estado_alumnos=estados["alumnos"],
        estado_practicas=estados["practicas"],
        estado_calendario=estados["calendario"],
        estado_franjas=estados["franjas"],
        tipo_curso=tipo_curso,
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


# Fallback para procesar_turno(entrada=None). Los botones de la UI ya no
# pasan None: inyectan nudge_cierre_por_boton, que nombra los pasos.
_NUDGE_CONTINUAR = (
    "[El paso anterior se ha cerrado. Continúa con el siguiente paso "
    "según el estado actual — Rosa no ha escrito nada nuevo.]"
)

# Nombres de los pasos tal como se le nombran al LLM en los nudges.
_NOMBRES_PASOS = {
    "tipo_curso":     "TIPO DE CURSO",
    "calendario":     "CALENDARIO",
    "prueba_fuego":   "PRUEBA DE FUEGO",
    "franjas":        "HORARIOS",
    "ajustar_inicio": "AJUSTE DE INICIO",
    "orden":          "ORDEN DE ASIGNATURAS",
    "alumnos":        "ALUMNOS",
    "profesores":     "PROFESORES",
    "practicas":      "PRÁCTICAS",
}


def nudge_cierre_por_boton(bloque_cerrado, bloque_siguiente, resumen):
    """
    Mensaje que se inyecta en llm_messages cuando Rosa cierra una lista
    (alumnos/profesores) pulsando el botón de la interfaz.

    A diferencia del nudge genérico, nombra explícitamente el paso que se
    cerró y el que toca ahora: el cierre por botón NO pasa por el LLM, así
    que su historial se queda con la pregunta del paso viejo sin responder
    — sin este mensaje, el modelo seguía el hilo de la conversación y
    volvía a preguntar por el paso ya cerrado (bug del botón de alumnos).
    """
    nombre_cerrado   = _NOMBRES_PASOS.get(bloque_cerrado, bloque_cerrado.upper())
    nombre_siguiente = _NOMBRES_PASOS.get(bloque_siguiente, bloque_siguiente.upper())
    return (
        f"[Rosa ha pulsado el botón de cerrar la lista. El paso {nombre_cerrado} "
        f"queda COMPLETADO ({resumen}) — no vuelvas a preguntar por él. "
        f"Ahora el paso activo es {nombre_siguiente}: haz su primera pregunta.]"
    )


def procesar_turno(entrada, estado_conversacion, client):
    """
    Processa un torn de la conversa per a la UI de Streamlit.

    Paràmetres:
        entrada             : str | None — missatge de Rosa, o None per demanar que
                               l'agent continuï tot sol (s'usa quan un bloc de llista
                               oberta es tanca amb el botó de la interfície, sense
                               que Rosa hagi escrit res — així l'agent fa la següent
                               pregunta automàticament en comptes de quedar-se mut).
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

    messages.append({"role": "user", "content": entrada if entrada is not None else _NUDGE_CONTINUAR})

    respuesta_text = ""
    terminado      = False
    ruta_docx      = None

    while True:
        # system com a llista: part estàtica cacheada primer, part dinàmica sense caché després
        system_blocks = [
            {"type": "text", "text": SYSTEM_PROMPT,
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": _construir_contexto_estado(bloque_actual, estados)},
        ]
        # Se recalcula en cada vuelta: bloque_actual puede cambiar dentro de este bucle,
        # y solo se ofrecen al LLM las tools del bloque activo en ese momento.
        tools_turno = _herramientas_para_bloque(bloque_actual)

        # [DEBUG-AJUSTE-LLM] logging temporal: qué recibe REALMENTE el LLM cuando
        # bloque_actual == "ajustar_inicio". Quitar una vez diagnosticado.
        if bloque_actual == "ajustar_inicio":
            print("[DEBUG-AJUSTE-LLM] ══════ ANTES de client.messages.create ══════")
            print(f"[DEBUG-AJUSTE-LLM] SYSTEM_PROMPT contiene 'ajuste de la fecha de inicio': "
                  f"{'ajuste de la fecha de inicio' in SYSTEM_PROMPT}")
            print(f"[DEBUG-AJUSTE-LLM] SYSTEM_PROMPT completo:\n{SYSTEM_PROMPT}")
            print(f"[DEBUG-AJUSTE-LLM] tools enviadas: {[t['name'] for t in tools_turno]}")
            print(f"[DEBUG-AJUSTE-LLM] contexto de bloque enviado:\n{system_blocks[1]['text']}")

        resposta = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_blocks,
            tools=tools_turno,
            messages=messages,
        )

        if bloque_actual == "ajustar_inicio":
            print("[DEBUG-AJUSTE-LLM] ══════ DESPUÉS de client.messages.create ══════")
            print(f"[DEBUG-AJUSTE-LLM] stop_reason: {resposta.stop_reason}")
            for bloque_resp in resposta.content:
                if bloque_resp.type == "tool_use":
                    print(f"[DEBUG-AJUSTE-LLM] LLAMÓ A TOOL: {bloque_resp.name} con input={bloque_resp.input}")
                elif hasattr(bloque_resp, "text"):
                    print(f"[DEBUG-AJUSTE-LLM] TEXTO DE RESPUESTA: {bloque_resp.text!r}")
            print("[DEBUG-AJUSTE-LLM] ══════════════════════════════════════════════")

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
            elif resultado_avance.get("horas_insuficientes"):
                # Aviso fijo (no generado por el LLM, igual que el mensaje de éxito):
                # se añade también al historial que ve el modelo, porque la
                # conversación sigue (a diferencia del caso "terminado", aquí Rosa
                # puede seguir escribiendo) y el modelo debe saber que ya se avisó.
                respuesta_text = resultado_avance["respuesta_text"]
                messages.append({"role": "assistant", "content": respuesta_text})
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


