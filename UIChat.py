import streamlit as st
import uuid
import os

st.set_page_config(page_title="AI Tutor", page_icon="🤖", layout="wide")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Custom Dark CSS ---
st.markdown("""
<style>
/* Toàn bộ nền */
.stApp {
    background-color: #1e1e2e;
    color: #e5e5e5;
    font-family: 'Segoe UI', sans-serif;
}

/* Header */
.header {
    text-align: center;
    padding: 20px 0;
    font-size: 26px;
    font-weight: bold;
    color: #60a5fa;
}

/* Chat container */
.chat-bubble {
    padding: 12px 18px;
    margin: 8px 0;
    border-radius: 18px;
    max-width: 80%;
    line-height: 1.5;
    word-wrap: break-word;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.2);
}
.chat-user {
    background-color: #3b82f6;
    color: white;
    margin-left: auto;
}
.chat-ai {
    background-color: #2e2e3e;
    color: #f3f4f6;
    margin-right: auto;
}

/* Input bar cố định cuối */
.input-container {
    position: fixed;
    bottom: 0;
    left: 18%;
    width: 82%;
    background: #2a2a3a;
    border-top: 1px solid #3f3f46;
    padding: 10px 15px;
    border-radius: 12px 12px 0 0;
}
</style>
""", unsafe_allow_html=True)

# --- State ---
if "sessions" not in st.session_state:
    st.session_state.sessions = {}  
if "current_session" not in st.session_state:
    sid = str(uuid.uuid4())
    st.session_state.sessions[sid] = {"name": None, "messages": []}
    st.session_state.current_session = sid
if "show_uploader" not in st.session_state:
    st.session_state.show_uploader = False


def new_session():
    # chỉ tạo mới nếu phiên hiện tại đã có nội dung
    current = st.session_state.sessions.get(st.session_state.current_session, None)
    if current and not current["messages"]:
        st.toast("📌 Hãy nhập câu hỏi trước khi tạo phiên mới")
        return  
    sid = str(uuid.uuid4())
    st.session_state.sessions[sid] = {"name": None, "messages": []}
    st.session_state.current_session = sid


def delete_session(sid):
    if sid in st.session_state.sessions:
        del st.session_state.sessions[sid]
        if not st.session_state.sessions:
            new_session()
        else:
            st.session_state.current_session = list(st.session_state.sessions.keys())[0]


def shorten_name(text, max_len=18):
    return text if len(text) <= max_len else text[:max_len] + "..."


# --- Sidebar ---
st.sidebar.header("📚 AI Tutor")
st.sidebar.button("➕ Bắt đầu phiên mới", on_click=new_session)

st.sidebar.subheader("📜 Lịch sử học tập")
for sid, sess in list(st.session_state.sessions.items()):
    if sid == st.session_state.current_session and sess["name"] is None:
        continue  
    col1, col2 = st.sidebar.columns([4, 1])
    display_name = sess["name"] or "Chưa đặt tên"
    display_name = shorten_name(display_name)
    if col1.button(display_name, key=f"open-{sid}"):
        st.session_state.current_session = sid
    if col2.button("❌", key=f"del-{sid}"):
        delete_session(sid)
        st.rerun()


# --- Main layout ---
st.markdown("<div class='header'>🤖 AI Tutor – Người bạn đồng hành học tập</div>", unsafe_allow_html=True)

chat_container = st.container()
input_container = st.container()

current = st.session_state.sessions[st.session_state.current_session]

with chat_container:
    if not current["messages"]:
        st.markdown(
            "<div style='text-align:center; font-size:18px; color:gray; margin-top:100px;'>"
            "Xin chào 👋, tôi là <b>AI Tutor</b>.<br/>"
            "Bạn muốn học gì hôm nay? 📘"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        for m in current["messages"]:
            role_class = "chat-user" if m["role"] == "user" else "chat-ai"
            st.markdown(f"<div class='chat-bubble {role_class}'>{m['content']}</div>", unsafe_allow_html=True)


with input_container:
    st.markdown("<div class='input-container'>", unsafe_allow_html=True)
    cols = st.columns([0.1, 0.9])
    with cols[0]:
        if st.button("📎", key="icon-upload"):
            st.session_state.show_uploader = not st.session_state.show_uploader
        if st.session_state.show_uploader:
            uploaded = st.file_uploader("Upload file", type=None, label_visibility="collapsed", key="hidden_uploader")
            if uploaded:
                file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{uploaded.name}")
                with open(file_path, "wb") as f:
                    f.write(uploaded.getbuffer())
                current["messages"].append({"role": "user", "type": "file", "content": f"📎 {uploaded.name}"})
                if current["name"] is None:
                    current["name"] = uploaded.name
                st.session_state.show_uploader = False
                st.rerun()

    with cols[1]:
        prompt = st.chat_input("✍️ Nhập câu hỏi của bạn...")
        if prompt:
            # add user message
            current["messages"].append({"role": "user", "type": "text", "content": prompt})
            if current["name"] is None:
                current["name"] = prompt

            # mock AI trả lời
            reply = f"📘 Đây là gợi ý học tập từ AI Tutor:<br/>{prompt[::-1]}"
            current["messages"].append({"role": "assistant", "type": "text", "content": reply})
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
