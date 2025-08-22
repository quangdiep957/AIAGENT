"""
Demo tích hợp tất cả các tools
Workflow hoàn chỉnh: Upload -> Extract -> OCR -> Embed -> Search
"""

import os
from datetime import datetime
from tools import FileUploadTool, FileReaderTool, OCRTool, EmbeddingTool, VectorSearchTool
from services import EmbeddingService
from models import DocumentModel, DocumentUtils
from database import DatabaseManager

class DocumentProcessingPipeline:
    """Pipeline xử lý documents hoàn chỉnh"""
    
    def __init__(self):
        """Khởi tạo pipeline với tất cả tools"""
        self.upload_tool = FileUploadTool()
        self.reader_tool = FileReaderTool()
        self.ocr_tool = OCRTool()
        self.embedding_tool = EmbeddingTool()
        self.search_tool = VectorSearchTool()
        self.embedding_service = EmbeddingService()
        self.db_manager = DatabaseManager()
    
    def process_document(self, file_path: str, metadata: dict = None) -> dict:
        """
        Xử lý document hoàn chỉnh từ upload đến embedding
        
        Args:
            file_path (str): Đường dẫn file
            metadata (dict): Metadata bổ sung
            
        Returns:
            dict: Kết quả xử lý
        """
        try:
            print(f"🚀 Bắt đầu xử lý file: {os.path.basename(file_path)}")
            
            # 1. Upload file
            print("📁 Step 1: Upload file...")
            upload_result = self.upload_tool.upload_file(file_path, metadata)
            if not upload_result["success"]:
                return {
                    "success": False,
                    "step": "upload",
                    "error": upload_result["errors"]
                }
            
            file_document = upload_result["document"]
            file_id = upload_result["file_id"]
            uploaded_path = file_document["absolute_path"]
            file_type = file_document["file_type"]
            
            print(f"✅ Upload thành công. File ID: {file_id}")
            
            # 2. Extract content
            print("📖 Step 2: Extract content...")
            content = ""
            
            if file_type in ["pdf", "docx", "doc", "txt", "md"]:
                # Đọc file text-based
                read_result = self.reader_tool.read_file(uploaded_path)
                if read_result["success"]:
                    if file_type == "pdf":
                        content = read_result["total_content"]
                    elif file_type in ["docx", "doc"]:
                        content = read_result["total_content"]
                    else:  # text files
                        content = read_result["content"]
                    print(f"✅ Extracted {len(content)} characters")
                else:
                    print(f"❌ File reading failed: {read_result['error']}")
                    return {
                        "success": False,
                        "step": "extract",
                        "error": read_result["error"]
                    }
            
            elif file_type == "image":
                # OCR cho ảnh
                ocr_result = self.ocr_tool.extract_text_from_image(uploaded_path)
                if ocr_result["success"]:
                    content = ocr_result["text"]
                    print(f"✅ OCR extracted {len(content)} characters")
                else:
                    print(f"❌ OCR failed: {ocr_result['error']}")
                    return {
                        "success": False,
                        "step": "ocr",
                        "error": ocr_result["error"]
                    }
            
            if not content.strip():
                return {
                    "success": False,
                    "step": "extract",
                    "error": "Không thể extract content từ file"
                }
            
            # 3. Process embeddings
            print("🧠 Step 3: Create embeddings...")
            processing_result = self.embedding_service.process_file_content(
                file_id=file_id,
                content=content,
                metadata={
                    **metadata,
                    "file_type": file_type,
                    "original_filename": file_document["filename"]
                }
            )
            
            if not processing_result["success"]:
                return {
                    "success": False,
                    "step": "embedding",
                    "error": processing_result["error"]
                }
            
            print(f"✅ Created {processing_result['total_chunks']} embedding chunks")
            
            # 4. Test search
            print("🔍 Step 4: Test search...")
            test_query = content[:100] + "..."  # Dùng đoạn đầu content để test
            search_result = self.search_tool.similarity_search(
                query_text=test_query,
                limit=3
            )
            
            search_found = 0
            if search_result["success"]:
                search_found = len(search_result["results"])
                print(f"✅ Search test: Found {search_found} similar documents")
            
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
                    "search_test_results": search_found
                },
                "processing_time": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "step": "pipeline",
                "error": f"Pipeline error: {str(e)}"
            }
    
    def search_content(self, query: str, filters: dict = None, limit: int = 5) -> dict:
        """
        Tìm kiếm content
        
        Args:
            query (str): Query text
            filters (dict): Filters
            limit (int): Số kết quả
            
        Returns:
            dict: Kết quả tìm kiếm
        """
        try:
            print(f"🔍 Searching for: '{query}'")
            
            # Vector search
            result = self.search_tool.similarity_search(
                query_text=query,
                limit=limit,
                filters=filters
            )
            
            if result["success"]:
                print(f"✅ Found {len(result['results'])} results")
                
                # Format kết quả
                formatted_results = []
                for i, doc in enumerate(result["results"], 1):
                    formatted_results.append({
                        "rank": i,
                        "score": doc.get("similarity_score", 0),
                        "content_type": doc.get("type", "unknown"),
                        "topic": doc.get("topic", "N/A"),
                        "content_preview": doc.get("content", "")[:200] + "...",
                        "metadata": doc.get("metadata", {})
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "results": formatted_results,
                    "total_found": len(formatted_results)
                }
            else:
                return result
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Search error: {str(e)}"
            }
    
    def get_dashboard_stats(self) -> dict:
        """
        Lấy thống kê cho dashboard
        
        Returns:
            dict: Thống kê tổng quan
        """
        try:
            # Stats từ embedding service
            processing_stats = self.embedding_service.get_processing_stats()
            
            # Stats từ vector search tool
            collection_stats = self.search_tool.get_collection_stats()
            
            return {
                "success": True,
                "processing": processing_stats.get("data", {}) if processing_stats["success"] else {},
                "collection": collection_stats.get("data", {}) if collection_stats["success"] else {},
                "tools_status": {
                    "upload_tool": "ready",
                    "reader_tool": "ready", 
                    "ocr_tool": "ready" if hasattr(self.ocr_tool, 'easyocr_reader') else "limited",
                    "embedding_tool": "ready",
                    "search_tool": "ready"
                },
                "last_updated": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Stats error: {str(e)}"
            }

def demo_pipeline():
    """Demo chạy pipeline"""
    print("=" * 60)
    print("🤖 DOCUMENT PROCESSING PIPELINE DEMO")
    print("=" * 60)
    
    try:
        # Khởi tạo pipeline
        pipeline = DocumentProcessingPipeline()
        
        # Tạo file test
        test_file = "demo_document.txt"
        test_content = """
        English Grammar Lesson: Present Perfect Tense
        
        The Present Perfect tense is used to describe actions that happened at an unspecified time in the past or actions that started in the past and continue to the present.
        
        Formation: have/has + past participle
        
        Examples:
        1. I have visited London three times.
        2. She has lived here for five years.
        3. They have finished their homework.
        
        Key words: already, just, yet, ever, never, since, for
        
        Practice exercises:
        - Complete the sentences with the correct form
        - Choose between Present Perfect and Past Simple
        """
        
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)
        
        # 1. Xử lý document
        print("\\n1️⃣ PROCESSING DOCUMENT")
        print("-" * 30)
        
        result = pipeline.process_document(
            file_path=test_file,
            metadata={
                "subject": "English",
                "grade": "intermediate",
                "source": "demo"
            }
        )
        
        if result["success"]:
            print("✅ Document processing completed!")
            print(f"   📁 File: {result['file_info']['filename']}")
            print(f"   📝 Content type: {result['content_info']['content_type']}")
            print(f"   🎯 Topic: {result['content_info']['topic']}")
            print(f"   📊 Chunks: {result['processing_info']['total_chunks']}")
            print(f"   🏷️  Tags: {', '.join(result['content_info']['tags'])}")
        else:
            print(f"❌ Processing failed at {result['step']}: {result['error']}")
            return
        
        # 2. Test search
        print("\\n2️⃣ TESTING SEARCH")
        print("-" * 30)
        
        test_queries = [
            "present perfect tense",
            "grammar exercises",
            "English lesson"
        ]
        
        for query in test_queries:
            search_result = pipeline.search_content(query, limit=3)
            
            if search_result["success"]:
                print(f"\\n🔍 Query: '{query}'")
                print(f"   Found: {search_result['total_found']} results")
                
                for result in search_result["results"][:2]:  # Show top 2
                    print(f"   #{result['rank']} (Score: {result['score']:.3f}) - {result['content_type']}: {result['topic']}")
            else:
                print(f"❌ Search failed for '{query}': {search_result['error']}")
        
        # 3. Dashboard stats
        print("\\n3️⃣ DASHBOARD STATS")
        print("-" * 30)
        
        stats = pipeline.get_dashboard_stats()
        if stats["success"]:
            tools_status = stats["tools_status"]
            print("🛠️  Tools Status:")
            for tool, status in tools_status.items():
                status_icon = "✅" if status == "ready" else "⚠️"
                print(f"   {status_icon} {tool}: {status}")
        
        print("\\n✅ Demo completed successfully!")
        
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
            
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        
        # Cleanup
        if 'test_file' in locals() and os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    demo_pipeline()
