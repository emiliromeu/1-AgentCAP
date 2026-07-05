# Coloca de forma determinista las horas de cada asignatura en el calendario respetando franjas y descansos.

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from herramientas.calendario import parsear_fecha, es_dia_valido
from herramientas.motor_prueba_fuego import CODI_MMPP, NOM_MMPP, HORES_PF


# ── Franjas horarias semanales ───────────────────────────────────────────────
#
# Para cada día de la semana (weekday() → 0=lunes … 6=domingo) se define la
# hora de inicio y la hora de fin de clase.
# None significa que ese día no hay clase (domingo).
#
# Estos valores son de ejemplo: reflejan el horario CAP real para que el motor
# funcione desde el primer momento. En el futuro la usuaria podrá ajustarlos.
# Usamos objetos time de datetime para poder hacer aritmética directamente
# (datetime.combine + timedelta), sin necesidad de parsear strings.
FRANJAS_SEMANALES = {
    0: {"inicio": time(18, 0),  "fin": time(21, 15)},  # lunes
    1: {"inicio": time(18, 0),  "fin": time(21, 15)},  # martes
    2: {"inicio": time(18, 0),  "fin": time(21, 15)},  # miércoles
    3: {"inicio": time(18, 0),  "fin": time(21, 15)},  # jueves
    4: {"inicio": time(16, 0),  "fin": time(20, 15)},  # viernes
    5: {"inicio": time(7,  45), "fin": time(14, 15)},  # sábado
    6: None,                                            # domingo — sin clase
}


# ── Reglas de descanso ───────────────────────────────────────────────────────
_BLOQUE_MIN   = 120  # minutos de clase por bloque antes de descanso (2 horas)
_DESCANSO_MIN = 15   # minutos de descanso entre bloques


def horas_clase_de_dia(hora_inicio, hora_fin):
    """
    Calcula las horas de clase NETAS de un día, descontando los descansos.

    Regla de descansos: un descanso de 15 minutos después de cada bloque de
    2 horas de clase, EXCEPTO al final del día. Es decir, los descansos se
    insertan ENTRE bloques, nunca tras el último.

    El enfoque es simular el llenado del tiempo bruto disponible:
      - Tomamos bloques de hasta 2 horas de clase.
      - Entre bloque y bloque (no al final) restamos 15 min de descanso.
      - Sumamos los minutos de clase reales; el resto es descanso o fin de día.

    Parámetros:
        hora_inicio : objeto time con el inicio de la jornada
        hora_fin    : objeto time con el fin de la jornada

    Devuelve float con las horas de clase netas (puede ser decimal, ej. 3.5).
    """
    # Calculamos los minutos brutos disponibles usando una fecha arbitraria
    # como ancla (datetime.combine necesita una fecha)
    ancla = date.today()
    minutos_brutos = int(
        (datetime.combine(ancla, hora_fin) - datetime.combine(ancla, hora_inicio))
        .total_seconds() // 60
    )

    if minutos_brutos <= 0:
        return 0.0

    minutos_restantes = minutos_brutos
    minutos_clase     = 0
    primer_bloque     = True

    while minutos_restantes > 0:
        # Antes de cada bloque (salvo el primero) intentamos insertar el descanso.
        # Si no queda tiempo ni para el descanso, paramos.
        if not primer_bloque:
            if minutos_restantes <= _DESCANSO_MIN:
                break
            minutos_restantes -= _DESCANSO_MIN

        # Tomamos un bloque de clase: hasta _BLOQUE_MIN o lo que quede
        bloque = min(_BLOQUE_MIN, minutos_restantes)
        minutos_clase     += bloque
        minutos_restantes -= bloque
        primer_bloque      = False

    return minutos_clase / 60


def _horas_dia_pf(franja, prueba_fuego):
    """
    Hores de classe d'un dia amb Prova de Foc (capacitat real, no la franja sencera).
    Fase 1: franja_ini → hora_pf - 45min
    PF:     2h fixes
    Fase 2: hora_pf + 2h + 30min → franja_fi
    """
    ancla  = date.today()
    pf_ini = prueba_fuego["hora_inicio"]
    t1_fi  = (datetime.combine(ancla, pf_ini) - timedelta(minutes=45)).time()
    t2_ini = (datetime.combine(ancla, pf_ini) + timedelta(hours=2, minutes=30)).time()
    h1 = Decimal(str(horas_clase_de_dia(franja["inicio"], t1_fi)))
    h2 = Decimal(str(horas_clase_de_dia(t2_ini, franja["fin"])))
    return h1 + HORES_PF + h2


# ── Días lectivos ────────────────────────────────────────────────────────────

def dias_lectivos(fecha_inicio_texto, dia_amarillo_texto, festivos_texto):
    """
    Devuelve la lista ordenada de días lectivos entre la fecha de inicio y el día amarillo
    (ambos incluidos), excluyendo domingos y festivos.

    Parámetros:
        fecha_inicio_texto  : string "DD/MM/AAAA" con el primer día del curso
        dia_amarillo_texto  : string "DD/MM/AAAA" con el último día permitido del plan
        festivos_texto      : lista de strings "DD/MM/AAAA" (puede estar vacía)

    Devuelve:
        Lista de objetos date — no strings — para que el motor pueda operar directamente
        sobre ellos (comparaciones, aritmética, weekday) sin tener que volver a parsear.
        Si alguna fecha de entrada es inválida, devuelve un dict {'error': <mensaje>}.
    """
    # Parseamos la fecha de inicio
    r_inicio = parsear_fecha(fecha_inicio_texto)
    if not r_inicio["valida"]:
        return {"error": f"Fecha de inicio inválida: {r_inicio['mensaje']}"}

    # Parseamos el día amarillo
    r_amarillo = parsear_fecha(dia_amarillo_texto)
    if not r_amarillo["valida"]:
        return {"error": f"Día amarillo inválido: {r_amarillo['mensaje']}"}

    # Parseamos cada festivo; si alguno falla, lo informamos y paramos
    festivos = []
    for texto in festivos_texto:
        r = parsear_fecha(texto)
        if not r["valida"]:
            return {"error": f"Festivo inválido ({texto}): {r['mensaje']}"}
        festivos.append(r["fecha"])

    inicio   = r_inicio["fecha"]
    amarillo = r_amarillo["fecha"]

    # Recorremos el rango día a día y filtramos con es_dia_valido,
    # que ya sabe rechazar domingos, festivos y días posteriores al amarillo.
    lectivos = []
    dia_actual = inicio
    while dia_actual <= amarillo:
        if es_dia_valido(dia_actual, amarillo, festivos)["valido"]:
            lectivos.append(dia_actual)
        dia_actual += timedelta(days=1)

    return lectivos


# ── Dia amb Prova de Foc ─────────────────────────────────────────────────────

def _tramos_dia_pf(colocaciones_dia, franja, pf_coloc, dia):
    """
    Genera els tramos d'un dia amb Prova de Foc (MM.PP pràctic extern).

    Distribució fixa:
      franja_ini → hora_pf - 45min  : matèries normals (Fase 1)
      hora_pf - 45min → hora_pf     : DESCANS - Transport (anada)
      hora_pf → hora_pf + 2h        : MM.PP prova de foc (contínua, sense pausa)
      hora_pf + 2h → hora_pf+2h+30m : DESCANS - Transport (tornada)
      hora_pf+2h+30m → franja_fi    : matèries normals (Fase 2)

    La capacitat de cada fase coincideix exactament amb les hores que
    colocar_materias_dos_colas hi ha assignat (gràcies a _horas_dia_pf),
    per la qual cosa les dues fases s'omplen ajustades, sense desbordament.
    """
    ANADA_MIN   = 45
    TORNADA_MIN = 30

    pf_ini_dt     = datetime.combine(dia, pf_coloc["hora_inicio"])
    anada_ini_dt  = pf_ini_dt - timedelta(minutes=ANADA_MIN)
    pf_fi_dt      = pf_ini_dt + timedelta(hours=2)
    tornada_fi_dt = pf_fi_dt  + timedelta(minutes=TORNADA_MIN)
    franja_fi_dt  = datetime.combine(dia, franja["fin"])

    # Cua de materials normals (sense PF) — còpies mutables
    cola   = [{"codigo": c["codigo"], "nombre": c["nombre"], "horas": c["horas"]}
              for c in colocaciones_dia if not c.get("prueba_fuego")]
    cola_i = [0]   # índex en llista per poder-lo modificar des de la funció interna
    tramos = []

    def _volcar_fins(cursor_dt, t_stop_dt):
        """Col·loca tramos normals des de cursor fins a t_stop; retorna cursor."""
        hores_acum = Decimal("0")
        while cola_i[0] < len(cola):
            c = cola[cola_i[0]]
            if c["horas"] <= Decimal("0"):
                cola_i[0] += 1
                continue
            diff_min = int(round((t_stop_dt - cursor_dt).total_seconds() / 60))
            if diff_min <= 0:
                break
            h_disp          = Decimal(diff_min) / 60
            hores_fins_desc = Decimal("2") - (hores_acum % Decimal("2"))
            chunk = min(Decimal("1"), c["horas"], hores_fins_desc, h_disp)
            if chunk <= Decimal("0"):
                break
            fi_dt = cursor_dt + timedelta(minutes=int(chunk * 60))
            tramos.append({"inicio": cursor_dt.time(), "fin": fi_dt.time(),
                           "codigo": c["codigo"], "nombre": c["nombre"], "tipo": "clase"})
            cursor_dt   = fi_dt
            hores_acum += chunk
            c["horas"] -= chunk
            if c["horas"] <= Decimal("0"):
                cola_i[0] += 1
            # Pausa normal de 15min si assolim múltiple de 2h i queda material i temps
            if (hores_acum % Decimal("2") == Decimal("0") and
                    cursor_dt < t_stop_dt and cola_i[0] < len(cola)):
                fi_br = cursor_dt + timedelta(minutes=15)
                if fi_br <= t_stop_dt:
                    tramos.append({"inicio": cursor_dt.time(), "fin": fi_br.time(),
                                   "codigo": None, "nombre": "DESCANS", "tipo": "descanso"})
                    cursor_dt = fi_br
        return cursor_dt

    cursor = datetime.combine(dia, franja["inicio"])

    # Fase 1: materials normals fins al transport d'anada
    cursor = _volcar_fins(cursor, anada_ini_dt)
    if cursor < anada_ini_dt:
        cursor = anada_ini_dt   # si la fase 1 és buida, avancem directament

    # Transport anada (45min)
    tramos.append({"inicio": cursor.time(), "fin": pf_ini_dt.time(),
                   "codigo": None, "nombre": "DESCANS - Transport (anada)", "tipo": "descanso"})
    cursor = pf_ini_dt

    # Prova de Foc (2h contínues, sense pausa interna)
    tramos.append({"inicio": cursor.time(), "fin": pf_fi_dt.time(),
                   "codigo": pf_coloc["codigo"], "nombre": pf_coloc["nombre"],
                   "tipo":        "clase",
                   "prueba_fuego": True,
                   "profesor":    pf_coloc.get("proveedor", ""),
                   "proveedor":   pf_coloc.get("proveedor", "")})
    cursor = pf_fi_dt

    # Transport tornada (30min)
    tramos.append({"inicio": cursor.time(), "fin": tornada_fi_dt.time(),
                   "codigo": None, "nombre": "DESCANS - Transport (tornada)", "tipo": "descanso"})
    cursor = tornada_fi_dt

    # Fase 2: materials normals restants fins al final de la franja
    _volcar_fins(cursor, franja_fi_dt)

    return tramos


# ── Detalle de franjas horarias con descansos ────────────────────────────────

def detallar_horario(colocaciones, franjas):
    """
    Baja el reparto grueso (colocar_materias) a tramos horarios concretos con descansos.

    Regla de descansos: un descanso de 15 minutos después de cada 2 horas ACUMULADAS
    en el día (el contador no se reinicia al cambiar de materia), EXCEPTO al final
    (si ya no queda más clase, no se inserta descanso).

    La lógica de cada tramo usa la "danza del mínimo ajustada al descanso":
    el chunk es el mínimo de {1 hora, horas restantes de la materia, horas hasta el
    próximo punto de descanso}. Así los descansos siempre caen en el sitio correcto
    aunque una materia se agote a mitad de un bloque de 2 horas.

    Parámetros:
        colocaciones : lista plana de {dia, codigo, nombre, horas} (de colocar_materias)
        franjas      : dict weekday → {"inicio": time, "fin": time} | None

    Devuelve una lista de dicts por día — no plana — porque el siguiente paso
    (PDF/Word) renderiza una sección por día y necesita los tramos agrupados:
        [
            {
                "dia"   : date,
                "tramos": [
                    {"inicio": time, "fin": time,
                     "codigo": str|None, "nombre": str, "tipo": "clase"|"descanso"},
                    ...
                ]
            },
            ...
        ]
    El campo 'tipo' permite al generador de documentos aplicar estilos distintos
    sin tener que inspeccionar el contenido.
    """
    from itertools import groupby

    resultado = []

    # Las colocaciones vienen ya ordenadas por día; groupby agrupa las consecutivas
    for dia, grupo in groupby(colocaciones, key=lambda c: c["dia"]):
        colocaciones_dia = list(grupo)

        franja = franjas.get(dia.weekday())
        if franja is None:
            continue  # no debería ocurrir, pero lo cubrimos

        # Dia amb Prova de Foc → lògica especial (fases + transports)
        pf_coloc = next((c for c in colocaciones_dia if c.get("prueba_fuego")), None)
        if pf_coloc is not None:
            resultado.append({
                "dia":    dia,
                "tramos": _tramos_dia_pf(colocaciones_dia, franja, pf_coloc, dia),
            })
            continue

        # Trabajamos con datetime para la aritmética; .time() solo para el resultado
        cursor = datetime.combine(dia, franja["inicio"])

        # Total de horas de clase del día: para saber si queda más clase tras un bloque
        total_horas_dia        = sum(c["horas"] for c in colocaciones_dia)
        horas_clase_acumuladas = Decimal("0")

        tramos = []

        for coloc in colocaciones_dia:
            horas_restantes = coloc["horas"]

            while horas_restantes > Decimal("0"):
                # Horas hasta el próximo punto de descanso dentro del ciclo de 2 horas
                horas_hasta_descanso = Decimal("2") - (horas_clase_acumuladas % Decimal("2"))

                # Chunk: lo que cabe entre el límite de 1 hora, la materia y el descanso
                chunk = min(Decimal("1"), horas_restantes, horas_hasta_descanso)

                # Tramo de clase
                minutos = int(chunk * 60)
                fin = cursor + timedelta(minutes=minutos)
                tramos.append({
                    "inicio": cursor.time(),
                    "fin":    fin.time(),
                    "codigo": coloc["codigo"],
                    "nombre": coloc["nombre"],
                    "tipo":   "clase",
                })
                cursor = fin

                horas_clase_acumuladas += chunk
                horas_restantes        -= chunk

                # Insertamos descanso si acumulamos múltiplo de 2h Y queda más clase
                if (horas_clase_acumuladas % Decimal("2") == Decimal("0") and
                        horas_clase_acumuladas < total_horas_dia):
                    fin_descanso = cursor + timedelta(minutes=15)
                    tramos.append({
                        "inicio": cursor.time(),
                        "fin":    fin_descanso.time(),
                        "codigo": None,
                        "nombre": "DESCANS",
                        "tipo":   "descanso",
                    })
                    cursor = fin_descanso

        resultado.append({"dia": dia, "tramos": tramos})

    return resultado


# ── Colocación gruesa de materias ────────────────────────────────────────────

def colocar_materias(dias, franjas, cola):
    """
    Reparte los trozos de la cola en los días lectivos siguiendo la "danza del mínimo":
    en cada paso se coloca el mínimo entre las horas libres del día y las horas
    restantes del trozo. Cuando se agota el día se avanza al siguiente;
    cuando se agota el trozo se avanza al siguiente de la cola.

    Esta función realiza el reparto GRUESO (qué materia, cuántas horas, en qué día).
    No baja a franjas horarias concretas ni inserta descansos; eso es el paso siguiente.

    La cola debe construirse antes de llamar a esta función con uno de los puentes:
        - construir_cola_desde_orden(orden, asignaturas) : una entrada por código
        - construir_cola_desde_plantilla(plantilla, asignaturas) : trozos con repeticiones

    Parámetros:
        dias  : lista de objetos date (salida de construir_dias_lectivos)
        franjas: dict weekday → {"inicio": time, "fin": time} | None
        cola  : lista de [codigo, nombre, horas_Decimal] — una entrada por trozo.
                La cola se copia internamente; el original no se muta.

    Devuelve un dict con:
        'colocaciones' : lista plana de {dia, codigo, nombre, horas} ordenada por día,
                         donde 'horas' es Decimal.
        'pendientes'   : lista de códigos de trozos que no pudieron colocarse
                         porque se agotaron los días (vacía si todo cuadró).
    """
    # Copia defensiva: la danza muta las horas de cada entrada
    cola = [[c, n, h] for c, n, h in cola]

    # Horas de clase disponibles por día, pre-calculadas como Decimal
    # Días con franja None (no deberían aparecer tras construir_dias_lectivos, pero lo cubrimos)
    horas_por_dia = {}
    for dia in dias:
        franja = franjas.get(dia.weekday())
        if franja is None:
            horas_por_dia[dia] = Decimal("0")
        else:
            h = horas_clase_de_dia(franja["inicio"], franja["fin"])
            horas_por_dia[dia] = Decimal(str(h))

    colocaciones = []
    dia_idx = 0   # puntero al día actual
    mat_idx = 0   # puntero al trozo actual de la cola

    if not dias or not cola:
        return {"colocaciones": [], "pendientes": [e[0] for e in cola]}

    horas_libres = horas_por_dia[dias[0]]

    while mat_idx < len(cola) and dia_idx < len(dias):
        codigo = cola[mat_idx][0]
        nombre = cola[mat_idx][1]
        dia    = dias[dia_idx]

        # La danza del mínimo: colocamos lo que quepa
        colocado = min(horas_libres, cola[mat_idx][2])

        if colocado > 0:
            colocaciones.append({
                "dia":    dia,
                "codigo": codigo,
                "nombre": nombre,
                "horas":  colocado,
            })

        horas_libres     -= colocado
        cola[mat_idx][2] -= colocado

        # Si el día se agota, avanzamos al siguiente
        if horas_libres == Decimal("0"):
            dia_idx += 1
            if dia_idx < len(dias):
                horas_libres = horas_por_dia[dias[dia_idx]]

        # Si el trozo se agota, avanzamos al siguiente
        if cola[mat_idx][2] == Decimal("0"):
            mat_idx += 1

    # Trozos que quedaron sin colocar (días insuficientes)
    pendientes = [e[0] for e in cola[mat_idx:] if e[2] > 0]

    return {
        "colocaciones": colocaciones,
        "pendientes":   pendientes,
    }


def colocar_materias_dos_colas(dias, franjas, cola_semana, cola_finde,
                               prueba_fuego=None):
    """
    Variante de colocar_materias con regla de fin de semana (dos colas):

    - cola_finde  : trozos de materias obligatorias viernes/sábado. Se colocan
                    únicamente en días con weekday 4 (viernes) o 5 (sábado).
    - cola_semana : resto de trozos. Van en días lunes–jueves.
    - Desbordamiento: si cola_finde se agota antes de llenar un día de finde,
                      el hueco restante se llena con cola_semana.
    - prueba_fuego: dict {"fecha", "hora_inicio", "proveedor"} opcional.
                    Si el día procesado coincide con esa fecha, se reservan 2h
                    para la prueba de fuego (colocación especial con
                    prueba_fuego=True) antes de llenar el resto con las colas.

    Mantiene la danza del mínimo dentro de cada cola y acepta el mismo formato
    de entrada que colocar_materias. Las dos colas se copian internamente.
    """
    cola_semana = [[c, n, h] for c, n, h in cola_semana]
    cola_finde  = [[c, n, h] for c, n, h in cola_finde]

    pf_fecha = prueba_fuego["fecha"] if prueba_fuego is not None else None

    horas_por_dia = {}
    for dia in dias:
        franja = franjas.get(dia.weekday())
        if franja is None:
            horas_por_dia[dia] = Decimal("0")
        elif pf_fecha is not None and dia == pf_fecha:
            horas_por_dia[dia] = _horas_dia_pf(franja, prueba_fuego)
        else:
            h = horas_clase_de_dia(franja["inicio"], franja["fin"])
            horas_por_dia[dia] = Decimal(str(h))

    colocaciones = []
    sem_idx = 0
    fin_idx = 0

    def _volcar(dia, cola, idx, horas_libres):
        while idx < len(cola) and horas_libres > Decimal("0"):
            colocado = min(horas_libres, cola[idx][2])
            if colocado > Decimal("0"):
                colocaciones.append({
                    "dia":    dia,
                    "codigo": cola[idx][0],
                    "nombre": cola[idx][1],
                    "horas":  colocado,
                })
            horas_libres    -= colocado
            cola[idx][2]    -= colocado
            if cola[idx][2] == Decimal("0"):
                idx += 1
        return idx, horas_libres

    for dia in dias:
        horas_libres = horas_por_dia[dia]
        if horas_libres == Decimal("0"):
            continue

        # Reserva de la prova de foc: 2h fixes en el dissabte indicat
        if pf_fecha is not None and dia == pf_fecha:
            colocaciones.append({
                "dia":          dia,
                "codigo":       CODI_MMPP,
                "nombre":       NOM_MMPP,
                "horas":        HORES_PF,
                "prueba_fuego": True,
                "hora_inicio":  prueba_fuego["hora_inicio"],
                "proveedor":    prueba_fuego["proveedor"],
            })
            horas_libres -= HORES_PF
            if horas_libres <= Decimal("0"):
                continue

        if dia.weekday() in (4, 5):
            fin_idx, horas_libres = _volcar(dia, cola_finde, fin_idx, horas_libres)
            if horas_libres > Decimal("0"):
                sem_idx, horas_libres = _volcar(dia, cola_semana, sem_idx, horas_libres)
        else:
            sem_idx, horas_libres = _volcar(dia, cola_semana, sem_idx, horas_libres)

    pendientes = (
        [e[0] for e in cola_semana[sem_idx:] if e[2] > Decimal("0")] +
        [e[0] for e in cola_finde[fin_idx:]  if e[2] > Decimal("0")]
    )
    return {"colocaciones": colocaciones, "pendientes": pendientes}


# ── Puente: estado de franjas del cerebro → FRANJAS_SEMANALES del motor ──────

def construir_franjas_semanales(estado_franjas):
    """
    Convierte los tres horarios recogidos por el cerebro al formato que consume el motor.

    El cerebro guarda las horas como strings "HH:MM":
        estado_franjas["horario_lun_jue"]["valor"] = {"inicio": "18:00", "fin": "21:15"}

    El motor necesita objetos time, indexados por weekday (0=lunes … 6=domingo):
        {0: {"inicio": time(18,0), "fin": time(21,15)}, ..., 6: None}

    Decisión sobre horarios incompletos: si alguno de los tres no ha sido recogido
    todavía (valor None o conseguido=False), se lanza ValueError. Esta función vive
    en la frontera del motor y solo debe llamarse cuando el bloque franjas está
    completo; un fallo explícito es más seguro que producir un horario parcialmente
    incorrecto sin avisar.

    Parámetros:
        estado_franjas : dict con los tres horarios del bloque franjas del cerebro

    Devuelve:
        dict {weekday (int): {"inicio": time, "fin": time} | None}
    """
    # Verificar que los tres horarios están disponibles antes de construir nada
    for nombre in ("horario_lun_jue", "horario_viernes", "horario_sabado"):
        if not estado_franjas[nombre]["conseguido"] or estado_franjas[nombre]["valor"] is None:
            raise ValueError(
                f"El horario '{nombre}' aún no está recogido. "
                "Llama a esta función solo cuando el bloque franjas esté completo."
            )

    def _parsear(hm):
        """Convierte "HH:MM" a un objeto time."""
        return datetime.strptime(hm, "%H:%M").time()

    lj = estado_franjas["horario_lun_jue"]["valor"]
    vi = estado_franjas["horario_viernes"]["valor"]
    sa = estado_franjas["horario_sabado"]["valor"]

    # Lunes a jueves comparten el mismo horario; se usa el mismo dict porque
    # el motor solo lee estos valores y nunca los modifica en su lugar.
    franja_lj = {"inicio": _parsear(lj["inicio"]), "fin": _parsear(lj["fin"])}
    franja_vi = {"inicio": _parsear(vi["inicio"]), "fin": _parsear(vi["fin"])}
    franja_sa = {"inicio": _parsear(sa["inicio"]), "fin": _parsear(sa["fin"])}

    return {
        0: franja_lj,  # lunes
        1: franja_lj,  # martes
        2: franja_lj,  # miércoles
        3: franja_lj,  # jueves
        4: franja_vi,  # viernes
        5: franja_sa,  # sábado
        6: None,       # domingo — sin clase
    }


# ── Puente: estado del calendario del cerebro → días lectivos del motor ───────

def construir_dias_lectivos(estado_calendario):
    """
    Extrae las fechas del estado del calendario y llama a dias_lectivos.

    El cerebro guarda las fechas como strings "DD/MM/AAAA" y los festivos como
    lista de strings (posiblemente vacía):
        estado_calendario["fecha_inicio"]["valor"] = "19/10/2026"
        estado_calendario["dia_amarillo"]["valor"] = "30/11/2026"
        estado_calendario["festivos"]["valor"]     = []  o ["08/12/2026", ...]

    dias_lectivos espera exactamente ese formato, así que el puente solo extrae
    y pasa — no hay conversión.

    OJO: festivos=[] es un valor VÁLIDO ("no hay festivos"), no un dato sin recoger.
    La comprobación de completitud se hace por el flag 'conseguido', no por el valor.

    Decisión sobre datos incompletos: se lanza ValueError si cualquiera de los tres
    datos necesarios (fecha_inicio, dia_amarillo, festivos) no ha sido recogido
    todavía. El motor no debe arrancar con un calendario parcial; fallar ruidosamente
    es más seguro que producir una lista de días silenciosamente incorrecta.

    Parámetros:
        estado_calendario : dict con los cuatro datos del bloque calendario del cerebro

    Devuelve:
        Lista de objetos date con los días lectivos (resultado de dias_lectivos),
        o un dict {'error': <mensaje>} si alguna fecha del estado es inválida.
    """
    # Los tres datos que necesita el motor de teoría (dia_verde no se usa aquí)
    for nombre in ("fecha_inicio", "dia_amarillo", "festivos"):
        if not estado_calendario[nombre]["conseguido"]:
            raise ValueError(
                f"El dato '{nombre}' del calendario aún no está recogido. "
                "Llama a esta función solo cuando el bloque calendario esté completo."
            )

    fecha_inicio_texto = estado_calendario["fecha_inicio"]["valor"]
    dia_amarillo_texto = estado_calendario["dia_amarillo"]["valor"]
    festivos_texto     = estado_calendario["festivos"]["valor"]   # [] es válido

    return dias_lectivos(fecha_inicio_texto, dia_amarillo_texto, festivos_texto)


# ── Puente: estado del orden del cerebro → orden del motor ───────────────────

def construir_orden(estado_orden):
    """
    Extrae la lista de códigos de asignatura del estado del orden.

    El cerebro guarda el orden como lista de strings:
        estado_orden["orden"]["valor"] = ["1.1", "1.2", "1.3", ...]

    colocar_materias espera exactamente esa lista, así que el puente
    solo extrae y devuelve — no hay conversión.

    Decisión sobre orden incompleto: si el orden no ha sido recogido todavía
    (conseguido=False o valor=None), se lanza ValueError. Mismo criterio que
    los otros dos puentes: fallar ruidosamente antes que dejar que el motor
    coloque las materias en un orden equivocado sin avisar.

    Parámetros:
        estado_orden : dict con el dato "orden" del bloque orden del cerebro

    Devuelve:
        Lista de strings con los códigos de asignatura en orden de impartición.
    """
    if not estado_orden["orden"]["conseguido"] or estado_orden["orden"]["valor"] is None:
        raise ValueError(
            "El orden de asignaturas aún no está recogido. "
            "Llama a esta función solo cuando el bloque orden esté completo."
        )

    return estado_orden["orden"]["valor"]


# ── Puentes: lista de códigos / plantilla → cola de colocar_materias ─────────

def construir_cola_desde_orden(orden, asignaturas):
    """
    Convierte una lista de códigos (el orden clásico) a la cola que espera
    colocar_materias: una entrada por código con las horas totales de ASIGNATURAS.

    Es la ruta «clásica», equivalente a la construcción que antes hacía
    colocar_materias internamente.

    Parámetros:
        orden       : lista de strings con los códigos en orden de impartición
        asignaturas : lista de dicts {'codigo', 'nombre', 'horas'} (ASIGNATURAS)

    Devuelve:
        Lista de [codigo, nombre, horas_Decimal], una entrada por código.
    """
    por_codigo = {a["codigo"]: a for a in asignaturas}
    return [
        [codigo, por_codigo[codigo]["nombre"], Decimal(por_codigo[codigo]["horas"])]
        for codigo in orden
    ]


def construir_cola_desde_plantilla(plantilla, asignaturas):
    """
    Convierte una plantilla de trozos [(codigo, horas), ...] a la cola que
    espera colocar_materias.

    A diferencia de construir_cola_desde_orden, aquí la fragmentación y el orden
    pedagógico ya vienen dados por la plantilla: el mismo código puede aparecer
    varias veces (cada aparición es un trozo independiente que se colocará en el
    orden en que figure en la plantilla).

    Parámetros:
        plantilla   : lista de (codigo, horas) — ej. PLANTILLA_MERCANCIAS
        asignaturas : lista de dicts {'codigo', 'nombre', 'horas'} (ASIGNATURAS)
                      — solo se usa para resolver el nombre de cada código

    Devuelve:
        Lista de [codigo, nombre, horas_Decimal], un entry por trozo de la plantilla.
    """
    por_codigo = {a["codigo"]: a for a in asignaturas}
    return [
        [codigo, por_codigo[codigo]["nombre"], Decimal(str(horas))]
        for codigo, horas in plantilla
    ]


def construir_colas_desde_plantilla(plantilla, asignaturas, obligatorias_finde):
    """
    Separa la plantilla en dos colas manteniendo el orden relativo de cada una:
        cola_semana : trozos cuyo código NO está en obligatorias_finde
        cola_finde  : trozos cuyo código SÍ está en obligatorias_finde

    Pensada para pasar directamente a colocar_materias_dos_colas.

    Devuelve (cola_semana, cola_finde) — listas de [codigo, nombre, horas_Decimal].
    """
    por_codigo  = {a["codigo"]: a for a in asignaturas}
    cola_semana = []
    cola_finde  = []
    for codigo, horas in plantilla:
        entrada = [codigo, por_codigo[codigo]["nombre"], Decimal(str(horas))]
        if codigo in obligatorias_finde:
            cola_finde.append(entrada)
        else:
            cola_semana.append(entrada)
    return cola_semana, cola_finde
