# Director de orquesta: une los tres bloques recogidos por el cerebro con el motor.
# Recibe los estados reales (calendario, franjas, orden) y produce el horario detallado.
# No imprime ni conversa — solo orquesta puentes y motor, y devuelve el resultado.

from collections import defaultdict
from datetime import datetime, date, timedelta

from datos.asignaturas          import ASIGNATURAS
from datos.asignaturas_viatgers import ASIGNATURAS_VIATGERS
from datos.plantilla_mercancias import PLANTILLA_MERCANCIAS, OBLIGATORIAS_FINDE_MERCANCIAS
from datos.plantilla_viatgers   import PLANTILLA_VIATGERS,   OBLIGATORIAS_FINDE_VIATGERS
from herramientas.motor_horario import (
    construir_dias_lectivos,
    construir_franjas_semanales,
    construir_colas_desde_plantilla,
    colocar_materias_dos_colas,
    detallar_horario,
)
from herramientas.motor_prueba_fuego import preparar_plantilla_con_prueba_fuego


def aplicar_profesores(horario_detallado, estado_profesores):
    """
    Añade el campo 'profesor' a cada tramo de clase del horario.

    Lógica por día:
      - Por defecto, el profesor es el general del curso.
      - Si la fecha del día coincide con una excepción, se usa el profesor
        de esa excepción en lugar del general.
      - Los tramos de tipo 'descanso' no reciben el campo 'profesor'.

    Comparación de fechas: el horario usa objetos date; las excepciones
    guardan strings "DD/MM/AAAA". Se formatea el date con strftime para
    comparar en el mismo formato, evitando parsear los strings.

    Modifica el horario en su lugar (añade la clave a los dicts de tramo)
    y lo devuelve para encadenamiento.

    Parámetros:
        horario_detallado : lista de dicts {"dia": date, "tramos": [...]}
                            producida por detallar_horario
        estado_profesores : dict del bloque profesores del cerebro
                            {"profesor_general": str, "excepciones": [...], "terminado": bool}

    Devuelve:
        La misma lista, con el campo 'profesor' añadido en cada tramo de clase.
    """
    profesor_general = estado_profesores["profesor_general"]

    # Índice de excepciones: "DD/MM/AAAA" → nombre del profesor sustituto
    excepciones = {
        exc["fecha"]: exc["profesor"]
        for exc in estado_profesores["excepciones"]
    }

    for entrada in horario_detallado:
        # Convertir date a "DD/MM/AAAA" para comparar con las claves del índice
        fecha_texto = entrada["dia"].strftime("%d/%m/%Y")
        profesor_dia = excepciones.get(fecha_texto, profesor_general)

        for tramo in entrada["tramos"]:
            if tramo["tipo"] == "clase" and not tramo.get("prueba_fuego"):
                tramo["profesor"] = profesor_dia
            # Los descansos y tramos PF (tienen su proveedor como profesor) se dejan sin cambios

    return horario_detallado


_CONF_CURSO = {
    "mercancias": (PLANTILLA_MERCANCIAS, OBLIGATORIAS_FINDE_MERCANCIAS, ASIGNATURAS),
    "viatgers":   (PLANTILLA_VIATGERS,   OBLIGATORIAS_FINDE_VIATGERS,   ASIGNATURAS_VIATGERS),
}


def generar_horario(estado_calendario, estado_franjas, estado_orden,
                    tipo_curso="mercancias", prueba_fuego=None):
    """
    Genera el horario detallado a partir de los tres estados recogidos por el cerebro.

    Parámetros:
        estado_calendario : dict del bloque calendario (fecha_inicio, dia_amarillo, festivos)
        estado_franjas    : dict del bloque franjas (horario_lun_jue, horario_viernes, horario_sabado)
        estado_orden      : dict del bloque orden (lista de códigos de asignatura)
        tipo_curso        : "mercancias" (defecto) o "viatgers"

    Devuelve:
        {"horario": [...], "pendientes": [...]}
    """
    if tipo_curso not in _CONF_CURSO:
        raise ValueError(f"tipo_curso desconegut: {tipo_curso!r}. Valors: {list(_CONF_CURSO)}")
    plantilla, obligatorias_finde, asignaturas = _CONF_CURSO[tipo_curso]

    # ── Paso 1: puentes — de estados del cerebro a formatos del motor ─────────
    dias    = construir_dias_lectivos(estado_calendario)
    franjas = construir_franjas_semanales(estado_franjas)

    # Si hi ha prova de foc (només mercaderies), reduïm MM.PP 2h a la plantilla
    pf = prueba_fuego if (tipo_curso == "mercancias" and prueba_fuego is not None) else None
    plantilla_motor = preparar_plantilla_con_prueba_fuego(plantilla, pf)

    cola_semana, cola_finde = construir_colas_desde_plantilla(
        plantilla_motor, asignaturas, obligatorias_finde
    )

    # ── Paso 2: colocación gruesa — qué materia va en qué día y cuántas horas ─
    resultado = colocar_materias_dos_colas(dias, franjas, cola_semana, cola_finde,
                                           prueba_fuego=pf)

    # ── Paso 3: detalle — bajar a tramos horarios con descansos ──────────────
    horario = detallar_horario(resultado["colocaciones"], franjas)

    return {
        "horario":    horario,
        "pendientes": resultado["pendientes"],
    }


def horas_totales_plantilla(tipo_curso):
    """
    Devuelve el total de horas oficiales del plan (suma de la plantilla) para
    el tipo de curso — 130.0 h tanto para mercancías como para viajeros hoy,
    pero se calcula sumando la plantilla real en vez de un número fijo, para
    seguir siendo correcto si la plantilla cambiara en el futuro.
    """
    if tipo_curso not in _CONF_CURSO:
        raise ValueError(f"tipo_curso desconegut: {tipo_curso!r}. Valors: {list(_CONF_CURSO)}")
    plantilla, _, _ = _CONF_CURSO[tipo_curso]
    return sum(float(h) for _, h in plantilla)


def horas_colocadas(horario_detallado):
    """
    Suma las horas netas de clase (excluyendo descansos) ya colocadas en un
    horario detallado (el que devuelve generar_horario en la clave "horario").
    """
    ancla = date.today()
    total = 0.0
    for entrada in horario_detallado:
        for tramo in entrada["tramos"]:
            if tramo["tipo"] != "clase":
                continue
            minutos = (
                datetime.combine(ancla, tramo["fin"]) - datetime.combine(ancla, tramo["inicio"])
            ).total_seconds() / 60
            total += minutos / 60
    return total


def cronograma_por_semanas(horario_detallado):
    """
    Agrupa el horario detallado por semanas naturales (lunes–domingo) y acumula
    las horas de clase de cada materia (por código) dentro de cada semana.

    Criterio de semana: cada día se asigna a la semana cuyo lunes lo contiene.
    Las semanas se numeran 1, 2, 3... desde la primera semana con clases.
    Los tramos de tipo 'descanso' no se cuentan.
    Las horas se acumulan en minutos (enteros) para evitar errores de coma
    flotante, y se convierten a horas al devolver el resultado.

    Parámetros:
        horario_detallado : lista de dicts {"dia": date, "tramos": [...]}
                            producida por detallar_horario / generar_horario

    Devuelve:
        dict  { num_semana: { codigo: horas_float } }
        — Las semanas están ordenadas; las materias dentro de cada semana,
          en orden de primera aparición.
    """
    # ── Paso 1: asignar a cada día su "lunes de semana" ──────────────────────
    # date.weekday() devuelve 0=lunes … 6=domingo, así que restar weekday()
    # da siempre el lunes de esa semana natural.

    lunes_por_dia = {}
    for entrada in horario_detallado:
        dia   = entrada["dia"]
        lunes = dia - timedelta(days=dia.weekday())
        lunes_por_dia[dia] = lunes

    # Numerar semanas en orden cronológico: la más temprana es la Setmana 1
    lunes_ordenados = sorted(set(lunes_por_dia.values()))
    lunes_a_num     = {l: i + 1 for i, l in enumerate(lunes_ordenados)}

    # ── Paso 2: acumular minutos de clase por semana y código ─────────────────
    # Usamos minutos enteros para evitar aritmética de coma flotante en la suma.

    BASE = date.today()   # fecha auxiliar para combinar con time y restar
    acumulado = defaultdict(lambda: defaultdict(int))  # {num_sem: {codigo: minutos}}

    for entrada in horario_detallado:
        dia       = entrada["dia"]
        num_sem   = lunes_a_num[lunes_por_dia[dia]]

        for tramo in entrada["tramos"]:
            if tramo["tipo"] != "clase":
                continue   # descansos fuera

            minutos = int(
                (datetime.combine(BASE, tramo["fin"]) -
                 datetime.combine(BASE, tramo["inicio"]))
                .total_seconds() / 60
            )
            acumulado[num_sem][tramo["codigo"]] += minutos

    # ── Paso 3: convertir minutos → horas y devolver como dicts normales ──────
    return {
        num_sem: {codigo: mins / 60 for codigo, mins in materias.items()}
        for num_sem, materias in sorted(acumulado.items())
    }
