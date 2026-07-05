# Funcions per a la Prova de Foc (Prueba de Fuego) del CAP de mercaderies.
#
# La prova de foc és una sessió de 2h de MM.PP (Maniobres Pràctiques) que Rosa
# programa en un dissabte concret amb un proveïdor extern. Aquestes 2h se separen
# de les 24h totals de MM.PP i es col·loquen com a bloc fix al dissabte triat,
# mentre les 22h restants segueixen el circuit normal de la plantilla.

from decimal import Decimal
from datetime import date, time

CODI_MMPP         = "MM.PP"
NOM_MMPP          = "Mercaderies perilloses bàsica comuna (inclou prova de foc)"
HORES_PF          = Decimal("2")
PROVEIDOR_DEFAULT = "FAST PARCMOTOR"


def crear_prueba_fuego(fecha: date, hora_inicio: time,
                       proveedor: str = PROVEIDOR_DEFAULT) -> dict:
    """Crea el dict de dades de la prova de foc."""
    return {
        "fecha":       fecha,
        "hora_inicio": hora_inicio,
        "proveedor":   proveedor,
    }


def preparar_plantilla_con_prueba_fuego(plantilla, prueba_fuego):
    """
    Retorna una NOVA plantilla amb les hores de MM.PP reduïdes en 2h.
    Les 2h es reserven per a la prova de foc i es col·locaran a part.

    Si prueba_fuego és None (no hi ha prova de foc), retorna la plantilla sense canvis.
    Si MM.PP té menys de 2h en total, llança ValueError.

    Estratègia de reducció: descompta les 2h del primer tros de MM.PP;
    si aquell tros té menys de 2h (cas hipotètic amb fragments petits), continua
    amb el següent. Els trossos que queden a 0h s'eliminen de la llista.

    Paràmetres:
        plantilla    : llista de (codigo, hores) — ex. PLANTILLA_MERCANCIAS
        prueba_fuego : dict {"fecha", "hora_inicio", "proveedor"} o None

    Retorna:
        Nova llista de (codigo, hores_Decimal) amb MM.PP reduïda.
    """
    if prueba_fuego is None:
        return [(cod, Decimal(str(h))) for cod, h in plantilla]

    total_mmpp = sum(Decimal(str(h)) for cod, h in plantilla if cod == CODI_MMPP)
    if total_mmpp < HORES_PF:
        raise ValueError(
            f"{CODI_MMPP} té {total_mmpp}h en total — insuficient per reservar {HORES_PF}h "
            "per a la prova de foc."
        )

    nova = []
    restant = HORES_PF
    for cod, h in plantilla:
        h_dec = Decimal(str(h))
        if cod == CODI_MMPP and restant > Decimal("0"):
            reduccio = min(restant, h_dec)
            nova_h   = h_dec - reduccio
            restant -= reduccio
            if nova_h > Decimal("0"):
                nova.append((cod, nova_h))
            # tros amb 0h: s'elimina
        else:
            nova.append((cod, h_dec))

    return nova
