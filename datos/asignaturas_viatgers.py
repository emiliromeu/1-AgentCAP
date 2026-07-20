# Llista oficial de les 19 assignatures del CAP (Certificat d'Aptitud Professional) de viatgers.
# Les hores estan guardades com a strings amb punt decimal perquè Decimal(str) sigui exacte
# i no hereti errors de representació de coma flotant en convertir des de float.

ASIGNATURAS_VIATGERS = [
    {"codigo": "1.1",       "nombre": "Cadena cinemàtica",                          "horas": "8"},
    {"codigo": "1.2",       "nombre": "Dispositius de seguretat",                   "horas": "9"},
    {"codigo": "1.3",       "nombre": "Optimitzar consum",                          "horas": "9"},
    {"codigo": "1.3 bis",   "nombre": "Anticipar riscos",                           "horas": "2.5"},
    {"codigo": "1.5",       "nombre": "Seguretat i comoditat de viatgers",          "horas": "6.5"},
    {"codigo": "1.6",       "nombre": "Operació de càrrega i descàrrega",           "horas": "6"},
    {"codigo": "2.1",       "nombre": "Entorn social del transport",                "horas": "12"},
    {"codigo": "2.3",       "nombre": "Reglamentació de viatgers",                  "horas": "5"},
    {"codigo": "3.1",       "nombre": "Riscos i accidents de treball",              "horas": "8"},
    {"codigo": "3.2",       "nombre": "Prevenció de la delinqüència",               "horas": "1"},
    {"codigo": "3.3",       "nombre": "Prevenir riscos físics",                     "horas": "3"},
    {"codigo": "3.4",       "nombre": "Aptitud física i mental",                    "horas": "3"},
    {"codigo": "3.5",       "nombre": "Avaluar situacions d'emergència",            "horas": "3"},
    {"codigo": "3.6",       "nombre": "Imatge de marca",                            "horas": "3"},
    {"codigo": "3.8",       "nombre": "Entorn econòmic de viatgers",                "horas": "15"},
    {"codigo": "Mòdul 1",   "nombre": "Sensibilització per a la discapacitat",      "horas": "10"},
    {"codigo": "2 Mòdul 2", "nombre": "Transport Escolar",                          "horas": "10"},
    {"codigo": "3 Mòdul 3", "nombre": "Primers Auxilis",                            "horas": "8"},
    {"codigo": "Mòdul 5",   "nombre": "Tacògraf Digital",                           "horas": "8"},
]

# Suma oficial: 130,0 hores exactes (verificat amb Decimal per evitar errors de coma flotant)
