# Motor de col·locació automàtica de sessions de pràctiques del CAP.
#
# Calcula i distribueix les hores de pràctica (10h × alumnes complets +
# 2.5h × alumnes d'ampliació) en dies lectius a partir de la segona setmana,
# respectant els horaris de teoria per evitar solapaments.
#
# Les hores dels alumnes complets van primer (flag ampliacio=False).
# Les hores d'ampliació van al final, en un bloc identificable (ampliacio=True).

from decimal import Decimal
from datetime import date, time, timedelta


# ── Blocs horaris de pràctica ─────────────────────────────────────────────────
# Matí:  08:00 – 13:00 (5h màxim)
# Tarda: 15:00 – 17:00 (2h màxim)
_BLOCS = [
    (time(8,  0), time(13, 0), Decimal("5")),
    (time(15, 0), time(17, 0), Decimal("2")),
]


def _add_hores(t: time, h: Decimal) -> time:
    """Suma hores_decimal a un time. Retorna time."""
    total_min = t.hour * 60 + t.minute + int(h * 60)
    return time(total_min // 60, total_min % 60)


def _bloc_valid(bloc_ini: time, bloc_fi: time, franja_teoria) -> bool:
    """
    Retorna True si el bloc de pràctica NO solapa la franja de teoria.
    franja_teoria és {'inicio': time, 'fin': time} o None.
    """
    if franja_teoria is None:
        return True
    teoria_ini = franja_teoria["inicio"]
    teoria_fi  = franja_teoria["fin"]
    return bloc_fi <= teoria_ini or bloc_ini >= teoria_fi


def colocar_practicas(dias_lectivos, franjas, n_completos, n_ampliacion,
                      festivos=None):
    """
    Distribueix les hores de pràctica en sessions a partir de la segona setmana.

    Paràmetres:
        dias_lectivos  : llista de date (sortida de construir_dias_lectivos)
        franjas        : dict weekday→{'inicio': time, 'fin': time}|None
                         (per detectar solapaments amb la teoria)
        n_completos    : nombre d'alumnes de curs complet
        n_ampliacion   : nombre d'alumnes d'ampliació
        festivos       : llista de date a excloure (normalment ja exclosos a
                         dias_lectivos, però es respecta per seguretat)

    Retorna:
        Llista de dicts amb:
            data        : date
            hora_inicio : time
            hora_fin    : time
            hores       : Decimal (hores netes de la sessió)
            ampliacio   : bool (True = sessió per als alumnes d'ampliació)
    """
    festius_set = set(festivos or [])

    hores_completes = Decimal("10")  * n_completos
    hores_ampliacio = Decimal("2.5") * n_ampliacion

    # ── Dies disponibles: a partir de la segona setmana del calendari ─────────
    if not dias_lectivos:
        return []

    primera_setmana = dias_lectivos[0] - timedelta(days=dias_lectivos[0].weekday())
    dies = [
        d for d in dias_lectivos
        if (d - timedelta(days=d.weekday())) > primera_setmana
        and d not in festius_set
        and d.weekday() <= 3           # només dilluns–dijous (0–3)
    ]

    # ── Col·locació: primer completes, després ampliació ──────────────────────
    sessions = []
    pendent_c = hores_completes
    pendent_a = hores_ampliacio

    for dia in dies:
        if pendent_c <= 0 and pendent_a <= 0:
            break

        franja_t = franjas.get(dia.weekday()) if franjas else None

        for ini_bloc, fi_bloc, max_h in _BLOCS:
            if pendent_c <= 0 and pendent_a <= 0:
                break

            if not _bloc_valid(ini_bloc, fi_bloc, franja_t):
                continue   # solapament amb teoria: salta aquest bloc

            # Hores totals pendents limitat per la capacitat del bloc
            total_pendent = pendent_c + pendent_a
            h_bloc = min(max_h, total_pendent)
            if h_bloc <= 0:
                break

            # ── Part 1: omplir amb hores de completes ──────────────────────
            h_comp = min(pendent_c, h_bloc)
            cursor = ini_bloc

            if h_comp > 0:
                fi_sess = _add_hores(cursor, h_comp)
                sessions.append({
                    "data":        dia,
                    "hora_inicio": cursor,
                    "hora_fin":    fi_sess,
                    "hores":       h_comp,
                    "ampliacio":   False,
                })
                pendent_c -= h_comp
                cursor     = fi_sess

            # ── Part 2: omplir la resta del bloc amb hores d'ampliació ────
            h_amp = min(pendent_a, h_bloc - h_comp)
            if h_amp > 0:
                fi_sess = _add_hores(cursor, h_amp)
                sessions.append({
                    "data":        dia,
                    "hora_inicio": cursor,
                    "hora_fin":    fi_sess,
                    "hores":       h_amp,
                    "ampliacio":   True,
                })
                pendent_a -= h_amp

    return sessions
