"""
Embedding Service - Service layer cho embedding operations
Quản lý việc tạo và lưu trữ embeddings
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from tools.embedding_tool import EmbeddingTool
from tools.vector_search_tool import VectorSearchTool
from models.document_model import DocumentModel, DocumentUtils
from database import DatabaseManager

class EmbeddingService:
    """Service quản lý embedding operations"""
    
    def __init__(self, 
                 db_manager: DatabaseManager = None,
                 embedding_tool: EmbeddingTool = None):
        """
        Khởi tạo EmbeddingService
        
        Args:
            db_manager (DatabaseManager): Database manager
            embedding_tool (EmbeddingTool): Embedding tool
        """
        self.db_manager = db_manager or DatabaseManager()
        self.embedding_tool = embedding_tool or EmbeddingTool()
        
        # Collections
        self.files_collection = "uploaded_files"
        self.embeddings_collection = "document_embeddings"
        self.logs_collection = "processing_logs"
    
    def process_file_content(self, 
                           file_id: str, 
                           content: str,
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Xử lý content từ file: chia chunks, tạo embeddings, lưu vào database
        
        Args:
            file_id (str): ID của file gốc
            content (str): Nội dung cần xử lý
            metadata (Dict): Metadata bổ sung
            
        Returns:
            Dict[str, Any]: Kết quả xử lý
        """
        try:
            # Log bắt đầu quá trình
            self._log_processing(file_id, "embedding", "started", "Bắt đầu tạo embeddings")
            
            # Auto-classify content
            content_type = DocumentUtils.classify_content_type(content)
            topic = DocumentUtils.extract_topic(content)
            difficulty = DocumentUtils.estimate_difficulty_level(content)
            tags = DocumentUtils.generate_tags(content, content_type)
            
            # Merge metadata
            merged_metadata = {
                "content_type": content_type,
                "topic": topic,
                "difficulty_level": difficulty,
                "tags": tags,
                "auto_classified": True,
                **(metadata or {})
            }
            
            # Chunk và tạo embeddings
            chunk_result = self.embedding_tool.chunk_and_embed(
                content, 
                chunk_size_tokens=1000, 
                overlap_tokens=100
            )
            
            if not chunk_result["success"]:
                self._log_processing(file_id, "embedding", "failed", chunk_result["error"])
                return {
                    "success": False,
                    "error": f"Lỗi khi chunk và embed: {chunk_result['error']}"
                }
            
            # Lưu từng chunk vào database
            saved_chunks = []
            for chunk_data in chunk_result["chunks"]:
                # Tạo embedding document
                embedding_doc = DocumentModel.create_embedding_document(
                    file_id=file_id,
                    content=chunk_data["content"],
                    embedding=chunk_data["embedding"],
                    doc_type=content_type,
                    topic=topic,
                    chunk_index=chunk_data["chunk_index"],
                    metadata={
                        **merged_metadata,
                        "token_count": chunk_data["token_count"],
                        "text_length": chunk_data["text_length"],
                        "start_position": chunk_data.get("start_position", 0),
                        "embedding_model": self.embedding_tool.model,
                        "content_hash": self.embedding_tool.create_text_hash(chunk_data["content"])
                    }
                )
                
                # Lưu vào MongoDB
                collection = self.db_manager.db[self.embeddings_collection]
                result = collection.insert_one(embedding_doc)
                
                saved_chunks.append({
                    "chunk_index": chunk_data["chunk_index"],
                    "document_id": str(result.inserted_id),
                    "content_preview": chunk_data["content"][:100] + "...",
                    "token_count": chunk_data["token_count"]
                })
            
            # Cập nhật file status
            self._update_file_status(file_id, "completed", {
                "total_chunks": len(saved_chunks),
                "content_type": content_type,
                "topic": topic,
                "processing_completed_at": datetime.utcnow()
            })
            
            # Log thành công
            self._log_processing(
                file_id, 
                "embedding", 
                "completed", 
                f"Đã tạo {len(saved_chunks)} chunks với embeddings"
            )
            
            return {
                "success": True,
                "file_id": file_id,
                "total_chunks": len(saved_chunks),
                "saved_chunks": saved_chunks,
                "content_type": content_type,
                "topic": topic,
                "difficulty_level": difficulty,
                "tags": tags,
                "total_tokens": chunk_result["total_tokens"],
                "processing_time": datetime.utcnow()
            }
            
        except Exception as e:
            error_msg = f"Lỗi khi xử lý file content: {str(e)}"
            self._log_processing(file_id, "embedding", "failed", error_msg, {"error": str(e)})
            return {
                "success": False,
                "error": error_msg
            }
    
    def search_similar_content(self, 
                             query: str,
                             content_type: str = None,
                             topic: str = None,
                             limit: int = 10) -> Dict[str, Any]:
        """
        Tìm kiếm content tương tự
        
        Args:
            query (str): Query text
            content_type (str): Lọc theo loại content
            topic (str): Lọc theo topic
            limit (int): Số kết quả tối đa
            
        Returns:
            Dict[str, Any]: Kết quả tìm kiếm
        """
        try:
            # Tạo filters
            filters = {}
            if content_type:
                filters["type"] = content_type
            if topic:
                filters["topic"] = {"$regex": topic, "$options": "i"}
            
            # Sử dụng VectorSearchTool
            search_tool = VectorSearchTool(self.db_manager, self.embedding_tool)
            results = search_tool.similarity_search(
                query_text=query,
                limit=limit,
                filters=filters
            )
            
            if results["success"]:
                # Log search query
                self._log_search_query(query, "vector", len(results["results"]), filters)
                
                # Format kết quả
                formatted_results = []
                for result in results["results"]:
                    formatted_results.append({
                        "document_id": str(result["_id"]),
                        "content": result["content"],
                        "content_type": result.get("type", "unknown"),
                        "topic": result.get("topic"),
                        "similarity_score": result["similarity_score"],
                        "chunk_index": result.get("chunk_index", 0),
                        "metadata": result.get("metadata", {})
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "results": formatted_results,
                    "total_found": len(formatted_results),
                    "filters_applied": filters
                }
            else:
                return results
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi search: {str(e)}"
            }
    
    def get_content_by_type(self, content_type: str, limit: int = 20) -> Dict[str, Any]:
        """
        Lấy content theo loại
        
        Args:
            content_type (str): Loại content
            limit (int): Số lượng tối đa
            
        Returns:
            Dict[str, Any]: Danh sách content
        """
        try:
            collection = self.db_manager.db[self.embeddings_collection]
            
            cursor = collection.find(
                {"type": content_type},
                {"embedding": 0}  # Không lấy embedding vector để giảm kích thước
            ).limit(limit).sort("created_at", -1)
            
            results = []
            for doc in cursor:
                results.append({
                    "document_id": str(doc["_id"]),
                    "content": doc["content"],
                    "topic": doc.get("topic"),
                    "chunk_index": doc.get("chunk_index", 0),
                    "word_count": doc.get("word_count", 0),
                    "metadata": doc.get("metadata", {}),
                    "created_at": doc.get("created_at")
                })
            
            return {
                "success": True,
                "content_type": content_type,
                "results": results,
                "total_found": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi lấy content: {str(e)}"
            }
    
    def get_topics_by_type(self, content_type: str = None) -> Dict[str, Any]:
        """
        Lấy danh sách topics
        
        Args:
            content_type (str): Lọc theo loại content
            
        Returns:
            Dict[str, Any]: Danh sách topics
        """
        try:
            collection = self.db_manager.db[self.embeddings_collection]
            
            # Tạo aggregation pipeline
            match_stage = {}
            if content_type:
                match_stage["type"] = content_type
            
            pipeline = []
            if match_stage:
                pipeline.append({"$match": match_stage})
            
            pipeline.extend([
                {"$group": {
                    "_id": "$topic",
                    "count": {"$sum": 1},
                    "content_type": {"$first": "$type"}
                }},
                {"$match": {"_id": {"$ne": None}}},  # Loại bỏ null topics
                {"$sort": {"count": -1}}
            ])
            
            cursor = collection.aggregate(pipeline)
            topics = list(cursor)
            
            return {
                "success": True,
                "content_type": content_type,
                "topics": topics,
                "total_topics": len(topics)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi lấy topics: {str(e)}"
            }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê xử lý
        
        Returns:
            Dict[str, Any]: Thống kê
        """
        try:
            embeddings_collection = self.db_manager.db[self.embeddings_collection]
            files_collection = self.db_manager.db[self.files_collection]
            
            # Thống kê embeddings
            total_embeddings = embeddings_collection.count_documents({})
            
            # Thống kê theo type
            type_stats = list(embeddings_collection.aggregate([
                {"$group": {"_id": "$type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]))
            
            # Thống kê files
            total_files = files_collection.count_documents({})
            processed_files = files_collection.count_documents({"processed": True})
            
            # Usage stats từ embedding tool
            usage_stats = self.embedding_tool.get_usage_stats()
            
            return {
                "success": True,
                "embeddings": {
                    "total_documents": total_embeddings,
                    "type_distribution": type_stats
                },
                "files": {
                    "total_files": total_files,
                    "processed_files": processed_files,
                    "processing_rate": (processed_files / total_files * 100) if total_files > 0 else 0
                },
                "usage": usage_stats,
                "last_updated": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi lấy stats: {str(e)}"
            }
    
    def _update_file_status(self, file_id: str, status: str, metadata: Dict[str, Any] = None):
        """Cập nhật status của file"""
        try:
            collection = self.db_manager.db[self.files_collection]
            
            update_data = {
                "processing_status": status,
                "updated_at": datetime.utcnow()
            }
            
            if status == "completed":
                update_data["processed"] = True
                update_data["processing_completed_at"] = datetime.utcnow()
            
            if metadata:
                update_data["processing_metadata"] = metadata
            
            collection.update_one(
                {"_id": file_id},
                {"$set": update_data}
            )
            
        except Exception as e:
            print(f"Lỗi khi cập nhật file status: {e}")
    
    def _log_processing(self, file_id: str, stage: str, status: str, message: str = None, error_details: Dict[str, Any] = None):
        """Log quá trình xử lý"""
        try:
            log_doc = DocumentModel.create_processing_log(
                file_id=file_id,
                stage=stage,
                status=status,
                message=message,
                error_details=error_details
            )
            
            collection = self.db_manager.db[self.logs_collection]
            collection.insert_one(log_doc)
            
        except Exception as e:
            print(f"Lỗi khi log processing: {e}")
    
    def _log_search_query(self, query: str, search_type: str, results_count: int, filters: Dict[str, Any] = None):
        """Log search queries"""
        try:
            log_doc = DocumentModel.create_search_query_log(
                query_text=query,
                search_type=search_type,
                results_count=results_count,
                filters=filters
            )
            
            collection = self.db_manager.db["search_logs"]
            collection.insert_one(log_doc)
            
        except Exception as e:
            print(f"Lỗi khi log search query: {e}")

# Example usage
if __name__ == "__main__":
    print("=== Embedding Service Demo ===")
    
    try:
        # Khởi tạo service
        service = EmbeddingService()
        
        # Test content processing
        test_content = """
        Lesson 1: Past Perfect Tense
        
        The Past Perfect tense is used to show that something happened before another action in the past.
        
        Form: had + past participle
        
        Examples:
        - I had finished my homework before I watched TV.
        - She had left when he arrived.
        """
        
        # Giả lập file_id
        fake_file_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format
        
        print("Processing content...")
        result = service.process_file_content(
            file_id=fake_file_id,
            content=test_content,
            metadata={
                "subject": "English",
                "language": "en",
                "source": "textbook"
            }
        )
        
        if result["success"]:
            print(f"✅ Processing successful:")
            print(f"   Content type: {result['content_type']}")
            print(f"   Topic: {result['topic']}")
            print(f"   Total chunks: {result['total_chunks']}")
            print(f"   Difficulty: {result['difficulty_level']}")
            print(f"   Tags: {result['tags']}")
        else:
            print(f"❌ Processing failed: {result['error']}")
        
        # Test search
        print("\\nTesting search...")
        search_result = service.search_similar_content(
            query="past perfect grammar",
            limit=3
        )
        
        if search_result["success"]:
            print(f"✅ Search successful: {search_result['total_found']} results found")
        else:
            print(f"❌ Search failed: {search_result['error']}")
        
        # Get stats
        stats = service.get_processing_stats()
        if stats["success"]:
            print(f"\\n📊 Processing Stats:")
            print(f"   Total embeddings: {stats['embeddings']['total_documents']}")
            print(f"   Total files: {stats['files']['total_files']}")
        
    except Exception as e:
        print(f"Demo không thể chạy: {e}")
        print("Cần cài đặt database connection và OpenAI API key")
