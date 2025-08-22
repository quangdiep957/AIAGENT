import streamlit as st
import uuid
import os
import asyncio
import time
from datetime import datetime

# Import các tools đã tạo
from tools import FileUploadTool, FileReaderTool, OCRTool, EmbeddingTool, VectorSearchTool
from services import EmbeddingService
from models import DocumentModel, DocumentUtils
from database import DatabaseManager

st.set_page_config(page_title="AI Tutor", page_icon="🤖", layout="wide")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Khởi tạo các tools
@st.cache_resource
def init_tools():
    """Khởi tạo các tools cho document processing"""
    try:
        upload_tool = FileUploadTool(upload_dir=UPLOAD_DIR)
        reader_tool = FileReaderTool()
        ocr_tool = OCRTool()
        embedding_tool = EmbeddingTool()
        search_tool = VectorSearchTool()
        embedding_service = EmbeddingService()
        db_manager = DatabaseManager()
        
        return {
            "upload_tool": upload_tool,
            "reader_tool": reader_tool,
            "ocr_tool": ocr_tool,
            "embedding_tool": embedding_tool,
            "search_tool": search_tool,
            "embedding_service": embedding_service,
            "db_manager": db_manager,
            "status": "success"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Khởi tạo tools
tools = init_tools()

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
if "processing_files" not in st.session_state:
    st.session_state.processing_files = {}
if "uploaded_documents" not in st.session_state:
    st.session_state.uploaded_documents = []


def process_uploaded_file(uploaded_file, session_id):
    """Xử lý file đã upload"""
    try:
        if tools["status"] != "success":
            return {
                "success": False,
                "error": "Tools chưa được khởi tạo đúng cách"
            }
        
        # Lưu file tạm
        temp_file_path = os.path.join(UPLOAD_DIR, f"temp_{uuid.uuid4().hex}_{uploaded_file.name}")
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Upload sử dụng FileUploadTool
        upload_result = tools["upload_tool"].upload_file(
            file_path=temp_file_path,
            metadata={
                "session_id": session_id,
                "original_name": uploaded_file.name,
                "upload_source": "streamlit_ui"
            }
        )
        
        if not upload_result["success"]:
            return {
                "success": False,
                "error": f"Upload failed: {', '.join(upload_result['errors'])}"
            }
        
        file_document = upload_result["document"]
        file_id = upload_result["file_id"]
        
        # Extract content dựa trên loại file
        content = ""
        extraction_method = ""
        
        file_type = file_document["file_type"]
        file_path = file_document["absolute_path"]
        
        if file_type in ["pdf", "docx", "doc", "txt", "md"]:
            # Đọc file text-based
            read_result = tools["reader_tool"].read_file(file_path)
            if read_result["success"]:
                if file_type == "pdf":
                    content = read_result["total_content"]
                elif file_type in ["docx", "doc"]:
                    content = read_result["total_content"]
                else:  # text files
                    content = read_result["content"]
                extraction_method = "file_reader"
            else:
                return {
                    "success": False,
                    "error": f"Không thể đọc file: {read_result['error']}"
                }
        
        elif file_type == "image":
            # OCR cho ảnh
            print(f"🔍 Starting OCR for image: {file_path}")
            ocr_result = tools["ocr_tool"].extract_text_from_image(file_path)
            print(f"📊 OCR result: {ocr_result}")
            
            if ocr_result["success"]:
                content = ocr_result["text"]
                extraction_method = "ocr"
                print(f"✅ OCR successful. Text length: {len(content)} characters")
            else:
                print(f"❌ OCR failed: {ocr_result['error']}")
                return {
                    "success": False,
                    "error": f"OCR failed: {ocr_result['error']}"
                }
        
        if not content or not content.strip():
            print(f"⚠️ Warning: No content extracted. Content length: {len(content) if content else 0}")
            return {
                "success": False,
                "error": "Không thể trích xuất nội dung từ file. File có thể rỗng hoặc không chứa text có thể đọc được."
            }
        
        # Tạo embeddings
        processing_result = tools["embedding_service"].process_file_content(
            file_id=file_id,
            content=content,
            metadata={
                "session_id": session_id,
                "extraction_method": extraction_method,
                "file_type": file_type
            }
        )
        
        if not processing_result["success"]:
            return {
                "success": False,
                "error": f"Embedding processing failed: {processing_result['error']}"
            }
        
        # Cleanup temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        return {
            "success": True,
            "file_id": file_id,
            "file_info": {
                "filename": file_document["filename"],
                "file_type": file_type,
                "file_size": file_document["file_size"]
            },
            "content_info": {
                "length": len(content),
                "word_count": len(content.split()),
                "content_type": processing_result["content_type"],
                "topic": processing_result["topic"],
                "difficulty": processing_result["difficulty_level"],
                "tags": processing_result["tags"]
            },
            "processing_info": {
                "total_chunks": processing_result["total_chunks"],
                "total_tokens": processing_result["total_tokens"],
                "extraction_method": extraction_method
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Lỗi xử lý file: {str(e)}"
        }


def search_relevant_content(query, limit=3):
    """Tìm kiếm nội dung liên quan từ database"""
    try:
        if tools["status"] != "success":
            return []
        
        search_result = tools["search_tool"].similarity_search(
            query_text=query,
            limit=limit,
            similarity_threshold=0.3
        )
        
        if search_result["success"] and search_result["results"]:
            relevant_docs = []
            for doc in search_result["results"]:
                relevant_docs.append({
                    "content": doc["content"][:300] + "..." if len(doc["content"]) > 300 else doc["content"],
                    "similarity": doc["similarity_score"],
                    "type": doc.get("type", "unknown"),
                    "topic": doc.get("topic", "N/A")
                })
            return relevant_docs
        
        return []
        
    except Exception as e:
        print(f"Search error: {e}")
        return []


def generate_ai_response(user_message, relevant_docs=None):
    """Tạo phản hồi AI với context từ documents"""
    try:
        if relevant_docs:
            context = "\n\n".join([f"📄 {doc['type']}: {doc['content']}" for doc in relevant_docs])
            response = f"""
📚 **Dựa trên tài liệu đã upload, tôi tìm thấy thông tin liên quan:**

{context}

---

💡 **Trả lời cho câu hỏi của bạn:**
{user_message}

Dựa trên nội dung trên, đây là gợi ý học tập phù hợp với câu hỏi của bạn.
            """
        else:
            response = f"""
🤖 **AI Tutor phản hồi:**

Tôi đã nhận được câu hỏi: "{user_message}"

Hiện tại chưa có tài liệu nào được upload để tham khảo. Bạn có thể:
- Upload tài liệu học tập (PDF, Word, hình ảnh)
- Đặt câu hỏi cụ thể về chủ đề bạn quan tâm

Tôi sẽ giúp bạn học tập hiệu quả hơn! 📘
            """
        
        return response
        
    except Exception as e:
        return f"❌ Lỗi khi tạo phản hồi: {str(e)}"


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
            st.markdown("### 📤 Upload File")
            uploaded_files = st.file_uploader(
                "Chọn file để upload:", 
                type=['pdf', 'docx', 'doc', 'txt', 'md', 'png', 'jpg', 'jpeg'],
                accept_multiple_files=True,
                key="main_uploader"
            )
            
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                    
                    # Check if file is already being processed
                    if file_key not in st.session_state.processing_files:
                        st.session_state.processing_files[file_key] = "processing"
                        
                        # Show processing indicator
                        with st.spinner(f"Đang xử lý file: {uploaded_file.name}..."):
                            result = process_uploaded_file(uploaded_file, st.session_state.current_session)
                            
                            if result["success"]:
                                st.session_state.processing_files[file_key] = "completed"
                                st.session_state.uploaded_documents.append(result)
                                
                                # Add file message to chat
                                current["messages"].append({
                                    "role": "user", 
                                    "type": "file", 
                                    "content": f"📄 Đã upload: {uploaded_file.name} ({result['file_info']['file_type']})\n"
                                              f"📊 Chủ đề: {result['content_info']['topic']}\n"
                                              f"📏 {result['content_info']['word_count']:,} từ"
                                })
                                
                                # AI response about the uploaded file
                                ai_response = f"""
📚 **Đã nhận và xử lý file: {uploaded_file.name}**

✅ **Thông tin file:**
- Loại: {result['file_info']['file_type'].upper()}
- Kích thước: {result['file_info']['file_size']:,} bytes
- Nội dung: {result['content_info']['word_count']:,} từ

🔍 **Phân tích nội dung:**
- Chủ đề: {result['content_info']['topic']}
- Độ khó: {result['content_info']['difficulty']}
- Tags: {', '.join(result['content_info']['tags'])}

💡 Tôi đã tạo embedding cho {result['processing_info']['total_chunks']} phần nội dung. 
Bây giờ bạn có thể đặt câu hỏi về nội dung trong file này!
                                """
                                current["messages"].append({
                                    "role": "assistant", 
                                    "type": "text", 
                                    "content": ai_response
                                })
                                
                                # Update session name if needed
                                if current["name"] is None:
                                    current["name"] = uploaded_file.name
                                
                                st.success(f"✅ Đã xử lý: {uploaded_file.name}")
                                
                            else:
                                st.session_state.processing_files[file_key] = "error"
                                st.error(f"❌ Lỗi: {result['error']}")
                                
                                # Add error message to chat
                                current["messages"].append({
                                    "role": "assistant", 
                                    "type": "text", 
                                    "content": f"❌ **Lỗi xử lý file: {uploaded_file.name}**\n\n{result['error']}"
                                })
            
            # Show uploaded documents summary
            if st.session_state.uploaded_documents:
                st.markdown("### 📚 Tài liệu đã upload")
                for doc in st.session_state.uploaded_documents:
                    st.write(f"📄 {doc['file_info']['filename']} - {doc['content_info']['topic']}")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("✅ Hoàn thành", key="finish_upload"):
                    st.session_state.show_uploader = False
                    st.rerun()
            with col2:
                if st.button("❌ Đóng", key="close_upload"):
                    st.session_state.show_uploader = False
                    st.rerun()

    with cols[1]:
        prompt = st.chat_input("✍️ Nhập câu hỏi của bạn...")
        if prompt:
            # add user message
            current["messages"].append({"role": "user", "type": "text", "content": prompt})
            if current["name"] is None:
                current["name"] = prompt

            # Search for relevant content from uploaded documents
            relevant_docs = search_relevant_content(prompt, limit=3)
            
            # Generate AI response with context
            ai_response = generate_ai_response(prompt, relevant_docs)
            current["messages"].append({"role": "assistant", "type": "text", "content": ai_response})
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
