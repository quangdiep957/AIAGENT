#!/usr/bin/env python3
"""
Semantic Document Manager - Quản lý documents với semantic search sử dụng OpenAI embeddings
"""

from pymongo import MongoClient
from config import MONGODB_CONNECTION, OPENAI_API_KEY
import logging
from langchain_openai import OpenAIEmbeddings
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SemanticDocumentManager:
    """
    Quản lý documents với semantic search sử dụng OpenAI embeddings
    
    Tính năng chính:
    - Lưu trữ documents với embeddings
    - Tìm kiếm semantic sử dụng cosine similarity
    - Quản lý documents theo user
    - CRUD operations đầy đủ
    """
    
    def __init__(self, database_name="study_db", collection_name="documents"):
        """
        Khởi tạo semantic document manager
        
        Args:
            database_name (str): Tên database
            collection_name (str): Tên collection cho documents
        """
        self.client = None
        self.db = None
        self.collection = None
        self.embeddings_model = None
        self.database_name = database_name
        self.collection_name = collection_name
        
        # Kết nối database và setup embeddings
        self.connect()
        self.setup_embeddings()
    
    def connect(self):
        """Kết nối đến MongoDB"""
        try:
            # Tạo kết nối MongoDB
            self.client = MongoClient(MONGODB_CONNECTION)
            
            # Test kết nối
            self.client.admin.command('ping')
            logger.info("✅ Kết nối MongoDB cho semantic search thành công!")
            
            # Sử dụng database được chỉ định
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Tạo collection nếu chưa tồn tại
            if self.collection_name not in self.db.list_collection_names():
                self.db.create_collection(self.collection_name)
                logger.info(f"📁 Đã tạo collection: {self.collection_name}")
            
            logger.info(f"🎯 Đang sử dụng database: {self.database_name}, collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"❌ Không thể kết nối MongoDB: {e}")
            raise
    
    def setup_embeddings(self):
        """Thiết lập OpenAI embeddings model"""
        try:
            if not OPENAI_API_KEY:
                raise ValueError("Không tìm thấy OPENAI_API_KEY trong biến môi trường")
            
            # Khởi tạo model embeddings
            self.embeddings_model = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=OPENAI_API_KEY
            )
            logger.info("✅ OpenAI embeddings model đã được khởi tạo thành công!")
            
        except Exception as e:
            logger.error(f"❌ Không thể thiết lập embeddings: {e}")
            raise
    
    def save_document(self, user_id, file_name, content, metadata=None):
        """
        Lưu document với semantic embedding
        
        Args:
            user_id (str): ID của user
            file_name (str): Tên file được upload
            content (str): Nội dung text của document
            metadata (dict): Metadata bổ sung (tùy chọn)
        
        Returns:
            str: ID của document nếu thành công
        """
        try:
            # Tạo embedding cho nội dung
            embedding = self.embeddings_model.embed_query(content)
            
            # Chuẩn bị document
            doc = {
                "user_id": user_id,
                "file_name": file_name,
                "content": content,
                "embedding": embedding,
                "content_length": len(content),
                "created_at": self._get_current_timestamp(),
                "metadata": metadata or {}
            }
            
            # Chèn document vào database
            result = self.collection.insert_one(doc)
            doc_id = str(result.inserted_id)
            
            logger.info(f"✅ Document đã được lưu thành công với ID: {doc_id}")
            logger.info(f"📄 File: {file_name}, Độ dài nội dung: {len(content)} ký tự")
            
            return doc_id
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu document: {e}")
            raise
    
    def search_similar(self, query, top_k=3, user_id=None):
        """
        Tìm kiếm documents tương tự sử dụng semantic similarity với cosine similarity
        
        Args:
            query (str): Câu query tìm kiếm
            top_k (int): Số lượng kết quả top trả về
            user_id (str): Lọc theo user ID (tùy chọn)
        
        Returns:
            list: Danh sách documents tương tự với scores
        """
        try:
            # Tạo embedding cho query
            query_embedding = self.embeddings_model.embed_query(query)
            
            # Xây dựng filter query
            filter_query = {}
            if user_id:
                filter_query["user_id"] = user_id
            
            # Lấy tất cả documents phù hợp với filter
            documents = list(self.collection.find(filter_query))
            
            if not documents:
                logger.info("🔍 Không tìm thấy documents nào phù hợp với filter")
                return []
            
            # Tính cosine similarity cho mỗi document
            similarities = []
            for doc in documents:
                if "embedding" in doc:
                    doc_embedding = doc["embedding"]
                    similarity = self._cosine_similarity(query_embedding, doc_embedding)
                    similarities.append((doc, similarity))
            
            # Sắp xếp theo similarity score (giảm dần)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Trả về top_k kết quả
            top_results = similarities[:top_k]
            
            # Format kết quả
            results = []
            for doc, score in top_results:
                result = {
                    "content": doc.get("content", ""),
                    "file_name": doc.get("file_name", ""),
                    "user_id": doc.get("user_id", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": score
                }
                results.append(result)
            
            logger.info(f"🔍 Tìm thấy {len(results)} documents tương tự cho query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Lỗi trong semantic search: {e}")
            return []
    
    def _cosine_similarity(self, vec1, vec2):
        """
        Tính cosine similarity giữa hai vectors
        
        Args:
            vec1 (list): Vector thứ nhất
            vec2 (list): Vector thứ hai
        
        Returns:
            float: Cosine similarity score (0-1)
        """
        try:
            # Chuyển đổi sang numpy arrays
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            # Tính cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tính cosine similarity: {e}")
            return 0.0
    
    def get_user_documents(self, user_id, limit=20):
        """
        Lấy tất cả documents của một user cụ thể
        
        Args:
            user_id (str): ID của user
            limit (int): Số lượng documents tối đa
        
        Returns:
            list: Danh sách documents của user
        """
        try:
            documents = list(self.collection.find(
                {"user_id": user_id},
                {"content": 0, "embedding": 0}  # Loại trừ các trường lớn
            ).sort("created_at", -1).limit(limit))
            
            logger.info(f"📄 Đã lấy {len(documents)} documents của user: {user_id}")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi lấy documents của user: {e}")
            return []
    
    def delete_document(self, doc_id, user_id=None):
        """
        Xóa một document
        
        Args:
            doc_id (str): ID của document cần xóa
            user_id (str): ID của user để xác minh (tùy chọn)
        
        Returns:
            bool: True nếu thành công
        """
        try:
            filter_query = {"_id": self._parse_object_id(doc_id)}
            if user_id:
                filter_query["user_id"] = user_id
            
            result = self.collection.delete_one(filter_query)
            
            if result.deleted_count > 0:
                logger.info(f"✅ Document {doc_id} đã được xóa thành công")
                return True
            else:
                logger.warning(f"⚠️ Document {doc_id} không tìm thấy hoặc không được phép")
                return False
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi xóa document: {e}")
            return False
    
    def _get_current_timestamp(self):
        """Lấy timestamp hiện tại"""
        from datetime import datetime
        return datetime.utcnow()
    
    def _parse_object_id(self, doc_id):
        """Chuyển đổi string ID thành ObjectId"""
        from bson import ObjectId
        try:
            return ObjectId(doc_id)
        except:
            return doc_id
    
    def close_connection(self):
        """Đóng kết nối MongoDB"""
        if self.client:
            self.client.close()
            logger.info("🔒 Đã đóng kết nối MongoDB")

# Demo function để test SemanticDocumentManager
def demo_semantic_search():
    """Demo các thao tác semantic document"""
    try:
        print("🚀 Demo Semantic Document Manager")
        print("=" * 50)
        
        # Khởi tạo semantic document manager
        semantic_manager = SemanticDocumentManager()
        
        # Test 1: Lưu sample documents
        print("\n📝 Test 1: Lưu sample documents...")
        
        doc1_id = semantic_manager.save_document(
            "user1", 
            "hoc_toan.pdf",
            "Định lý Pythagore: Trong tam giác vuông, bình phương cạnh huyền bằng tổng bình phương hai cạnh góc vuông. Công thức: a² + b² = c²"
        )
        
        doc2_id = semantic_manager.save_document(
            "user1", 
            "hoc_vatly.pdf",
            "Định luật II Newton: Lực bằng khối lượng nhân gia tốc. Công thức: F = m × a. Đơn vị lực là Newton (N)."
        )
        
        doc3_id = semantic_manager.save_document(
            "user1", 
            "hoc_hoa.pdf",
            "Định luật bảo toàn khối lượng: Trong phản ứng hóa học, tổng khối lượng các chất tham gia bằng tổng khối lượng các chất tạo thành."
        )
        
        print(f"✅ Đã lưu 3 documents với IDs: {doc1_id}, {doc2_id}, {doc3_id}")
        
        # Test 2: Semantic search
        print("\n🔍 Test 2: Test semantic search...")
        
        # Tìm kiếm nội dung toán học
        math_results = semantic_manager.search_similar("Công thức tính cạnh huyền là gì?", top_k=2)
        print(f"\n🔍 Tìm kiếm: 'Công thức tính cạnh huyền là gì?'")
        for i, result in enumerate(math_results, 1):
            print(f"  {i}. File: {result.get('file_name', 'Unknown')}")
            print(f"     Nội dung: {result.get('content', '')[:100]}...")
            print(f"     Score: {result.get('score', 'N/A')}")
        
        # Tìm kiếm nội dung vật lý
        physics_results = semantic_manager.search_similar("Lực và gia tốc có mối quan hệ gì?", top_k=2)
        print(f"\n🔍 Tìm kiếm: 'Lực và gia tốc có mối quan hệ gì?'")
        for i, result in enumerate(physics_results, 1):
            print(f"  {i}. File: {result.get('file_name', 'Unknown')}")
            print(f"     Nội dung: {result.get('content', '')[:100]}...")
            print(f"     Score: {result.get('score', 'N/A')}")
        
        # Test 3: Lấy documents của user
        print("\n📄 Test 3: Lấy documents của user...")
        user_docs = semantic_manager.get_user_documents("user1", limit=5)
        print(f"📁 User 'user1' có {len(user_docs)} documents:")
        for doc in user_docs:
            print(f"  - {doc.get('file_name', 'Unknown')} (tạo lúc: {doc.get('created_at', 'Unknown')})")
        
        # Test 4: Xóa document
        print("\n🗑️ Test 4: Xóa document...")
        if semantic_manager.delete_document(doc3_id, "user1"):
            print(f"✅ Document {doc3_id} đã được xóa thành công")
        else:
            print(f"❌ Không thể xóa document {doc3_id}")
        
        # Đóng kết nối
        semantic_manager.close_connection()
        
        print("\n🎉 Demo semantic search hoàn thành thành công!")
        
    except Exception as e:
        print(f"❌ Demo semantic search thất bại: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_semantic_search()
