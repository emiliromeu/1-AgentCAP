import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from anthropic import Anthropic

from agente.cerebro import procesar_turno, crear_estado_conversacion
from agente.persistencia import guardar_estado, cargar_estado, eliminar_estado

load_dotenv()

ESTILO_ESPACIAL = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
.stApp {
    background-color: #0A0E1A;
    background-image:
        radial-gradient(circle at 15% 20%, rgba(91, 141, 238, 0.10) 0%, transparent 45%),
        radial-gradient(circle at 85% 75%, rgba(120, 90, 200, 0.08) 0%, transparent 50%),
        radial-gradient(circle at 50% 100%, rgba(30, 50, 90, 0.15) 0%, transparent 60%);
    background-attachment: fixed;
}
.stApp::before {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        radial-gradient(1.5px 1.5px at 20% 30%, rgba(255,255,255,0.9), transparent),
        radial-gradient(1.5px 1.5px at 60% 70%, rgba(255,255,255,0.7), transparent),
        radial-gradient(2px 2px at 80% 20%, rgba(180,210,255,0.9), transparent),
        radial-gradient(1.5px 1.5px at 35% 85%, rgba(255,255,255,0.6), transparent),
        radial-gradient(2px 2px at 90% 55%, rgba(180,210,255,0.8), transparent),
        radial-gradient(1px 1px at 10% 60%, rgba(255,255,255,0.7), transparent),
        radial-gradient(1.5px 1.5px at 45% 15%, rgba(255,255,255,0.8), transparent),
        radial-gradient(1px 1px at 75% 40%, rgba(255,255,255,0.6), transparent),
        radial-gradient(2px 2px at 25% 50%, rgba(180,210,255,0.7), transparent),
        radial-gradient(1px 1px at 55% 90%, rgba(255,255,255,0.7), transparent),
        radial-gradient(1.5px 1.5px at 5% 25%, rgba(255,255,255,0.6), transparent),
        radial-gradient(1px 1px at 95% 15%, rgba(255,255,255,0.7), transparent);
    background-repeat: no-repeat;
    pointer-events: none;
    z-index: 0;
    animation: drift 40s ease-in-out infinite alternate;
}
.stApp, .stMarkdown, .stMarkdown p, [data-testid="stChatMessageContent"], [data-testid="stChatMessageContent"] p {
    color: #E8EAF0 !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}
h1 { color: #FFFFFF !important; font-weight: 600 !important; letter-spacing: -0.02em !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #7B8AA8 !important; }
[data-testid="stChatMessage"] {
    background: rgba(20, 28, 48, 0.55) !important;
    border: 1px solid rgba(91, 141, 238, 0.18) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(8px);
    padding: 16px 20px !important;
    margin-bottom: 12px !important;
}
[data-testid="stChatInput"] {
    background: rgba(15, 22, 40, 0.85) !important;
    border: 1px solid rgba(91, 141, 238, 0.30) !important;
    border-radius: 14px !important;
}
[data-testid="stChatInput"] textarea { color: #E8EAF0 !important; }
[data-testid="stChatInput"] textarea::placeholder { color: #5A6A88 !important; }
.stButton > button, .stDownloadButton > button {
    background: linear-gradient(135deg, #5B8DEE 0%, #4A6FD0 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 14px rgba(91, 141, 238, 0.25) !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(91, 141, 238, 0.40) !important;
}
[data-testid="stAlert"] {
    background: rgba(91, 141, 238, 0.10) !important;
    border: 1px solid rgba(91, 141, 238, 0.30) !important;
    border-radius: 14px !important;
    color: #E8EAF0 !important;
}
.stSpinner > div { border-top-color: #5B8DEE !important; }
.main .block-container { position: relative; z-index: 1; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent !important;}
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
    background: #0A0E1A !important;
}

/* Movimiento sutil de las estrellas */
@keyframes drift {
    0%   { transform: translate(0, 0); }
    100% { transform: translate(-40px, -30px); }
}

/* Brillo tech en las burbujas del asistente */
[data-testid="stChatMessage"] {
    box-shadow: 0 0 20px rgba(91, 141, 238, 0.08) !important;
}

/* Pulso sutil de brillo en los botones */
.stButton > button, .stDownloadButton > button {
    animation: glow 3s ease-in-out infinite;
}
@keyframes glow {
    0%, 100% { box-shadow: 0 4px 14px rgba(91, 141, 238, 0.25); }
    50%      { box-shadow: 0 4px 22px rgba(91, 141, 238, 0.45); }
}
</style>
'''

st.set_page_config(
    page_title="Generador de Horarios CAP - Autoescola Olivella",
    page_icon="🚛",
    layout="centered",
)

st.markdown(ESTILO_ESPACIAL, unsafe_allow_html=True)

st.markdown('''
<div style="text-align: center; padding: 1.5rem 0 1rem 0;">
    <div style="font-size: 2.6rem; font-weight: 700; letter-spacing: -0.03em;
                background: linear-gradient(135deg, #FFFFFF 0%, #5B8DEE 100%);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                background-clip: text; line-height: 1.1; margin-bottom: 0.3rem;">
        Generador de Horarios CAP
    </div>
    <div style="font-size: 0.95rem; color: #7B8AA8; font-weight: 400; letter-spacing: 0.08em;
                text-transform: uppercase;">
        Autoescola Olivella
    </div>
    <div style="width: 60px; height: 2px; margin: 1rem auto 0 auto;
                background: linear-gradient(90deg, transparent, #5B8DEE, transparent);"></div>
</div>
''', unsafe_allow_html=True)

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
    avatar = "🛰️" if msg["role"] == "assistant" else "🧑‍🚀"
    with st.chat_message(msg["role"], avatar=avatar):
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
