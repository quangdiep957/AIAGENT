"""
Chat Knowledge Tool - Tool để quản lý lịch sử chat và knowledge base
"""

from langchain.tools import tool
from typing import Dict, Any
import json
from datetime import datetime
import tempfile
import os

from database import DatabaseManager
from services.embedding_service import EmbeddingService

# Khởi tạo services
db_manager = DatabaseManager()
embedding_service = EmbeddingService()

@tool  
def save_chat_content(content: str) -> str:
    """
    Lưu nội dung tiếng Anh từ chat vào knowledge base
    
    Args:
        content: Nội dung cần lưu (văn bản tiếng Anh)
    
    Returns:
        Kết quả lưu trữ
    """
    try:
        # Kiểm tra nội dung có phải tiếng Anh không
        english_indicators = ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'it', 'you', 'that', 'he', 'was', 'for', 'on', 'are', 'as', 'with', 'his', 'they']
        content_lower = content.lower()
        english_count = sum(1 for word in english_indicators if word in content_lower)
        
        if english_count < 3 or len(content.split()) < 10:
            return "⏭️ Nội dung quá ngắn hoặc không phải tiếng Anh, bỏ qua lưu trữ"
        
        # Tạo metadata cho chat content
        chat_data = {
            "content": content,
            "source": "chat_conversation",
            "timestamp": datetime.now().isoformat(),
            "word_count": len(content.split()),
            "type": "chat_content"
        }
        
        # Lưu vào collection đặc biệt cho chat
        collection = db_manager.db["chat_knowledge"]
        result = collection.insert_one(chat_data)
        
        # Tạo embedding cho nội dung
        embedding_result = embedding_service.create_embedding_for_text(
            text=content,
            metadata={
                "source": "chat",
                "chat_id": str(result.inserted_id),
                "timestamp": chat_data["timestamp"]
            }
        )
        
        if embedding_result["success"]:
            return f"✅ Đã lưu nội dung tiếng Anh vào knowledge base ({len(content.split())} từ)"
        else:
            return f"⚠️ Đã lưu nội dung nhưng không tạo được embedding: {embedding_result['error']}"
            
    except Exception as e:
        return f"❌ Lỗi lưu chat content: {str(e)}"

@tool
def get_chat_history_summary(session_name: str = "current") -> str:
    """
    Lấy tóm tắt lịch sử chat từ database
    
    Args:
        session_name: Tên session chat cần lấy lịch sử
    
    Returns:
        Tóm tắt lịch sử chat
    """
    try:
        collection = db_manager.db["chat_knowledge"]
        
        # Lấy chat gần đây
        recent_chats = list(collection.find(
            {"source": "chat_conversation"},
            {"content": 1, "timestamp": 1, "word_count": 1}
        ).sort("timestamp", -1).limit(20))
        
        if not recent_chats:
            return "📝 Chưa có lịch sử chat nào được lưu trong knowledge base"
        
        total_words = sum(chat.get("word_count", 0) for chat in recent_chats)
        
        # Tạo tóm tắt
        summary = f"""📚 **Tóm tắt lịch sử chat:**

🔢 Số đoạn chat đã lưu: {len(recent_chats)}
📝 Tổng số từ: {total_words:,}
🕐 Chat gần nhất: {recent_chats[0]['timestamp'][:19] if recent_chats else 'N/A'}

💡 Các nội dung này đã được lưu vào knowledge base và có thể được sử dụng để trả lời câu hỏi!"""

        return summary
        
    except Exception as e:
        return f"❌ Lỗi lấy lịch sử chat: {str(e)}"

@tool
def search_chat_and_documents(query: str) -> str:
    """
    Tìm kiếm thông tin từ cả lịch sử chat và tài liệu trong knowledge base
    
    Args:
        query: Câu hỏi hoặc từ khóa cần tìm
    
    Returns:
        Kết quả tìm kiếm từ nhiều nguồn
    """
    try:
        from tools.vector_search_tool import VectorSearchTool
        search_tool = VectorSearchTool()
        
        # Tìm kiếm trong documents (tool có sẵn)
        doc_results = search_tool.similarity_search(
            query_text=query,
            limit=2,
            similarity_threshold=0.3
        )
        
        # Tìm kiếm trong chat history
        chat_collection = db_manager.db["chat_knowledge"]
        
        # Tạo text index nếu chưa có
        try:
            chat_collection.create_index([("content", "text")])
        except:
            pass  # Index đã tồn tại
        
        chat_docs = list(chat_collection.find(
            {"$text": {"$search": query}},
            {"content": 1, "timestamp": 1}
        ).limit(3))
        
        # Kết hợp kết quả
        results = []
        
        # Thêm kết quả từ documents
        if doc_results["success"] and doc_results["results"]:
            results.append("🔍 **Từ tài liệu đã upload:**")
            for i, doc in enumerate(doc_results["results"], 1):
                content_preview = doc['content'][:300] + "..." if len(doc['content']) > 300 else doc['content']
                results.append(f"""
📄 **Tài liệu {i}** (Độ tương đồng: {doc['similarity_score']:.2f})
📚 Chủ đề: {doc.get('topic', 'N/A')}
📝 Nội dung: {content_preview}
""")
        
        # Thêm kết quả từ chat history  
        if chat_docs:
            results.append("\n💬 **Từ lịch sử chat:**")
            for i, chat in enumerate(chat_docs, 1):
                content_preview = chat['content'][:300] + "..." if len(chat['content']) > 300 else chat['content']
                results.append(f"""
🗨️ **Chat {i}** ({chat['timestamp'][:19]})
📝 Nội dung: {content_preview}
""")
        
        if not results:
            return "🔍 Không tìm thấy thông tin liên quan trong cả tài liệu và lịch sử chat. Hãy thử từ khóa khác!"
        
        return "\n".join(results) + "\n\n💡 Dựa trên thông tin trên, tôi có thể giúp bạn trả lời câu hỏi chi tiết hơn."
        
    except Exception as e:
        return f"❌ Lỗi tìm kiếm: {str(e)}"

@tool
def auto_save_english_content(content_with_session: str) -> str:
    """
    Tự động phát hiện và lưu nội dung tiếng Anh vào knowledge base
    
    Args:
        content_with_session: Nội dung cần lưu, format: "content|session_name" hoặc chỉ "content"
    
    Returns:
        Kết quả xử lý
    """
    try:
        # Parse input
        if "|" in content_with_session:
            content, session_name = content_with_session.split("|", 1)
        else:
            content = content_with_session
            session_name = "default"
        # Kiểm tra xem có phải tiếng Anh không (đơn giản)
        english_indicators = ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'it', 'you', 'that', 'he', 'was', 'for', 'on', 'are', 'as', 'with', 'his', 'they']
        content_lower = content.lower()
        english_count = sum(1 for word in english_indicators if word in content_lower)
        
        if english_count >= 3 and len(content.split()) >= 10:  # Có ít nhất 3 từ tiếng Anh và 10 từ
            # Tạo file tạm và upload vào knowledge base
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            temp_file.write(content)
            temp_file.close()
            
            # Import tool để xử lý file
            from tools.file_upload_tool import FileUploadTool
            from tools.file_reader_tool import FileReaderTool
            
            upload_tool = FileUploadTool(upload_dir="uploads")
            reader_tool = FileReaderTool()
            
            # Upload file
            upload_result = upload_tool.upload_file(
                file_path=temp_file.name,
                metadata={
                    "original_name": f"chat_content_{session_name}.txt",
                    "upload_source": "auto_chat_save",
                    "session": session_name
                }
            )
            
            # Cleanup temp file
            os.unlink(temp_file.name)
            
            if upload_result["success"]:
                file_id = upload_result["file_id"]
                
                # Tạo embeddings
                processing_result = embedding_service.process_file_content(
                    file_id=file_id,
                    content=content,
                    metadata={
                        "extraction_method": "auto_chat_save",
                        "file_type": "chat_text",
                        "session": session_name
                    }
                )
                
                if processing_result["success"]:
                    return f"✅ Đã tự động lưu nội dung tiếng Anh vào knowledge base ({len(content.split())} từ)"
                else:
                    return f"⚠️ Đã lưu file nhưng không tạo được embedding: {processing_result['error']}"
            else:
                return f"❌ Không thể lưu content: {', '.join(upload_result['errors'])}"
        else:
            return "⏭️ Nội dung không đủ tiêu chí để lưu vào knowledge base"
            
    except Exception as e:
        return f"❌ Lỗi auto save: {str(e)}"
