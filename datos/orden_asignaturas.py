# Orden habitual de impartición de las asignaturas del CAP de mercancías.
# Es un dato fijo del dominio, como las propias asignaturas: refleja el cronograma
# estándar que se sigue en la mayoría de ediciones del curso.
# Los códigos deben coincidir exactamente con los de datos/asignaturas.py.
# Si el cronograma de una edición concreta requiere otro orden, se pasa
# directamente al motor en lugar de usar esta constante.

ORDEN_HABITUAL_MERCANCIAS = [
    "1.1",        # Cadena cinemàtica
    "1.2",        # Dispositius de seguretat
    "1.3",        # Optimitzar consum
    "1.3 bis",    # Anticipar riscos
    "1.4",        # Operació de càrrega i descàrrega
    "2.1",        # Entorn social del transport
    "2.2",        # Reglamentació de mercaderies
    "3.1",        # Riscos i accidents de treball
    "3.2",        # Prevenció de la delinqüència
    "3.3",        # Prevenir riscos físics
    "3.4",        # Aptitud física i mental
    "3.5",        # Avaluar situacions d'emergència
    "3.6",        # Imatge de marca
    "3.7",        # Entorn econòmic de mercaderies
    "MM.PP",      # Mercaderies perilloses bàsica comuna (inclou prova de foc)
    "Mòdul 2",    # Cisternes
]
