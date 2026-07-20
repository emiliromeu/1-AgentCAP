# Plantilla de colocació pedagògica del CAP de viatgers (130h).
#
# Cada troç és (codi, hores). Els codis que apareixen diverses vegades
# en la seqüència reflecteixen la fragmentació pedagògica real del curs.
#
# OBLIGATORIAS_FINDE_VIATGERS: codis que han de caure obligatòriament
# en divendres o dissabte (weekday 4 o 5). El motor dos-coles
# els gestiona per separat de la resta.

PLANTILLA_VIATGERS = [
    ("2.3",      4),
    ("1.6",      6),
    ("2.3",      1),
    ("3.8",      5),
    ("1.1",      8),
    ("1.2",      1),
    ("3.8",     10),
    ("1.2",      2),
    ("1.3",      4),
    ("1.2",      6),
    ("1.5",      0.5),
    ("1.3",      3),
    ("1.5",      6),
    ("1.3 bis",  2.5),
    ("2.1",      9),
    ("2 Mòdul 2", 10),
    ("2.1",      3),
    ("3.3",      3),
    ("3.4",      3),
    ("3.5",      3),
    ("3 Mòdul 3",  8),
    ("Mòdul 5",  2),
    ("3.6",      3),
    ("3.1",      8),
    ("Mòdul 5",  6),
    ("Mòdul 1",  8),
    ("1.3",      2),
    ("Mòdul 1",  2),
    ("3.2",      1),
]

# "2 Mòdul 2" (Transport Escolar) està a OBLIGATORIAS_FINDE però NO a AMPLIACION:
# es força a divendres/dissabte com la resta de finde, però NO és assignatura
# d'ampliació ni surt en vermell (el color/ampliació el marca AMPLIACION_VIATGERS,
# que és un set independent).
OBLIGATORIAS_FINDE_VIATGERS = {"1.5", "1.6", "2.3", "3.8", "2 Mòdul 2"}

# Materias que apareixen en VERMELL al cronograma (les fan els alumnes d'ampliació).
AMPLIACION_VIATGERS = {"1.5", "1.6", "2.3", "3.8"}

# Regla 2: preferència de finde SENSE ser obligatòria. "3 Mòdul 3" (Primers
# Auxilis, 8h) es col·loca SENCER a divendres/dissabte si hi cap en un cap de
# setmana (rere les obligatòries); si no hi cap sencer, va SENCER a la cola de
# semana. NO és d'ampliació ni surt en vermell. Set independent d'OBLIGATORIAS
# i d'AMPLIACION.
PREFERENTES_FINDE_VIATGERS = {"3 Mòdul 3"}

# Suma: 130,0 hores exactes (29 trossos, 19 matèries)
