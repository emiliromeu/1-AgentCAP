# Llista oficial de les assignatures del CAP CONTINU (35h) de viatgers.
# Noms EXACTES del programa homologat ("Programa desenvolupat de coneixements",
# formació obligatòria D, D+E, D1, D1+E + complementària de viatgers) — van
# al document que veu la inspecció telemàtica, no es poden abreujar.
# Les hores estan guardades com a strings amb punt decimal perquè Decimal(str) sigui exacte.
#
# CATÀLEG SEPARAT del inicial: MOLT IMPORTANT aquí — el inicial de viatgers ja
# usa els codis "Mòdul 1/2/3/5" per a Sensibilització per a la discapacitat,
# Transport Escolar, Primers Auxilis i Tacògraf Digital. El "Mòdul 6" del
# continu no té res a veure amb aquells: mai barrejar els dos catàlegs.
#
# Estructura oficial — els números de MÒDUL no coincideixen amb els codis d'OBJECTIU:
#   Mòdul 1 — Seguretat viària (7h)                        = Obj. 3.1 (3h30) + Obj. 3.4 (3h30)
#   Mòdul 2 — Conducció racional i eficient i evolució
#             tecnològica (7h)                             = Obj. 1.2 (3h30) + Obj. 1.3 (3h30)
#   Mòdul 3 — Normativa sobre tacògraf i temps de
#             conducció i descans (7h)                     = Obj. 2.1 (6h teoria + 1h pràctica
#                                                            amb simulador de tacògraf digital)
#   Mòdul 6 — Sensibilització i Educació Viària (14h)      = bloc complementari de viatgers
#
# El Mòdul 6 es programa com UN SOL bloc de 14h d'aula (així consta al programa:
# "La durada d'aquest mòdul serà de 14 hores que s'impartiran a l'aula"). Els 17
# sub-temes a–q són CONTINGUT intern del mòdul, no unitats d'horari (mateixa
# llista i durades que el Mòdul 10 de mercaderies — veure
# asignaturas_continuo_mercancias.py; suma 14h exactes).
#
# Total: 21h obligatòries + 14h complementàries = 35h exactes.

ASIGNATURAS_CONTINUO_VIATGERS = [
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
     "nombre": "Poder optimitzar el consum de carburant",
     "horas": "3.5"},
    # Mòdul 3 — Normativa sobre tacògraf i temps de conducció i descans (7h).
    # La 1h de pràctica (simulador de tacògraf digital) va agrupada amb les 6h de
    # teoria en una sola assignatura (és formal, no la fan), com MM.PP al inicial.
    {"codigo": "2.1",
     "nombre": "Entorn social del transport",
     "horas": "7"},
    # Mòdul 6 — bloc complementari (14h, un sol bloc d'aula)
    {"codigo": "Mòdul 6",
     "nombre": "Sensibilització i Educació Viària",
     "horas": "14"},
]

# Suma oficial: 35,0 hores exactes (verificat amb Decimal per evitar errors de coma flotant)
