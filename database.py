#!/usr/bin/env python3
"""
Database Module - Module chính để quản lý database

Import các class từ các file riêng biệt để dễ quản lý và maintain
"""

# Import các class từ các file riêng biệt
from database_manager import DatabaseManager
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
