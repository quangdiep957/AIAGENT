# main.py - AI Tutor with Advanced Knowledge Management
import streamlit as st
import io
import tempfile
import os
from agents import create_agent
from database import DatabaseManager

st.set_page_config(page_title="AI Tutor", page_icon="🎓", layout="wide")

# -------- Init --------
if "agent" not in st.session_state:
    st.session_state.agent = create_agent()

if "db_manager" not in st.session_state:
    st.session_state.db_manager = DatabaseManager()

if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {"Mặc định": []}
if "current_session" not in st.session_state:
    st.session_state.current_session = "Mặc định"
if "attached_files" not in st.session_state:
    # { session_name: [ {"name": str, "bytes": b"..."} ] }
    st.session_state.attached_files = {}

def save_chat_to_knowledge_base(content: str, session_name: str):
    """Lưu nội dung tiếng Anh từ chat vào knowledge base"""
    try:
        # Kiểm tra xem có phải tiếng Anh không (đơn giản)
        english_indicators = ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'it', 'you', 'that', 'he', 'was', 'for', 'on', 'are', 'as', 'with', 'his', 'they']
        content_lower = content.lower()
        english_count = sum(1 for word in english_indicators if word in content_lower)
        
        if english_count >= 3 and len(content.split()) >= 10:  # Có ít nhất 3 từ tiếng Anh và 10 từ
            from datetime import datetime
            
            # Lưu vào collection chat_knowledge
            chat_data = {
                "content": content,
                "source": "chat_conversation",
                "timestamp": datetime.now().isoformat(),
                "word_count": len(content.split()),
                "type": "chat_content",
                "session_name": session_name
            }
            
            collection = st.session_state.db_manager.db["chat_knowledge"]
            result = collection.insert_one(chat_data)
            
            # Tạo embedding cho nội dung
            from services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            
            embedding_result = embedding_service.create_embedding_for_text(
                text=content,
                metadata={
                    "source": "chat",
                    "chat_id": str(result.inserted_id),
                    "timestamp": chat_data["timestamp"],
                    "session_name": session_name
                }
            )
            
            if embedding_result["success"]:
                return True
                
    except Exception as e:
        st.error(f"Lỗi lưu vào knowledge base: {e}")
    return False

def get_chat_history(session_name: str = None) -> str:
    """Lấy lịch sử chat của session"""
    if session_name is None:
        session_name = st.session_state.current_session
    
    messages = st.session_state.chat_sessions.get(session_name, [])
    history = []
    
    for msg in messages[-10:]:  # Lấy 10 tin nhắn gần nhất
        role = "Người dùng" if msg["role"] == "user" else "AI Tutor"
        history.append(f"{role}: {msg['content']}")
    
    return "\n\n".join(history)

def generate_ai_response(user_input: str) -> str:
    """Tạo response từ AI agent với context từ lịch sử chat và knowledge base"""
    try:
        # Lấy lịch sử chat
        chat_history = get_chat_history()
        
        # Tạo prompt có context
        enhanced_prompt = f"""
        Lịch sử chat gần đây:
        {chat_history}
        
        Câu hỏi hiện tại: {user_input}
        
        Quy tắc trả lời:
        1. Tìm kiếm thông tin từ knowledge base (nếu có liên quan)
        2. Sử dụng lịch sử chat để hiểu context
        3. Giữ nguyên nội dung tiếng Anh trong tài liệu
        4. Giải thích bằng tiếng Việt
        5. Luôn trả lời hoàn chỉnh, không để raw JSON action
        """
        
        # Gọi agent với timeout và error handling
        try:
            response = st.session_state.agent.invoke(
                {'input': enhanced_prompt},
                config={"max_execution_time": 30}  # Timeout 30s
            )
            
            if isinstance(response, dict):
                if 'output' in response:
                    output = response['output']
                    # Clean escape characters và JSON artifacts
                    clean_output = output.replace('\\\\n', '\n').replace('\\\\\"', '"')
                    # Remove any JSON action artifacts
                    if '{"action":' in clean_output or '"action_input":' in clean_output:
                        # Nếu còn JSON artifacts, trả về response đơn giản
                        return "Xin lỗi, tôi đang gặp sự cố kỹ thuật. Bạn có thể thử lại câu hỏi không?"
                    return clean_output
                else:
                    return str(response)
            else:
                return str(response)
                
        except Exception as agent_error:
            st.error(f"Agent error: {agent_error}")
            # Fallback response
            return f"Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi: {user_input}. Bạn có thể thử lại hoặc diễn đạt khác không?"
            
    except Exception as e:
        return f"❌ Xin lỗi, có lỗi xảy ra: {str(e)}"

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
    "📎", type=["txt", "pdf", "docx", "png", "jpg", "jpeg"], label_visibility="collapsed", key="sidebar_uploader"
)
if uploaded is not None:
    # Lưu file tạm và xử lý
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded.name.split('.')[-1]}") as tmp_file:
        tmp_file.write(uploaded.getvalue())
        tmp_file_path = tmp_file.name
    
    # Gọi agent để xử lý file
    with st.sidebar.spinner("Đang xử lý file..."):
        result = st.session_state.agent.invoke({
            'input': f'upload_and_process_document {tmp_file_path}|{uploaded.name}'
        })
        
        if isinstance(result, dict) and 'output' in result:
            result_text = result['output']
        else:
            result_text = str(result)
    
    # Cleanup
    os.unlink(tmp_file_path)
    
    if "✅" in result_text:
        st.sidebar.success(f"Đã xử lý: {uploaded.name}")
        # Thêm vào attached files để hiển thị
        files = st.session_state.attached_files.setdefault(st.session_state.current_session, [])
        files.append({"name": uploaded.name, "bytes": uploaded.getvalue()})
    else:
        st.sidebar.error("Lỗi xử lý file")

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
st.title("🎓 AI Tutor - English Learning Assistant")

# Sidebar tools
with st.sidebar.expander("🛠️ Công cụ AI", expanded=False):
    if st.button("📊 Thống kê tài liệu"):
        with st.spinner("Đang lấy thống kê..."):
            result = st.session_state.agent.invoke({'input': 'get_document_summary'})
            if isinstance(result, dict) and 'output' in result:
                st.info(result['output'])
            else:
                st.info(str(result))
    
    if st.button("🔍 Tìm kiếm tài liệu"):
        search_query = st.text_input("Nhập từ khóa tìm kiếm:")
        if search_query:
            with st.spinner("Đang tìm kiếm..."):
                result = st.session_state.agent.invoke({'input': f'search_documents {search_query}'})
                if isinstance(result, dict) and 'output' in result:
                    st.info(result['output'])
                else:
                    st.info(str(result))

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

    # Tự động lưu nội dung tiếng Anh vào knowledge base
    if len(prompt.split()) >= 10:  # Chỉ lưu câu dài
        save_chat_to_knowledge_base(prompt, st.session_state.current_session)

    # Tạo response từ AI agent
    with st.chat_message("assistant"):
        with st.spinner("AI đang suy nghĩ..."):
            response = generate_ai_response(prompt)
        st.markdown(response)

    messages.append({"role": "assistant", "content": response})
    
    # Lưu response tiếng Anh vào knowledge base nếu có
    if len(response.split()) >= 10:
        save_chat_to_knowledge_base(response, st.session_state.current_session)
