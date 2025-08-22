"""
Vector Search Tool - Tìm kiếm similarity trong database sử dụng vector embeddings
Hỗ trợ MongoDB với vector search và hybrid search
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from database import DatabaseManager
from tools.embedding_tool import EmbeddingTool

class VectorSearchTool:
    """Tool tìm kiếm vector similarity trong MongoDB"""
    
    def __init__(self, db_manager: DatabaseManager = None, embedding_tool: EmbeddingTool = None):
        """
        Khởi tạo VectorSearchTool
        
        Args:
            db_manager (DatabaseManager): Database manager instance
            embedding_tool (EmbeddingTool): Embedding tool instance
        """
        self.db_manager = db_manager or DatabaseManager()
        self.embedding_tool = embedding_tool or EmbeddingTool()
        
        # Tên collection chứa embeddings
        self.embeddings_collection = "document_embeddings"
        
        # Cấu hình search
        self.default_limit = 10
        self.min_similarity_threshold = 0.5
    
    def _calculate_cosine_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """
        Tính cosine similarity giữa 2 vectors
        
        Args:
            vector1 (List[float]): Vector 1
            vector2 (List[float]): Vector 2
            
        Returns:
            float: Cosine similarity (0-1)
        """
        try:
            if len(vector1) != len(vector2):
                return 0.0
            
            # Tính dot product
            dot_product = sum(a * b for a, b in zip(vector1, vector2))
            
            # Tính magnitude
            magnitude1 = math.sqrt(sum(a * a for a in vector1))
            magnitude2 = math.sqrt(sum(b * b for b in vector2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            # Cosine similarity
            similarity = dot_product / (magnitude1 * magnitude2)
            
            # Normalize to [0, 1]
            return max(0.0, min(1.0, (similarity + 1) / 2))
            
        except Exception as e:
            print(f"Lỗi khi tính cosine similarity: {e}")
            return 0.0
    
    def _create_vector_index(self) -> Dict[str, Any]:
        """
        Tạo vector search index trong MongoDB (nếu chưa có)
        
        Returns:
            Dict[str, Any]: Kết quả tạo index
        """
        try:
            collection = self.db_manager.db[self.embeddings_collection]
            
            # Kiểm tra index đã tồn tại chưa
            existing_indexes = collection.list_indexes()
            for index in existing_indexes:
                if index.get("name") == "vector_index":
                    return {
                        "success": True,
                        "message": "Vector index đã tồn tại"
                    }
            
            # Tạo vector search index (cho MongoDB Atlas)
            # Note: Cần MongoDB Atlas với Vector Search feature
            try:
                collection.create_search_index({
                    "name": "vector_index",
                    "definition": {
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embedding",
                                "numDimensions": 1536,  # Cho text-embedding-3-small
                                "similarity": "cosine"
                            }
                        ]
                    }
                })
                
                return {
                    "success": True,
                    "message": "Vector index đã được tạo"
                }
                
            except Exception as atlas_error:
                # Fallback: tạo regular index cho local MongoDB
                collection.create_index([("embedding", 1)])
                
                return {
                    "success": True,
                    "message": "Regular index đã được tạo (không phải vector index)"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi tạo vector index: {str(e)}"
            }
    
    def store_embedding(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lưu document với embedding vào database
        
        Args:
            document (Dict[str, Any]): Document chứa content và embedding
            
        Returns:
            Dict[str, Any]: Kết quả lưu trữ
        """
        try:
            # Validate document
            required_fields = ["content", "embedding"]
            for field in required_fields:
                if field not in document:
                    return {
                        "success": False,
                        "error": f"Thiếu field required: {field}"
                    }
            
            # Thêm metadata
            document.update({
                "created_at": datetime.utcnow(),
                "embedding_model": self.embedding_tool.model,
                "embedding_dimensions": len(document["embedding"]),
                "content_length": len(document["content"]),
                "content_hash": self.embedding_tool.create_text_hash(document["content"])
            })
            
            # Lưu vào MongoDB
            collection = self.db_manager.db[self.embeddings_collection]
            result = collection.insert_one(document)
            
            return {
                "success": True,
                "document_id": str(result.inserted_id),
                "message": "Document đã được lưu thành công"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi lưu embedding: {str(e)}"
            }
    
    def similarity_search(self, 
                         query_text: str, 
                         limit: int = None, 
                         filters: Dict[str, Any] = None,
                         similarity_threshold: float = None) -> Dict[str, Any]:
        """
        Tìm kiếm similarity dựa trên query text
        
        Args:
            query_text (str): Text cần tìm kiếm
            limit (int): Số kết quả tối đa
            filters (Dict): Filters bổ sung (type, topic, etc.)
            similarity_threshold (float): Ngưỡng similarity tối thiểu
            
        Returns:
            Dict[str, Any]: Kết quả tìm kiếm
        """
        try:
            # Tạo embedding cho query
            query_result = self.embedding_tool.create_embedding(query_text)
            if not query_result["success"]:
                return {
                    "success": False,
                    "error": f"Lỗi khi tạo embedding cho query: {query_result['error']}"
                }
            
            query_embedding = query_result["embedding"]
            
            # Cài đặt mặc định
            limit = limit or self.default_limit
            similarity_threshold = similarity_threshold or self.min_similarity_threshold
            
            # Tạo MongoDB query
            mongo_filter = filters or {}
            
            # Lấy tất cả documents từ collection
            collection = self.db_manager.db[self.embeddings_collection]
            cursor = collection.find(mongo_filter)
            
            # Tính similarity cho từng document
            results = []
            for doc in cursor:
                if "embedding" not in doc:
                    continue
                
                # Tính similarity
                similarity = self._calculate_cosine_similarity(
                    query_embedding, 
                    doc["embedding"]
                )
                
                # Lọc theo threshold
                if similarity >= similarity_threshold:
                    # Chuẩn bị kết quả (loại bỏ embedding vector để giảm kích thước)
                    result_doc = {k: v for k, v in doc.items() if k != "embedding"}
                    result_doc["similarity_score"] = similarity
                    results.append(result_doc)
            
            # Sắp xếp theo similarity giảm dần
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            # Giới hạn kết quả
            results = results[:limit]
            
            return {
                "success": True,
                "query": query_text,
                "results": results,
                "total_found": len(results),
                "limit": limit,
                "similarity_threshold": similarity_threshold,
                "filters_applied": mongo_filter,
                "search_time": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi tìm kiếm similarity: {str(e)}"
            }
    
    def vector_search_atlas(self, 
                           query_text: str, 
                           limit: int = None,
                           filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Vector search sử dụng MongoDB Atlas Vector Search (nếu có)
        
        Args:
            query_text (str): Text cần tìm kiếm
            limit (int): Số kết quả tối đa
            filters (Dict): Filters bổ sung
            
        Returns:
            Dict[str, Any]: Kết quả tìm kiếm
        """
        try:
            # Tạo embedding cho query
            query_result = self.embedding_tool.create_embedding(query_text)
            if not query_result["success"]:
                return {
                    "success": False,
                    "error": f"Lỗi khi tạo embedding cho query: {query_result['error']}"
                }
            
            query_embedding = query_result["embedding"]
            limit = limit or self.default_limit
            
            # MongoDB Atlas Vector Search aggregation pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": limit * 10,  # Số candidates để tìm
                        "limit": limit
                    }
                }
            ]
            
            # Thêm filters nếu có
            if filters:
                pipeline.append({"$match": filters})
            
            # Thêm metadata
            pipeline.append({
                "$addFields": {
                    "similarity_score": {"$meta": "vectorSearchScore"}
                }
            })
            
            # Loại bỏ embedding vector khỏi kết quả
            pipeline.append({
                "$project": {
                    "embedding": 0
                }
            })
            
            # Thực hiện search
            collection = self.db_manager.db[self.embeddings_collection]
            cursor = collection.aggregate(pipeline)
            results = list(cursor)
            
            return {
                "success": True,
                "query": query_text,
                "results": results,
                "total_found": len(results),
                "limit": limit,
                "search_method": "atlas_vector_search",
                "search_time": datetime.utcnow()
            }
            
        except Exception as e:
            # Fallback to regular similarity search
            print(f"Atlas vector search failed, falling back: {e}")
            return self.similarity_search(query_text, limit, filters)
    
    def hybrid_search(self, 
                     query_text: str,
                     keywords: List[str] = None,
                     limit: int = None,
                     vector_weight: float = 0.7,
                     keyword_weight: float = 0.3) -> Dict[str, Any]:
        """
        Hybrid search kết hợp vector search và keyword search
        
        Args:
            query_text (str): Text cần tìm kiếm
            keywords (List[str]): Keywords bổ sung
            limit (int): Số kết quả tối đa
            vector_weight (float): Trọng số cho vector search
            keyword_weight (float): Trọng số cho keyword search
            
        Returns:
            Dict[str, Any]: Kết quả tìm kiếm hybrid
        """
        try:
            limit = limit or self.default_limit
            
            # 1. Vector search
            vector_results = self.similarity_search(query_text, limit * 2)
            if not vector_results["success"]:
                return vector_results
            
            # 2. Keyword search
            keyword_results = []
            if keywords:
                # Tạo text search query
                text_filter = {
                    "$or": [
                        {"content": {"$regex": keyword, "$options": "i"}} 
                        for keyword in keywords
                    ]
                }
                
                collection = self.db_manager.db[self.embeddings_collection]
                cursor = collection.find(text_filter)
                
                for doc in cursor:
                    # Tính keyword score dựa trên số keyword match
                    keyword_score = 0
                    content_lower = doc.get("content", "").lower()
                    
                    for keyword in keywords:
                        if keyword.lower() in content_lower:
                            keyword_score += 1
                    
                    keyword_score = keyword_score / len(keywords) if keywords else 0
                    
                    result_doc = {k: v for k, v in doc.items() if k != "embedding"}
                    result_doc["keyword_score"] = keyword_score
                    result_doc["doc_id"] = str(doc["_id"])
                    keyword_results.append(result_doc)
            
            # 3. Kết hợp kết quả
            combined_results = {}
            
            # Thêm vector results
            for result in vector_results["results"]:
                doc_id = str(result["_id"])
                combined_results[doc_id] = {
                    **result,
                    "vector_score": result.get("similarity_score", 0),
                    "keyword_score": 0,
                    "doc_id": doc_id
                }
            
            # Thêm keyword results
            for result in keyword_results:
                doc_id = result["doc_id"]
                if doc_id in combined_results:
                    combined_results[doc_id]["keyword_score"] = result["keyword_score"]
                else:
                    combined_results[doc_id] = {
                        **result,
                        "vector_score": 0
                    }
            
            # 4. Tính hybrid score
            final_results = []
            for doc_id, result in combined_results.items():
                hybrid_score = (
                    result["vector_score"] * vector_weight + 
                    result["keyword_score"] * keyword_weight
                )
                result["hybrid_score"] = hybrid_score
                final_results.append(result)
            
            # 5. Sắp xếp và giới hạn
            final_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
            final_results = final_results[:limit]
            
            return {
                "success": True,
                "query": query_text,
                "keywords": keywords or [],
                "results": final_results,
                "total_found": len(final_results),
                "limit": limit,
                "vector_weight": vector_weight,
                "keyword_weight": keyword_weight,
                "search_method": "hybrid",
                "search_time": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi hybrid search: {str(e)}"
            }
    
    def get_similar_documents(self, 
                             document_id: str, 
                             limit: int = None,
                             exclude_self: bool = True) -> Dict[str, Any]:
        """
        Tìm documents tương tự với một document cụ thể
        
        Args:
            document_id (str): ID của document gốc
            limit (int): Số kết quả tối đa
            exclude_self (bool): Có loại trừ chính document đó không
            
        Returns:
            Dict[str, Any]: Kết quả tìm kiếm
        """
        try:
            # Lấy document gốc
            collection = self.db_manager.db[self.embeddings_collection]
            source_doc = collection.find_one({"_id": document_id})
            
            if not source_doc:
                return {
                    "success": False,
                    "error": "Document không tồn tại"
                }
            
            if "embedding" not in source_doc:
                return {
                    "success": False,
                    "error": "Document không có embedding"
                }
            
            # Tìm similar documents
            source_embedding = source_doc["embedding"]
            limit = limit or self.default_limit
            
            # Lấy tất cả documents khác
            filter_query = {}
            if exclude_self:
                filter_query["_id"] = {"$ne": document_id}
            
            cursor = collection.find(filter_query)
            
            # Tính similarity
            results = []
            for doc in cursor:
                if "embedding" not in doc:
                    continue
                
                similarity = self._calculate_cosine_similarity(
                    source_embedding, 
                    doc["embedding"]
                )
                
                result_doc = {k: v for k, v in doc.items() if k != "embedding"}
                result_doc["similarity_score"] = similarity
                results.append(result_doc)
            
            # Sắp xếp và giới hạn
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            results = results[:limit]
            
            return {
                "success": True,
                "source_document_id": document_id,
                "source_content": source_doc.get("content", "")[:200] + "...",
                "similar_documents": results,
                "total_found": len(results),
                "limit": limit,
                "search_time": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi tìm similar documents: {str(e)}"
            }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê về embeddings collection
        
        Returns:
            Dict[str, Any]: Thống kê collection
        """
        try:
            collection = self.db_manager.db[self.embeddings_collection]
            
            # Đếm documents
            total_docs = collection.count_documents({})
            
            # Thống kê theo type
            type_stats = list(collection.aggregate([
                {"$group": {"_id": "$type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]))
            
            # Thống kê theo model
            model_stats = list(collection.aggregate([
                {"$group": {"_id": "$embedding_model", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]))
            
            return {
                "success": True,
                "collection_name": self.embeddings_collection,
                "total_documents": total_docs,
                "type_distribution": type_stats,
                "embedding_model_distribution": model_stats,
                "last_updated": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi lấy collection stats: {str(e)}"
            }

# Example usage
if __name__ == "__main__":
    # Demo usage
    print("=== Vector Search Tool Demo ===")
    
    try:
        # Khởi tạo tools
        search_tool = VectorSearchTool()
        
        # Lấy stats
        stats = search_tool.get_collection_stats()
        print(f"Collection stats: {stats}")
        
        # Test similarity search
        query = "grammar rules"
        results = search_tool.similarity_search(query, limit=5)
        
        if results["success"]:
            print(f"\\n🔍 Search results for '{query}':")
            for i, result in enumerate(results["results"], 1):
                content = result.get("content", "")[:100] + "..."
                score = result.get("similarity_score", 0)
                print(f"{i}. Score: {score:.3f} - {content}")
        else:
            print(f"Search failed: {results['error']}")
        
    except Exception as e:
        print(f"Demo không thể chạy: {e}")
        print("Cần cài đặt database connection và OpenAI API key")
