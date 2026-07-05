# Lista oficial de las 16 asignaturas del CAP (Certificat d'Aptitud Professional) de mercaderies.
# Las horas están guardadas como strings con punto decimal para que Decimal(str) sea exacto
# y no herede errores de representación de coma flotante al convertir desde float.

ASIGNATURAS = [
    {"codigo": "1.1",        "nombre": "Cadena cinemàtica",                                          "horas": "8"},
    {"codigo": "1.2",        "nombre": "Dispositius de seguretat",                                   "horas": "9"},
    {"codigo": "1.3",        "nombre": "Optimitzar consum",                                          "horas": "9"},
    {"codigo": "1.3 bis",    "nombre": "Anticipar riscos",                                           "horas": "2.5"},
    {"codigo": "1.4",        "nombre": "Operació de càrrega i descàrrega",                           "horas": "12.5"},
    {"codigo": "2.1",        "nombre": "Entorn social del transport",                                "horas": "12"},
    {"codigo": "2.2",        "nombre": "Reglamentació de mercaderies",                               "horas": "5"},
    {"codigo": "3.1",        "nombre": "Riscos i accidents de treball",                              "horas": "8"},
    {"codigo": "3.2",        "nombre": "Prevenció de la delinqüència",                               "horas": "1"},
    {"codigo": "3.3",        "nombre": "Prevenir riscos físics",                                     "horas": "3"},
    {"codigo": "3.4",        "nombre": "Aptitud física i mental",                                    "horas": "3"},
    {"codigo": "3.5",        "nombre": "Avaluar situacions d'emergència",                            "horas": "3"},
    {"codigo": "3.6",        "nombre": "Imatge de marca",                                            "horas": "3"},
    {"codigo": "3.7",        "nombre": "Entorn econòmic de mercaderies",                             "horas": "15"},
    {"codigo": "MM.PP",      "nombre": "Mercaderies perilloses bàsica comuna (inclou prova de foc)", "horas": "24"},
    {"codigo": "Mòdul 2",    "nombre": "Cisternes",                                                  "horas": "12"},
]

# Suma oficial: 130,0 horas exactas (verificado con Decimal para evitar errores de coma flotante)
