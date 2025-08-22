# agents.py
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from tools import get_weather, calculate_sum, semantic_search, wiki_search, wiki_summary
import config  # ensure .env is loaded (load_dotenv runs in config)
from langchain.tools import tool
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

# Import các tools hiện có
from tools import FileUploadTool, FileReaderTool, OCRTool, EmbeddingTool, VectorSearchTool
from tools import save_chat_content, get_chat_history_summary, search_chat_and_documents, auto_save_english_content
from tools import search_web_with_evaluation, generate_llm_response_for_query
from services import EmbeddingService
from database import DatabaseManager

# Khởi tạo các tools
upload_tool = FileUploadTool(upload_dir="uploads")
reader_tool = FileReaderTool()
ocr_tool = OCRTool()
embedding_tool = EmbeddingTool()
search_tool = VectorSearchTool()
embedding_service = EmbeddingService()
db_manager = DatabaseManager()


@tool
def upload_and_process_document(file_info: str) -> str:
    """
    Upload và xử lý tài liệu (PDF, Word, Image) để lưu vào database và tạo embeddings

    Args:
        file_info: Thông tin file dạng "file_path|file_name" (ví dụ: "/path/to/file.pdf|document.pdf")

    Returns:
        Kết quả xử lý file
    """
    try:
        # Parse file info
        if "|" not in file_info:
            return "❌ Format không đúng. Vui lòng sử dụng format: file_path|file_name"

        file_path, file_name = file_info.split("|", 1)

        # Upload file
        upload_result = upload_tool.upload_file(
            file_path=file_path,
            metadata={
                "original_name": file_name,
                "upload_source": "ai_agent"
            }
        )

        if not upload_result["success"]:
            return f"❌ Upload thất bại: {', '.join(upload_result['errors'])}"

        file_document = upload_result["document"]
        file_id = upload_result["file_id"]

        # Extract content dựa trên loại file
        content = ""
        extraction_method = ""
        file_type = file_document["file_type"]
        file_path_abs = file_document["absolute_path"]

        if file_type in ["pdf", "docx", "doc", "txt", "md"]:
            # Đọc file text-based
            read_result = reader_tool.read_file(file_path_abs)
            if read_result["success"]:
                if file_type == "pdf":
                    content = read_result["total_content"]
                elif file_type in ["docx", "doc"]:
                    content = read_result["total_content"]
                else:  # text files
                    content = read_result["content"]
                extraction_method = "file_reader"
            else:
                return f"❌ Không thể đọc file: {read_result['error']}"

        elif file_type == "image":
            # OCR cho ảnh
            ocr_result = ocr_tool.extract_text_from_image(file_path_abs)
            if ocr_result["success"]:
                content = ocr_result["text"]
                extraction_method = "ocr"
            else:
                return f"❌ OCR thất bại: {ocr_result['error']}"

        if not content or not content.strip():
            return "❌ Không thể trích xuất nội dung từ file"

        # Tạo embeddings
        processing_result = embedding_service.process_file_content(
            file_id=file_id,
            content=content,
            metadata={
                "extraction_method": extraction_method,
                "file_type": file_type
            }
        )

        if not processing_result["success"]:
            return f"❌ Tạo embedding thất bại: {processing_result['error']}"

        return f"""✅ Đã xử lý thành công file: {file_name}
📊 Thông tin:
- Loại file: {file_type.upper()}
- Số từ: {len(content.split()):,}
- Chủ đề: {processing_result['topic']}
- Độ khó: {processing_result['difficulty_level']}
- Số chunks: {processing_result['total_chunks']}
- Tags: {', '.join(processing_result['tags'])}

Tài liệu đã được lưu vào database và sẵn sàng để tìm kiếm!"""

    except Exception as e:
        return f"❌ Lỗi xử lý file: {str(e)}"


@tool
def search_documents(query: str) -> str:
    """
    Tìm kiếm tài liệu dựa trên nội dung câu hỏi

    Args:
        query: Câu hỏi hoặc từ khóa cần tìm

    Returns:
        Nội dung tài liệu liên quan được tìm thấy
    """
    try:
        limit = 3  # Set default limit
        search_result = search_tool.similarity_search(
            query_text=query,
            limit=limit,
            similarity_threshold=0.3
        )

        if not search_result["success"]:
            return f"❌ Lỗi tìm kiếm: {search_result['error']}"

        if not search_result["results"]:
            return "🔍 Không tìm thấy tài liệu nào liên quan đến câu hỏi này. Bạn có thể upload thêm tài liệu để tôi hỗ trợ tốt hơn."

        # Format kết quả tìm kiếm
        results = []
        for i, doc in enumerate(search_result["results"], 1):
            # Giữ nguyên nội dung tiếng Anh, chỉ thêm thông tin metadata bằng tiếng Việt
            content_preview = doc['content'][:500]
            if len(doc['content']) > 500:
                content_preview += "..."

            results.append(f"""
📄 **Tài liệu {i}** (Độ tương đồng: {doc['similarity_score']:.2f})
📚 Chủ đề: {doc.get('topic', 'N/A')}
📝 Nội dung: {content_preview}
""")

        return f"""🔍 **Tìm thấy {len(search_result['results'])} tài liệu liên quan:**

{''.join(results)}

💡 Dựa trên những tài liệu tiếng Anh trên, tôi có thể giúp bạn học tập hiệu quả."""

    except Exception as e:
        return f"❌ Lỗi tìm kiếm: {str(e)}"


@tool
def get_document_summary(dummy_input: str = "") -> str:
    """
    Lấy tóm tắt về các tài liệu đã upload trong database
    
    Returns:
        Thống kê tài liệu trong database
    """
    try:
        collections = db_manager.get_collections()

        if "document_embeddings" in collections:
            collection = db_manager.db["document_embeddings"]
            total_docs = collection.count_documents({})

            # Lấy thống kê theo chủ đề
            pipeline = [
                {"$group": {"_id": "$topic", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ]
            topics = list(collection.aggregate(pipeline))

            topic_summary = "\n".join([f"- {topic['_id']}: {topic['count']} tài liệu" for topic in topics])

            return f"""📊 **Thống kê tài liệu trong database:**

📚 Tổng số tài liệu: {total_docs}

🔍 **Top chủ đề:**
{topic_summary}

💡 Bạn có thể hỏi tôi về bất kỳ chủ đề nào trong danh sách trên!"""
        else:
            return "📚 Chưa có tài liệu nào được upload. Hãy upload tài liệu để tôi có thể hỗ trợ bạn!"

    except Exception as e:
        return f"❌ Lỗi lấy thống kê: {str(e)}"

@tool
def smart_search_and_answer(query: str) -> str:
    """
    Tìm kiếm thông minh: Knowledge Base -> Web Search -> LLM Response
    
    Args:
        query: Câu hỏi hoặc từ khóa cần tìm
    
    Returns:
        Kết quả tìm kiếm và trả lời tối ưu
    """
    try:
        # Bước 1: Tìm trong Knowledge Base trước
        kb_results = search_tool.similarity_search(
            query_text=query,
            limit=3,
            similarity_threshold=0.4  # Ngưỡng cao hơn để đảm bảo chất lượng
        )
        
        if kb_results["success"] and kb_results["results"]:
            # Có kết quả trong KB, đánh giá chất lượng
            best_score = max(result['similarity_score'] for result in kb_results["results"])
            
            if best_score >= 0.6:  # Kết quả KB tốt
                results_text = []
                for i, doc in enumerate(kb_results["results"], 1):
                    content_preview = doc['content'][:400] + "..." if len(doc['content']) > 400 else doc['content']
                    results_text.append(f"""
📄 **Tài liệu {i}** (Độ tương đồng: {doc['similarity_score']:.2f})
📚 Chủ đề: {doc.get('topic', 'N/A')}
📝 Nội dung: {content_preview}
""")
                
                return f"""✅ **Tìm thấy trong Knowledge Base**

🔍 **Tìm thấy {len(kb_results['results'])} tài liệu liên quan:**

{''.join(results_text)}

💡 **Nguồn:** Knowledge Base chất lượng cao
**Trạng thái:** knowledge_base_found"""
        
        # Bước 2: KB không có hoặc chất lượng thấp -> Tìm kiếm web
        from tools.web_search_tool import search_web_with_evaluation, generate_llm_response_for_query
        web_result = search_web_with_evaluation(query)
        
        if "search_results_ready" in web_result:
            return web_result
        elif "llm_response_needed" in web_result:
            # Bước 3: Web search không tốt -> Dùng LLM
            llm_response = generate_llm_response_for_query(query)
            return llm_response
        else:
            # Fallback
            return web_result
            
    except Exception as e:
        # Final fallback
        from tools.web_search_tool import generate_llm_response_for_query
        llm_response = generate_llm_response_for_query(query)
        return f"""⚠️ **Lỗi trong quá trình tìm kiếm: {str(e)}**

{llm_response}"""

def get_llm():
    """Khởi tạo ChatOpenAI model"""
    return ChatOpenAI(model="gpt-4.1", temperature=0.3)


def create_agent():
    """Tạo AI agent với các tools tích hợp (đầu vào đơn giản 1 tham số)"""
    llm = get_llm()
    # Chỉ dùng các tool 1 tham số để tương thích ZeroShotAgent
    tools = [
        get_weather,
        calculate_sum,
        semantic_search,
        wiki_search,
        wiki_summary,
        upload_and_process_document,
        search_documents,
        get_document_summary,
        plan_study_auto,
        plan_study_schedule,
        smart_search_and_answer,
        search_web_with_evaluation,
        generate_llm_response_for_query
    ]


    agent_instructions = (
        "Bạn là trợ lý học tập. Khi người dùng có ý định xin 'lộ trình', 'kế hoạch', 'lịch học' hoặc tương tự, "
        "hãy GỌI công cụ plan_study_auto và truyền NGUYÊN VĂN câu hỏi làm đầu vào.\n"
        "Khi cần kiến thức tham chiếu, LUÔN ưu tiên gọi semantic_search trước để tìm trong tài liệu người dùng; "
        "chỉ gọi wiki_search nếu semantic_search trả về 'NO_HITS'."
    )

    # Tạo agent đơn giản với ReAct
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        agent_kwargs={
            "system_message": agent_instructions
        },
        handle_parsing_errors=True
    )
    return agent
