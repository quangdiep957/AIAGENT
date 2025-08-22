# agents.py
import os
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
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
        print(f"🔍 DEBUG: Starting upload process with input: {file_info}")
        
        # Parse file info
        if "|" not in file_info:
            print(f"❌ DEBUG: Invalid format - missing | separator")
            return "❌ Format không đúng. Vui lòng sử dụng format: file_path|file_name"
        
        file_path, file_name = file_info.split("|", 1)
        print(f"🔍 DEBUG: Parsed - file_path: {file_path}, file_name: {file_name}")
        
        # Check file exists
        if not os.path.exists(file_path):
            print(f"❌ DEBUG: File not found at path: {file_path}")
            return f"❌ File không tồn tại: {file_path}"
        
        print(f"🔍 DEBUG: File size: {os.path.getsize(file_path):,} bytes")
        
        # Upload file
        print(f"🔍 DEBUG: Starting file upload...")
        upload_result = upload_tool.upload_file(
            file_path=file_path,
            metadata={
                "original_name": file_name,
                "upload_source": "ai_agent"
            }
        )
        
        print(f"🔍 DEBUG: Upload result success: {upload_result.get('success')}")
        if not upload_result["success"]:
            error_msg = f"❌ Upload thất bại: {', '.join(upload_result.get('errors', ['Unknown error']))}"
            print(f"❌ DEBUG: {error_msg}")
            return error_msg
        
        file_document = upload_result["document"]
        file_id = upload_result["file_id"]
        print(f"🔍 DEBUG: Upload successful - file_id: {file_id}")
        
        # Extract content dựa trên loại file
        content = ""
        extraction_method = ""
        file_type = file_document["file_type"]
        file_path_abs = file_document["absolute_path"]
        
        print(f"🔍 DEBUG: File type detected: {file_type}")
        print(f"🔍 DEBUG: Absolute path: {file_path_abs}")
        
        if file_type in ["pdf", "docx", "doc", "txt", "md", "text"]:
            # Đọc file text-based
            print(f"🔍 DEBUG: Reading {file_type} file...")
            read_result = reader_tool.read_file(file_path_abs)
            print(f"🔍 DEBUG: Read result success: {read_result.get('success')}")
            
            if read_result["success"]:
                if file_type == "pdf":
                    content = read_result.get("total_content", read_result.get("content", ""))
                elif file_type in ["docx", "doc"]:
                    content = read_result.get("total_content", read_result.get("content", ""))
                else:  # text files
                    content = read_result["content"]
                extraction_method = "file_reader"
                print(f"🔍 DEBUG: Content extracted - length: {len(content)} chars")
            else:
                error_msg = f"❌ Không thể đọc file: {read_result.get('error', 'Unknown read error')}"
                print(f"❌ DEBUG: {error_msg}")
                return error_msg
        
        elif file_type == "image":
            # OCR cho ảnh
            print(f"🔍 DEBUG: Processing image with OCR...")
            ocr_result = ocr_tool.extract_text_from_image(file_path_abs)
            print(f"🔍 DEBUG: OCR result success: {ocr_result.get('success')}")
            
            if ocr_result["success"]:
                content = ocr_result["text"]
                extraction_method = "ocr"
                print(f"🔍 DEBUG: OCR content extracted - length: {len(content)} chars")
            else:
                error_msg = f"❌ OCR thất bại: {ocr_result.get('error', 'Unknown OCR error')}"
                print(f"❌ DEBUG: {error_msg}")
                return error_msg
        else:
            error_msg = f"❌ Loại file không được hỗ trợ: {file_type}"
            print(f"❌ DEBUG: {error_msg}")
            return error_msg
        
        if not content or not content.strip():
            print(f"❌ DEBUG: Empty content after extraction")
            return "❌ Không thể trích xuất nội dung từ file"
        
        print(f"🔍 DEBUG: Content validation passed - {len(content.split())} words")
        
        # Tạo embeddings
        print(f"🔍 DEBUG: Creating embeddings...")
        processing_result = embedding_service.process_file_content(
            file_id=file_id,
            content=content,
            metadata={
                "extraction_method": extraction_method,
                "file_type": file_type
            }
        )
        
        print(f"🔍 DEBUG: Embedding result success: {processing_result.get('success')}")
        
        if not processing_result["success"]:
            error_msg = f"❌ Tạo embedding thất bại: {processing_result.get('error', 'Unknown embedding error')}"
            print(f"❌ DEBUG: {error_msg}")
            return error_msg
        
        print(f"🔍 DEBUG: Processing completed successfully!")
        success_msg = f"""✅ Đã xử lý thành công file: {file_name}
📊 Thông tin:
- Loại file: {file_type.upper()}
- Số từ: {len(content.split()):,}
- Chủ đề: {processing_result.get('topic', 'N/A')}
- Độ khó: {processing_result.get('difficulty_level', 'N/A')}
- Số chunks: {processing_result.get('total_chunks', 'N/A')}
- Tags: {', '.join(processing_result.get('tags', []))}

Tài liệu đã được lưu vào database và sẵn sàng để tìm kiếm!"""
        print(f"🔍 DEBUG: Returning success message")
        return success_msg
        
    except Exception as e:
        error_msg = f"❌ Lỗi xử lý file: {str(e)}"
        print(f"❌ DEBUG: Exception occurred: {error_msg}")
        import traceback
        print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
        return error_msg

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
    
    Args:
        dummy_input: Tham số không sử dụng (để đảm bảo single input)
    
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
    Tìm kiếm thông minh và trả lời câu hỏi theo luồng: Knowledge Base -> Web Search -> LLM Response
    Đây là tool chính cho mọi câu hỏi tìm kiếm thông tin.
    
    Args:
        query: Câu hỏi hoặc từ khóa cần tìm
    
    Returns:
        Kết quả tìm kiếm và trả lời tối ưu
    """
    try:
        print(f"🔍 SMART SEARCH: Starting search for query: {query}")
        
        # Bước 1: Tìm trong Knowledge Base trước
        print(f"🔍 SMART SEARCH: Step 1 - Searching Knowledge Base...")
        kb_results = search_tool.similarity_search(
            query_text=query,
            limit=3,
            similarity_threshold=0.4  # Ngưỡng cao hơn để đảm bảo chất lượng
        )
        
        if kb_results["success"] and kb_results["results"]:
            # Có kết quả trong KB, đánh giá chất lượng
            best_score = max(result['similarity_score'] for result in kb_results["results"])
            print(f"🔍 SMART SEARCH: KB found {len(kb_results['results'])} results, best score: {best_score:.3f}")
            
            # Kiểm tra độ relevance thực sự bằng cách xem content có liên quan không
            best_result = max(kb_results["results"], key=lambda x: x['similarity_score'])
            content_sample = best_result['content'][:200].lower()
            query_lower = query.lower()
            
            # Từ khóa relevance check
            relevant_keywords = False
            query_words = set(query_lower.split())
            content_words = set(content_sample.split())
            overlap = len(query_words.intersection(content_words))
            
            if overlap >= 2 or best_score >= 0.7:  # Tăng threshold cho KB
                relevant_keywords = True
                
            print(f"🔍 SMART SEARCH: Relevance check - overlap: {overlap}, relevant: {relevant_keywords}")
            
            if best_score >= 0.7 and relevant_keywords:  # Tăng threshold từ 0.6 lên 0.7
                print(f"✅ SMART SEARCH: Using Knowledge Base results (high quality)")
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
**Độ tin cậy:** Cao"""
        
        # Bước 2: KB không có hoặc chất lượng thấp -> Tìm kiếm web
        print(f"🔍 SMART SEARCH: Step 2 - KB insufficient, searching web...")
        from tools.web_search_tool import search_web_with_evaluation, generate_llm_response_for_query
        web_result = search_web_with_evaluation(query)
        
        print(f"🔍 SMART SEARCH: Web search completed")
        
        if "search_results_ready" in web_result:
            print(f"✅ SMART SEARCH: Using web search results")
            return web_result
        elif "llm_response_needed" in web_result:
            # Bước 3: Web search không tốt -> Dùng LLM
            print(f"🔍 SMART SEARCH: Step 3 - Web insufficient, using LLM fallback...")
            llm_response = generate_llm_response_for_query(query)
            print(f"✅ SMART SEARCH: Using LLM fallback response")
            return llm_response
        else:
            # Fallback
            print(f"✅ SMART SEARCH: Using web result as fallback")
            return web_result
            
    except Exception as e:
        # Final fallback
        print(f"❌ SMART SEARCH: Exception occurred: {str(e)}")
        from tools.web_search_tool import generate_llm_response_for_query
        llm_response = generate_llm_response_for_query(query)
        return f"""⚠️ **Lỗi trong quá trình tìm kiếm: {str(e)}**

{llm_response}"""

def get_llm():
    """Khởi tạo ChatOpenAI model"""
    return ChatOpenAI(model="gpt-4.1", temperature=0.3)

def create_agent():
    """Tạo AI agent với các tools tích hợp"""
    llm = get_llm()
    
    # Chỉ expose các tools chính, ẩn tools phụ để agent không gọi trực tiếp
    tools = [
        upload_and_process_document,
        smart_search_and_answer,  # Tool chính cho search - sẽ handle KB -> Web -> LLM internally
        get_document_summary
    ]

    # Tạo agent đơn giản với ReAct
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False,
        handle_parsing_errors=True
    )
    return agent
