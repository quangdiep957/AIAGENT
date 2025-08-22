# chat_ui.py
import streamlit as st
from graph import build_graph

st.set_page_config(page_title="AI Chat", page_icon="🤖", layout="wide")

# -------- Init --------
if "workflow" not in st.session_state:
    st.session_state.workflow = build_graph()

if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {"Mặc định": []}
if "current_session" not in st.session_state:
    st.session_state.current_session = "Mặc định"
if "attached_files" not in st.session_state:
    # { session_name: [ {"name": str, "bytes": b"..."} ] }
    st.session_state.attached_files = {}

# -------- Sidebar (left menu) --------
st.sidebar.title("💬 Lịch sử chat")

# 📎 Uploader chỉ còn dạng icon trong sidebar
# Dùng CSS để làm dropzone siêu nhỏ, ẩn chữ, chỉ còn icon và vẫn click được
st.sidebar.markdown(
    """
    <style>
    /* Thu gọn uploader trong sidebar thành 1 icon */
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
        margin: 4px 0 12px 0;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        border: none !important;
        background: transparent !important;
        padding: 0 !important;
        width: 28px !important;
        height: 28px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
    }
    /* Ẩn mọi text trong dropzone */
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] > div {
        display: none !important;
    }
    /* Hiển thị icon 📎 ngay trên dropzone (click vào vẫn mở chọn file) */
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]::before {
        content: "📎";
        font-size: 20px;
        line-height: 1;
    }
    </style>
    """,
    unsafe_allow_html=True
)

uploaded = st.sidebar.file_uploader(
    "📎", type=["txt", "pdf", "docx"], label_visibility="collapsed", key="sidebar_uploader"
)
if uploaded is not None:
    files = st.session_state.attached_files.setdefault(st.session_state.current_session, [])
    files.append({"name": uploaded.name, "bytes": uploaded.getvalue()})
    st.sidebar.success(f"Đã đính kèm: {uploaded.name}")

# Danh sách phiên chat
session_names = list(st.session_state.chat_sessions.keys())
chosen = st.sidebar.radio("Chọn phiên:", session_names, index=session_names.index(st.session_state.current_session))
if chosen != st.session_state.current_session:
    st.session_state.current_session = chosen

if st.sidebar.button("➕ Tạo phiên mới"):
    new_name = f"Chat {len(session_names)}"
    st.session_state.chat_sessions[new_name] = []
    st.session_state.attached_files[new_name] = []
    st.session_state.current_session = new_name

# Hiển thị file đã đính kèm (nếu có)
attached = st.session_state.attached_files.get(st.session_state.current_session, [])
if attached:
    with st.sidebar.expander(f"📎 File đính kèm ({len(attached)})", expanded=False):
        for f in attached:
            st.write(f["name"])

# -------- Main chat --------
st.title("🤖 AI Assistant")

messages = st.session_state.chat_sessions[st.session_state.current_session]

# render lịch sử
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Ô nhập luôn nằm dưới cùng (dùng st.chat_input)
prompt = st.chat_input("Nhập tin nhắn của bạn...")

if prompt:
    # lưu + hiện user
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Gọi workflow; truyền kèm danh sách file (nếu muốn xử lý ngữ cảnh theo file)
    file_payload = [{"name": f["name"], "bytes": f["bytes"]} for f in attached]
    result = st.session_state.workflow.invoke({
        "input": prompt,
        "history": messages,
        "files": file_payload,  # tuỳ bạn dùng trong build_graph
    })
    response = result.get("output", "")

    # hiển thị AI
    with st.chat_message("assistant"):
        st.markdown(response)

    messages.append({"role": "assistant", "content": response})
