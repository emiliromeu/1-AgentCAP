import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from anthropic import Anthropic

from agente.cerebro import procesar_turno, crear_estado_conversacion
from agente.persistencia import guardar_estado, cargar_estado, eliminar_estado

load_dotenv()

st.set_page_config(
    page_title="Generador de Horarios CAP - Autoescola Olivella",
    page_icon="🚛",
    layout="centered",
)

st.title("Generador de Horarios CAP")
st.caption("Autoescola Olivella")

_BASE = Path(__file__).resolve().parent   # directori del projecte, sigui on sigui

BENVINGUDA = (
    "Hola Rosa, soy el asistente para generar horarios CAP. "
    "Vamos a empezar. ¿El curso es de mercancías o de viajeros?"
)
RUTA_SESSIO = str(_BASE / "datos" / "sesion.json")


@st.cache_resource
def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("No se encontró ANTHROPIC_API_KEY. Comprueba el fichero .env.")
        st.stop()
    return Anthropic(api_key=api_key)


def _init_limpio():
    """Inicialitza session_state amb una conversa nova."""
    st.session_state.chat_messages = [{"role": "assistant", "content": BENVINGUDA}]
    st.session_state.conv_state    = crear_estado_conversacion()
    st.session_state.terminado     = False
    st.session_state.ruta_docx     = None
    st.session_state.recuperant    = False   # flag: mostrant el diàleg de recuperació


# ── Primera càrrega: decidir si iniciar net o oferir recuperar ────────────────
if "chat_messages" not in st.session_state:
    sessio = cargar_estado(RUTA_SESSIO)

    if sessio is None:
        # Cap sessió guardada → inici net
        _init_limpio()

    else:
        conv_state, terminado, ruta_docx = sessio

        if terminado:
            # Última sessió ja completada → inici net (no té sentit continuar-la)
            eliminar_estado(RUTA_SESSIO)
            _init_limpio()

        else:
            # Hi ha una sessió a mitges → oferir continuar o reiniciar
            # Carreguem el conv_state però marquem que estem en diàleg de recuperació
            st.session_state.conv_state    = conv_state
            st.session_state.terminado     = False
            st.session_state.ruta_docx     = ruta_docx
            st.session_state.recuperant    = True
            # Els chat_messages els recuperem des del JSON (es guarden a conv_state["chat_messages"])
            st.session_state.chat_messages = conv_state.get("chat_messages", [
                {"role": "assistant", "content": BENVINGUDA}
            ])


# ── Diàleg de recuperació ─────────────────────────────────────────────────────
if st.session_state.get("recuperant", False):
    st.info(
        "👋 Parece que la última vez dejaste un CAP a medias. "
        "¿Quieres continuar donde lo dejaste, o empezar uno nuevo?"
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Continuar donde lo dejé", use_container_width=True):
            st.session_state.recuperant = False
            st.rerun()
    with col2:
        if st.button("🗑️ Empezar un CAP nuevo", use_container_width=True):
            eliminar_estado(RUTA_SESSIO)
            _init_limpio()
            st.rerun()
    st.stop()   # No mostrem res més mentre es decideix


# ── Mostra l'historial de missatges ──────────────────────────────────────────
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ── Botó de descàrrega + "Empezar un CAP nuevo" si ja ha acabat ──────────────
if st.session_state.terminado:
    if st.session_state.ruta_docx and os.path.exists(st.session_state.ruta_docx):
        with open(st.session_state.ruta_docx, "rb") as f:
            st.download_button(
                label="⬇️ Descargar horario CAP (.docx)",
                data=f.read(),
                file_name="horario_cap.docx",
                mime=(
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                ),
            )

    if st.button("🔄 Empezar un CAP nuevo", use_container_width=True):
        eliminar_estado(RUTA_SESSIO)
        _init_limpio()
        st.rerun()

# ── Input de l'usuari (desactivat quan la conversa ha acabat) ─────────────────
if not st.session_state.terminado:
    if entrada := st.chat_input("Escribe tu respuesta…"):
        client = get_client()

        st.session_state.chat_messages.append({"role": "user", "content": entrada})

        with st.spinner("Pensando…"):
            resultat = procesar_turno(entrada, st.session_state.conv_state, client)

        st.session_state.conv_state = resultat["estado"]

        if resultat["terminado"]:
            st.session_state.terminado = True
            st.session_state.ruta_docx = resultat["ruta_docx"]

        if resultat["respuesta"]:
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": resultat["respuesta"]}
            )

        # Desa l'estat a disc (inclou chat_messages per poder restaurar el xat visual)
        conv_amb_xat = {
            **st.session_state.conv_state,
            "chat_messages": st.session_state.chat_messages,
        }
        guardar_estado(
            conv_amb_xat,
            st.session_state.terminado,
            st.session_state.ruta_docx,
            RUTA_SESSIO,
        )

        st.rerun()
