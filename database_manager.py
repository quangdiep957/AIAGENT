#!/usr/bin/env python3
"""
Database Manager - Quản lý kết nối MongoDB cơ bản
"""

import os
import logging
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection from environment
MONGODB_CONNECTION = os.getenv('CONNECTION', 'mongodb://localhost:27017/')

class DatabaseManager:
    """
    Quản lý kết nối MongoDB cơ bản
    - Kết nối database
    - Quản lý collections
    - Thực hiện các thao tác CRUD cơ bản
    """
    
    def __init__(self):
        """Khởi tạo kết nối MongoDB"""
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Kết nối đến MongoDB"""
        try:
            # Tạo kết nối MongoDB
            self.client = MongoClient(MONGODB_CONNECTION)
            
            # Test kết nối
            self.client.admin.command('ping')
            logger.info("✅ Kết nối MongoDB thành công!")
            
            # Liệt kê tất cả databases có sẵn
            db_names = self.client.list_database_names()
            logger.info(f"📁 Các databases có sẵn: {db_names}")
            
            # Chọn database để sử dụng - ưu tiên study_db
            if 'study_db' in db_names:
                # Sử dụng study_db nếu có
                self.db = self.client['study_db']
                logger.info(f"🎯 Đang sử dụng database: study_db")
            else:
                # Tạo study_db nếu chưa có
                self.db = self.client['study_db']
                logger.info(f"🎯 Tạo và sử dụng database: study_db")
            
        except Exception as e:
            logger.error(f"❌ Không thể kết nối MongoDB: {e}")
            raise
    
    def get_collections(self):
        """Lấy danh sách tất cả collections trong database"""
        try:
            collections = self.db.list_collection_names()
            logger.info(f"📁 Các collections có sẵn: {collections}")
            return collections
        except Exception as e:
            logger.error(f"❌ Lỗi khi lấy collections: {e}")
            return []
    
    def get_data_from_collection(self, collection_name, limit=10, filter_query=None):
        """
        Lấy dữ liệu từ một collection cụ thể
        
        Args:
            collection_name (str): Tên collection
            limit (int): Số lượng documents tối đa trả về
            filter_query (dict): Bộ lọc MongoDB (tùy chọn)
        
        Returns:
            list: Danh sách documents
        """
        try:
            collection = self.db[collection_name]
            
            if filter_query:
                cursor = collection.find(filter_query).limit(limit)
            else:
                cursor = collection.find().limit(limit)
            
            documents = list(cursor)
            logger.info(f"📄 Đã lấy {len(documents)} documents từ {collection_name}")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi lấy dữ liệu từ {collection_name}: {e}")
            return []
    
    def count_documents(self, collection_name, filter_query=None):
        """Đếm số lượng documents trong collection"""
        try:
            collection = self.db[collection_name]
            if filter_query:
                count = collection.count_documents(filter_query)
            else:
                count = collection.estimated_document_count()
            
            logger.info(f"📊 Collection {collection_name} có {count} documents")
            return count
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi đếm documents trong {collection_name}: {e}")
            return 0
    
    def search_documents(self, collection_name, search_query, limit=10):
        """
        Tìm kiếm documents sử dụng text search hoặc regex
        
        Args:
            collection_name (str): Tên collection
            search_query (dict): Câu query tìm kiếm
            limit (int): Số lượng kết quả tối đa
        
        Returns:
            list: Danh sách documents phù hợp
        """
        try:
            collection = self.db[collection_name]
            cursor = collection.find(search_query).limit(limit)
            documents = list(cursor)
            
            logger.info(f"🔍 Tìm thấy {len(documents)} documents phù hợp với tiêu chí tìm kiếm")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tìm kiếm trong {collection_name}: {e}")
            return []
    
    def close_connection(self):
        """Đóng kết nối MongoDB"""
        if self.client:
            self.client.close()
            logger.info("🔒 Đã đóng kết nối MongoDB")

# Demo function để test DatabaseManager
def demo_database_operations():
    """Demo các thao tác database cơ bản"""
    try:
        print("🚀 Demo Database Manager")
        print("=" * 40)
        
        # Khởi tạo database manager
        db_manager = DatabaseManager()
        
        # Lấy tất cả collections
        collections = db_manager.get_collections()
        print(f"\n📁 Các collections có sẵn: {collections}")
        
        # Nếu có collections, demo việc lấy dữ liệu
        if collections:
            # Lấy dữ liệu từ collection đầu tiên
            first_collection = collections[0]
            print(f"\n📄 Dữ liệu mẫu từ '{first_collection}':")
            
            # Đếm số documents
            count = db_manager.count_documents(first_collection)
            print(f"Tổng số documents: {count}")
            
            # Lấy documents mẫu
            sample_data = db_manager.get_data_from_collection(first_collection, limit=3)
            for i, doc in enumerate(sample_data, 1):
                print(f"\nDocument {i}:")
                # In ra một vài trường đầu tiên của mỗi document
                for key, value in list(doc.items())[:3]:
                    print(f"  {key}: {value}")
                if len(doc.items()) > 3:
                    print(f"  ... và {len(doc.items()) - 3} trường khác")
        
        else:
            print("Không tìm thấy collections nào trong database")
        
        # Đóng kết nối
        db_manager.close_connection()
        
    except Exception as e:
        print(f"❌ Demo thất bại: {e}")

if __name__ == "__main__":
    demo_database_operations()
