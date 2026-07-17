# Plantilla de colocació pedagògica del CAP CONTINU de mercaderies (35h).
#
# Cada troç és (codi, hores), com a les plantilles del inicial. El motor la
# recorre EN ORDRE i omple cada dia lectiu segons les hores de la seva franja;
# un troç pot partir-se entre dos dies si no hi cap sencer.
#
# ORDRE D'IMPARTICIÓ CONFIRMAT amb els horaris reals de cursos ja impartits
# (juliol 2026): mòduls en seqüència 1 → 2 → 3 → 10, sense intercalar blocs
# (a diferència del inicial amb 1.2/1.4/3.7). Mateix ordre que el continu
# de viatgers.
#
# El continu NO porta prova de foc.

PLANTILLA_CONTINUO_MERCANCIAS = [
    # Mòdul 1 — Seguretat viària (7h)
    ("3.1",      3.5),
    ("3.4",      3.5),
    # Mòdul 2 — Conducció racional i eficient i evolució tecnològica (7h)
    ("1.2",      3.5),
    ("1.3",      3.5),
    # Mòdul 3 — Normativa sobre tacògraf i temps de conducció i descans
    # (7h, inclou la 1h de pràctica agrupada)
    ("2.1",      7),
    # Mòdul 10 — Sensibilització i Educació Viària (14h, un sol bloc)
    ("Mòdul 10", 14),
]

# Sense obligatòries de cap de setmana ni ampliació al continu (de moment):
# el curs és curt i el document de domini no defineix aquestes restriccions.
OBLIGATORIAS_FINDE_CONTINUO_MERCANCIAS = set()
AMPLIACION_CONTINUO_MERCANCIAS = set()

# Suma: 35,0 hores exactes (21h obligatòries + 14h complementàries)
