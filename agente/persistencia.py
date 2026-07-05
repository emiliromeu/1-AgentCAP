"""
Persistència de la sessió CAP: guarda/carrega el conv_state i els flags de la UI.

Estructura del fitxer JSON:
  {
    "terminado":   bool,
    "ruta_docx":   str | null,
    "bloque_actual": str,
    "llm_messages":  [...],          ← dicts purs (no objectes SDK)
    "estados": {
      "tipo_curso":   {...},
      "calendario":   {...},         ← dates com a strings "DD/MM/AAAA" (ja ho fan els estats)
      "prueba_fuego": {              ← fecha → "YYYY-MM-DD", hora_inicio → "HH:MM:SS"
        "fecha": "2026-09-19" | null,
        "hora_inicio": "10:00:00" | null,
        "proveedor": "...",
        "terminado": bool
      },
      "franjas":    {...},
      "orden":      {...},
      "alumnos":    {...},
      "profesores": {...},
      "practicas":  {...}
    }
  }
"""

import json
from datetime import date, time
from pathlib import Path


# ── Serialització dels blocs de content dels missatges LLM ───────────────────

def _bloc_a_dict(bloc) -> dict:
    """
    Converteix un TextBlock / ToolUseBlock del SDK a un dict pur que:
      - és JSON-serialitzable
      - l'API d'Anthropic l'accepta com a entrada en futures crides

    Filtra camps interns del SDK (caller, citations) que l'API no espera.
    """
    if isinstance(bloc, dict):
        return bloc                          # ja és un dict (tool_result o similars)

    t = getattr(bloc, "type", None)
    if t == "text":
        return {"type": "text", "text": bloc.text}
    if t == "tool_use":
        return {"type": "tool_use", "id": bloc.id, "name": bloc.name, "input": bloc.input}

    # Fallback: model_dump filtrant camps interns coneguts
    d = bloc.model_dump() if hasattr(bloc, "model_dump") else vars(bloc)
    return {k: v for k, v in d.items() if k not in ("caller", "citations") and v is not None}


def _serialitzar_llm_messages(messages: list) -> list:
    """
    Converteix llm_messages a una llista de dicts JSON-serialitzables.

    Els missatges d'usuari (content = str o llista de dicts) ja ho són.
    Els missatges d'assistent (content = llista d'objectes SDK) cal convertir-los.
    """
    resultat = []
    for msg in messages:
        content = msg["content"]
        if isinstance(content, str):
            resultat.append({"role": msg["role"], "content": content})
        elif isinstance(content, list):
            resultat.append({
                "role": msg["role"],
                "content": [_bloc_a_dict(b) for b in content],
            })
        else:
            # Cas inesperat: guardem tal qual (si ja és JSON-serialitzable)
            resultat.append({"role": msg["role"], "content": content})
    return resultat


# ── Serialització dels estats (prueba_fuego té date/time Python) ──────────────

def _serialitzar_estados(estados: dict) -> dict:
    """
    Retorna una còpia dels estats amb els date/time de prueba_fuego
    convertits a strings ISO per a JSON.
    """
    import copy
    estats = copy.deepcopy(estados)
    pf = estats.get("prueba_fuego", {})
    if isinstance(pf.get("fecha"), date):
        pf["fecha"] = pf["fecha"].isoformat()          # "2026-09-19"
    if isinstance(pf.get("hora_inicio"), time):
        pf["hora_inicio"] = pf["hora_inicio"].isoformat()  # "10:00:00"
    return estats


def _deserialitzar_estados(estados: dict) -> dict:
    """
    Restaura els date/time de prueba_fuego des de strings ISO.
    """
    pf = estados.get("prueba_fuego", {})
    if isinstance(pf.get("fecha"), str) and pf["fecha"]:
        pf["fecha"] = date.fromisoformat(pf["fecha"])
    if isinstance(pf.get("hora_inicio"), str) and pf["hora_inicio"]:
        pf["hora_inicio"] = time.fromisoformat(pf["hora_inicio"])
    return estados


# ── API pública ───────────────────────────────────────────────────────────────

def guardar_estado(conv_state: dict, terminado: bool, ruta_docx, ruta_fitxer: str) -> None:
    """
    Serialitza el conv_state i els flags a JSON i els desa a ruta_fitxer.

    Crea els directoris intermedis si no existeixen.
    L'escriptura és atòmica (fitxer temporal + rename) per evitar estats truncats.
    """
    payload = {
        "terminado":     terminado,
        "ruta_docx":     str(ruta_docx) if ruta_docx else None,
        "bloque_actual": conv_state["bloque_actual"],
        "llm_messages":  _serialitzar_llm_messages(conv_state["llm_messages"]),
        "estados":       _serialitzar_estados(conv_state["estados"]),
        "chat_messages": conv_state.get("chat_messages", []),
    }

    path = Path(ruta_fitxer)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Escriptura atòmica
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def cargar_estado(ruta_fitxer: str):
    """
    Llegeix el fitxer JSON i reconstrueix (conv_state, terminado, ruta_docx).

    Retorna None si el fitxer no existeix o és il·legible.
    """
    path = Path(ruta_fitxer)
    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    conv_state = {
        "bloque_actual": payload["bloque_actual"],
        "llm_messages":  payload["llm_messages"],    # dicts purs — l'API els accepta
        "estados":       _deserialitzar_estados(payload["estados"]),
        "chat_messages": payload.get("chat_messages", []),
    }

    return conv_state, payload["terminado"], payload["ruta_docx"]


def eliminar_estado(ruta_fitxer: str) -> None:
    """Esborra el fitxer de sessió (quan Rosa vol iniciar un CAP nou)."""
    path = Path(ruta_fitxer)
    if path.exists():
        path.unlink()
