import os
import uuid
import streamlit as st
from supabase import create_client

from rag_engine import get_client, answer_question, count_documents

st.set_page_config(
    page_title="FinCrece",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------- Estilo estilo ChatGPT, marca FinCrece ----------
st.markdown("""
<style>
    :root {
        --fc-accent: #0B6E4F;        /* verde bosque - crecimiento */
        --fc-accent-dark: #084d38;
        --fc-gold: #C9932E;          /* dorado - dinero, detalle de marca */
        --fc-text: #201F1C;          /* grafito cálido, no negro puro */
        --fc-muted: #6B6459;
        --fc-border: #E7E2D8;        /* borde cálido, no gris frío */
        --fc-bg: #FBFAF7;            /* blanco cálido, no blanco puro */
        --fc-sidebar-bg: #F3F1EA;
    }

    body, .stApp { background: var(--fc-bg); }

    #MainMenu, footer {visibility: hidden; height: 0;}
    header[data-testid="stHeader"] {background: transparent;}
    .block-container {padding-top: 1.5rem; max-width: 760px;}

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        color: var(--fc-text);
    }

    /* ---- Sidebar estilo ChatGPT ---- */
    [data-testid="stSidebar"] {
        background: var(--fc-sidebar-bg);
        border-right: 1px solid var(--fc-border);
    }
    [data-testid="stSidebar"] > div {padding-top: 1rem;}

    .fc-sidebar-logo {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0 0.5rem 1rem 0.5rem;
        margin-bottom: 0.5rem;
        border-bottom: 1px solid var(--fc-border);
    }
    .fc-logo-icon {
        width: 28px; height: 28px; border-radius: 8px;
        background: linear-gradient(135deg, var(--fc-accent-dark), var(--fc-gold));
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
    }
    .fc-wordmark { font-size: 1.05rem; font-weight: 700; letter-spacing: -0.01em; }
    .fc-wordmark span { color: var(--fc-accent); }

    [data-testid="stSidebar"] button {
        text-align: left !important;
        justify-content: flex-start !important;
        border-radius: 8px !important;
        font-size: 0.88rem !important;
    }
    /* Indicador de chat activo (punto dorado, en vez de emoji) */
    .fc-active-dot {
        display: inline-block;
        width: 6px; height: 6px;
        border-radius: 50%;
        background: var(--fc-gold);
        margin-right: 6px;
    }
    [data-testid="stSidebar"] [data-testid="column"]:nth-of-type(2) button {
        justify-content: center !important;
        padding: 0.25rem !important;
        min-height: 0 !important;
    }
    /* Botón "Nuevo chat" resaltado */
    [data-testid="stSidebar"] button[kind="primary"] {
        background: white !important;
        color: var(--fc-text) !important;
        border: 1px solid var(--fc-border) !important;
        font-weight: 500 !important;
    }
    [data-testid="stSidebar"] button[kind="primary"]:hover {
        border-color: var(--fc-accent) !important;
        color: var(--fc-accent) !important;
    }

    /* Header principal (logo centrado, solo visible cuando no hay sidebar visible en mobile) */
    .fc-header {
        display: flex; align-items: center; justify-content: center; gap: 10px;
        padding: 0.25rem 0 1.25rem 0;
        border-bottom: 1px solid var(--fc-border);
        margin-bottom: 1.5rem;
    }

    [data-testid="stChatMessage"] {
        background: transparent;
        padding: 0.85rem 0;
        border-bottom: 1px solid #f3f4f6;
    }
    [data-testid="stChatMessageAvatarUser"] { background: var(--fc-text) !important; }
    [data-testid="stChatMessageAvatarAssistant"] { background: var(--fc-accent) !important; }

    [data-testid="stChatInput"] {
        border-radius: 26px;
        border: 1px solid var(--fc-border);
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }
    [data-testid="stChatInput"]:focus-within { border-color: var(--fc-accent); }

    .fc-main-logo {
        display: flex; align-items: center; justify-content: center; gap: 10px;
        padding-bottom: 0.5rem;
    }
    .fc-main-logo .fc-logo-icon { width: 34px; height: 34px; border-radius: 10px; }
    .fc-main-logo .fc-wordmark { font-size: 1.4rem; }

    .fc-empty { text-align: center; color: var(--fc-muted); padding: 1rem 1rem 3rem 1rem; }
    .fc-empty h2 { color: var(--fc-text); font-size: 1.4rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ---------- Credenciales ----------
gemini_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
supabase_url = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
supabase_key = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))

missing = [name for name, val in [
    ("GEMINI_API_KEY", gemini_key),
    ("SUPABASE_URL", supabase_url),
    ("SUPABASE_KEY", supabase_key),
] if not val]

if missing:
    st.error(f"Faltan estas variables en Secrets: {', '.join(missing)}")
    st.stop()

client = get_client(gemini_key)
supabase = create_client(supabase_url, supabase_key)

try:
    doc_count = count_documents(supabase)
except Exception as e:
    st.error("No se pudo conectar con la base de datos.")
    st.code(str(e))
    st.stop()

if doc_count == 0:
    st.warning("Todavía no hay documentos indexados. Corre `index_documents.py` primero.")
    st.stop()

# ---------- Estado: múltiples chats (estilo ChatGPT) ----------
def new_chat_id():
    return str(uuid.uuid4())

if "chats" not in st.session_state:
    first_id = new_chat_id()
    st.session_state.chats = {first_id: {"title": "Nuevo chat", "messages": []}}
    st.session_state.current_chat_id = first_id

def create_new_chat():
    cid = new_chat_id()
    st.session_state.chats[cid] = {"title": "Nuevo chat", "messages": []}
    st.session_state.current_chat_id = cid

# ---------- Sidebar: logo + nuevo chat + historial ----------
with st.sidebar:
    st.markdown("""
    <div class="fc-sidebar-logo">
        <div class="fc-logo-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 17L9 11L13 15L21 7" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M15 7H21V13" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>
        <div class="fc-wordmark">FIN<span>CRECE</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.button("＋ Nuevo chat", use_container_width=True, type="primary", on_click=create_new_chat)

    st.markdown("<div style='height: 0.75rem'></div>", unsafe_allow_html=True)
    st.caption("Chats anteriores")

    # Mostrar chats más recientes primero
    for cid in reversed(list(st.session_state.chats.keys())):
        chat = st.session_state.chats[cid]
        label = chat["title"]
        is_active = cid == st.session_state.current_chat_id

        col_select, col_delete = st.columns([5, 1])
        with col_select:
            display_label = f"● {label}" if is_active else label
            if st.button(
                display_label,
                key=f"chat_btn_{cid}",
                use_container_width=True,
            ):
                st.session_state.current_chat_id = cid
                st.rerun()
        with col_delete:
            if st.button("🗑️", key=f"chat_del_{cid}", help="Eliminar chat"):
                del st.session_state.chats[cid]
                # Si borramos el chat activo (o ya no queda ninguno), crear/activar otro
                if not st.session_state.chats:
                    create_new_chat()
                elif cid == st.session_state.current_chat_id:
                    st.session_state.current_chat_id = list(st.session_state.chats.keys())[-1]
                st.rerun()

# ---------- Chat activo ----------
current = st.session_state.chats[st.session_state.current_chat_id]
messages = current["messages"]

if not messages:
    st.markdown("""
    <div class="fc-main-logo">
        <div class="fc-logo-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 17L9 11L13 15L21 7" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M15 7H21V13" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>
        <div class="fc-wordmark">FIN<span>CRECE</span></div>
    </div>
    <div class="fc-empty">
        <h2>¿En qué puedo ayudarte?</h2>
    </div>
    """, unsafe_allow_html=True)

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Escribe tu mensaje...")

if question:
    messages.append({"role": "user", "content": question})
    if current["title"] == "Nuevo chat":
        current["title"] = question[:40] + ("..." if len(question) > 40 else "")

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                result = answer_question(client, supabase, question)
            except Exception as e:
                st.error("Ocurrió un error al generar la respuesta.")
                st.code(str(e))
                st.stop()

            answer = result["answer"]
            sources = result["sources"]
            st.markdown(answer)
            if sources:
                st.caption("📎 " + ", ".join(sources))

    full_response = answer + ("\n\n📎 " + ", ".join(sources) if sources else "")
    messages.append({"role": "assistant", "content": full_response})
    st.rerun()
