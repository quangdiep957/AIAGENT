#!/usr/bin/env python3
"""
Database Module - Module chính để quản lý database

Import các class từ các file riêng biệt để dễ quản lý và maintain
"""

import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import List, Dict, Any, Optional

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('database_manager')

# MongoDB connection string from environment
MONGODB_CONNECTION = os.getenv('CONNECTION', 'mongodb://localhost:27017/')

class DatabaseManager:
    def __init__(self):
        """Initialize MongoDB connection"""
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(MONGODB_CONNECTION)
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ Kết nối MongoDB thành công!")
            
            # List all available databases
            db_names = self.client.list_database_names()
            logger.info(f"📁 Các databases có sẵn: {db_names}")
            
            # Always use study_db
            self.db = self.client['study_db']
            logger.info(f"🎯 Đang sử dụng database: study_db")
            
        except Exception as e:
            logger.error(f"❌ Kết nối MongoDB thất bại: {e}")
            raise
    
    def get_collections(self):
        """Get list of all collections in the database"""
        try:
            collections = self.db.list_collection_names()
            logger.info(f"📁 Available collections: {collections}")
            return collections
        except Exception as e:
            logger.error(f"❌ Error getting collections: {e}")
            return []
    
    def get_data_from_collection(self, collection_name, limit=10, filter_query=None):
        """
        Get data from a specific collection
        
        Args:
            collection_name (str): Name of the collection
            limit (int): Maximum number of documents to return
            filter_query (dict): MongoDB filter query (optional)
        
        Returns:
            list: List of documents
        """
        try:
            collection = self.db[collection_name]
            
            if filter_query:
                cursor = collection.find(filter_query).limit(limit)
            else:
                cursor = collection.find().limit(limit)
            
            documents = list(cursor)
            logger.info(f"📄 Retrieved {len(documents)} documents from {collection_name}")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Error getting data from {collection_name}: {e}")
            return []
    
    def count_documents(self, collection_name, filter_query=None):
        """Count documents in a collection"""
        try:
            collection = self.db[collection_name]
            if filter_query:
                count = collection.count_documents(filter_query)
            else:
                count = collection.estimated_document_count()
            
            logger.info(f"📊 Collection {collection_name} has {count} documents")
            return count
            
        except Exception as e:
            logger.error(f"❌ Error counting documents in {collection_name}: {e}")
            return 0
    
    def search_documents(self, collection_name, search_query, limit=10):
        """
        Search documents using text search or regex
        
        Args:
            collection_name (str): Name of the collection
            search_query (dict): Search query
            limit (int): Maximum number of results
        
        Returns:
            list: List of matching documents
        """
        try:
            collection = self.db[collection_name]
            cursor = collection.find(search_query).limit(limit)
            documents = list(cursor)
            
            logger.info(f"🔍 Found {len(documents)} documents matching search criteria")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Error searching in {collection_name}: {e}")
            return []
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("🔒 MongoDB connection closed")
# Import semantic document manager
from semantic_document_manager import SemanticDocumentManager

# Export các class để sử dụng
__all__ = [
    'DatabaseManager',
    'SemanticDocumentManager'
]

# Demo function để test cả hai class
def demo_all_database_features():
    """Demo tất cả tính năng database"""
    try:
        print("🚀 Demo Tất Cả Tính Năng Database")
        print("=" * 60)
        
        # Test 1: Database Manager cơ bản
        print("\n📊 Test 1: Database Manager cơ bản...")
        print("-" * 40)
        
        db_manager = DatabaseManager()
        collections = db_manager.get_collections()
        print(f"📁 Collections có sẵn: {collections}")
        
        if collections:
            first_collection = collections[0]
            count = db_manager.count_documents(first_collection)
            print(f"📊 Collection '{first_collection}' có {count} documents")
        
        db_manager.close_connection()
        
        # Test 2: Semantic Document Manager
        print("\n🔍 Test 2: Semantic Document Manager...")
        print("-" * 40)
        
        semantic_manager = SemanticDocumentManager()
        
        # Lưu một document mẫu
        doc_id = semantic_manager.save_document(
            "demo_user",
            "demo_document.txt",
            "Đây là một document mẫu để test semantic search. Document này chứa thông tin về AI và machine learning."
        )
        print(f"✅ Đã lưu document với ID: {doc_id}")
        
        # Test semantic search
        results = semantic_manager.search_similar("AI và machine learning", top_k=2)
        print(f"🔍 Kết quả tìm kiếm: {len(results)} documents")
        
        # Xóa document test
        semantic_manager.delete_document(doc_id, "demo_user")
        print(f"🗑️ Đã xóa document test")
        
        semantic_manager.close_connection()
        
        print("\n🎉 Tất cả tests hoàn thành thành công!")
        
    except Exception as e:
        print(f"❌ Demo thất bại: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_all_database_features()
