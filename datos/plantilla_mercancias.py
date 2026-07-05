# Plantilla de colocación pedagógica del CAP de mercancías inicial (130h).
#
# Define la SECUENCIA ORDENADA de trozos de materia que el motor debe colocar
# en los días lectivos. Cada trozo es (código, horas).
#
# La fragmentación refleja la estructura pedagógica real extraída de un CAP
# verificado: algunas materias aparecen varias veces en la secuencia (1.2, 1.4
# y 3.7 se retoman más adelante), lo que modela el reparto habitual donde se
# intercalan bloques de diferentes módulos a lo largo del curso.
#
# Esta plantilla es INDEPENDIENTE de las franjas horarias: el motor la recorre
# en orden y va llenando cada día lectivo con tantos trozos como quepan según
# las horas de su franja (lun-jue 3h, viernes 4h, sábado 6h, etc.). Un trozo
# puede partirse entre dos días si no cabe entero.
#
# Para usar en motor_horario en lugar de ORDEN_HABITUAL_MERCANCIAS:
#   from datos.plantilla_mercancias import PLANTILLA_MERCANCIAS

# Plantilla de colocación de MERCANCÍAS INICIAL: secuencia ordenada de trozos de materia.
# Cada trozo es (código, horas). La fragmentación pedagógica se expresa con materias que
# aparecen varias veces en la secuencia (1.2, 1.4 y 3.7 se retoman más tarde). Suma 130h.
# Es INDEPENDIENTE de las franjas: el motor colocará estos trozos EN ORDEN, llenando cada
# día lectivo según las horas de su franja (lun-jue 3h, viernes 4h, sábado 6h, etc.).
# Materias cuya colocación DEBE caer en viernes o sábado (ampliación).
# El resto va entre semana; si sobra hueco en finde tras vaciar esta cola,
# el motor lo ocupa con materias de semana para no desperdiciar horas.
OBLIGATORIAS_FINDE_MERCANCIAS = {"1.4", "2.2", "3.7"}

# Materias que apareixen en VERMELL al cronograma (les fan els alumnes d'ampliació).
# Subconjunt de les obligatòries de finde (MM.PP és prova de foc i es tractarà a part).
AMPLIACION_MERCANCIAS = {"1.4", "2.2", "3.7"}

PLANTILLA_MERCANCIAS = [
    ("1.3",      9),
    ("3.2",      1),
    ("1.1",      8),
    ("1.2",      4),
    ("1.4",     10),
    ("2.1",     12),
    ("3.7",     10),
    ("3.3",      3),
    ("3.4",      3),
    ("3.5",      3),
    ("3.6",      3),
    ("2.2",      5),
    ("1.4",      2.5),
    ("3.7",      2),
    ("1.2",      5),
    ("3.1",      8),
    ("3.7",      3),
    ("MM.PP",   24),
    ("1.3 bis",  2.5),
    ("Mòdul 2", 12),
]
