# Llista oficial de les assignatures del CAP CONTINU (35h) de mercaderies.
# Noms EXACTES del programa homologat ("Programa desenvolupat de coneixements",
# formació obligatòria C, C+E, C1, C1+E + complementària de mercaderies) — van
# al document que veu la inspecció telemàtica, no es poden abreujar.
# Les hores estan guardades com a strings amb punt decimal perquè Decimal(str) sigui exacte.
#
# CATÀLEG SEPARAT del inicial: encara que alguns codis d'objectiu coincideixin
# (3.1, 1.2, 2.1...), les assignatures del continu tenen hores i noms diferents
# i NO s'han de barrejar amb les del inicial.
#
# Estructura oficial — els números de MÒDUL no coincideixen amb els codis d'OBJECTIU:
#   Mòdul 1 — Seguretat viària (7h)                        = Obj. 3.1 (3h30) + Obj. 3.4 (3h30)
#   Mòdul 2 — Conducció racional i eficient i evolució
#             tecnològica (7h)                             = Obj. 1.2 (3h30) + Obj. 1.3 (3h30)
#   Mòdul 3 — Normativa sobre tacògraf i temps de
#             conducció i descans (7h)                     = Obj. 2.1 (6h teoria + 1h pràctica
#                                                            amb simulador de tacògraf digital)
#   Mòdul 10 — Sensibilització i Educació Viària (14h)     = bloc complementari de mercaderies
#
# El Mòdul 10 es programa com UN SOL bloc de 14h d'aula (així consta al programa:
# "La durada d'aquest mòdul serà de 14 hores que s'impartiran a l'aula"). Els 17
# sub-temes a–q són CONTINGUT intern del mòdul, no unitats d'horari:
#   a) Els accidents de trànsit: la magnitud del problema (1h)
#   b) Dinàmica d'un impacte i conseqüències per a les víctimes (1h)
#   c) La conducció: una tasca de presa de decisions (1h)
#   d) Aptituds i capacitats bàsiques per a una conducció segura (1h)
#   e) Els grups de risc (1h)
#   f) La velocitat com a factor de risc (30min)
#   g) L'alcohol com a factor de risc (1h)
#   h) Les drogues d'abús com a factor de risc (30min)
#   i) Les malalties i els fàrmacs com a factors de risc (30min)
#   j) La somnolència com a factor de risc (1h)
#   k) La fatiga com a factor de risc (30min)
#   l) L'estrès com a factor de risc (30min)
#   m) Seguretat activa i passiva (30min)
#   n) La conducció preventiva (1h)
#   o) Actuació en cas d'accident de trànsit (1h)
#   p) La importància del compliment de les normes de trànsit (1h)
#   q) Debat grupal i dinàmica de grups (1h)
#   (suma: 14h exactes)
#
# Total: 21h obligatòries + 14h complementàries = 35h exactes.

ASIGNATURAS_CONTINUO_MERCANCIAS = [
    # Mòdul 1 — Seguretat viària (7h)
    {"codigo": "3.1",
     "nombre": "Riscos carretera i accidents treball",
     "horas": "3.5"},
    {"codigo": "3.4",
     "nombre": "Aptitud física i mental",
     "horas": "3.5"},
    # Mòdul 2 — Conducció racional i eficient i evolució tecnològica (7h)
    {"codigo": "1.2",
     "nombre": "Dispositius de Seguretat",
     "horas": "3.5"},
    {"codigo": "1.3",
     "nombre": "Optimitzar el consum de carburant",
     "horas": "3.5"},
    # Mòdul 3 — Normativa sobre tacògraf i temps de conducció i descans (7h).
    # La 1h de pràctica (simulador de tacògraf digital) va agrupada amb les 6h de
    # teoria en una sola assignatura (és formal, no la fan), com MM.PP al inicial.
    {"codigo": "2.1",
     "nombre": "Entorn social del transport",
     "horas": "7"},
    # Mòdul 10 — bloc complementari (14h, un sol bloc d'aula)
    {"codigo": "Mòdul 10",
     "nombre": "Sensibilització i Educació Viària",
     "horas": "14"},
]

# Suma oficial: 35,0 hores exactes (verificat amb Decimal per evitar errors de coma flotant)
