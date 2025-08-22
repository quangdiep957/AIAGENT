#!/usr/bin/env python3
"""
Test script for semantic document search functionality
"""

from database import SemanticDocumentManager
import json

def test_semantic_search():
    """Test semantic search functionality"""
    print("🚀 Testing Semantic Document Search")
    print("=" * 60)
    
    try:
        # Initialize semantic document manager
        print("🔌 Initializing semantic document manager...")
        semantic_manager = SemanticDocumentManager()
        
        # Test 1: Save sample documents
        print("\n📝 Test 1: Saving sample documents...")
        print("-" * 40)
        
        # Sample documents with different topics
        sample_docs = [
            {
                "user_id": "user1",
                "file_name": "toan_hoc.pdf",
                "content": "Định lý Pythagore: Trong tam giác vuông, bình phương cạnh huyền bằng tổng bình phương hai cạnh góc vuông. Công thức: a² + b² = c². Đây là một trong những định lý quan trọng nhất trong hình học."
            },
            {
                "user_id": "user1", 
                "file_name": "vat_ly.pdf",
                "content": "Định luật II Newton: Lực bằng khối lượng nhân gia tốc. Công thức: F = m × a. Đơn vị lực là Newton (N). Định luật này giải thích mối quan hệ giữa lực, khối lượng và gia tốc."
            },
            {
                "user_id": "user1",
                "file_name": "hoa_hoc.pdf", 
                "content": "Định luật bảo toàn khối lượng: Trong phản ứng hóa học, tổng khối lượng các chất tham gia bằng tổng khối lượng các chất tạo thành. Không có gì mất đi, không có gì được tạo ra."
            },
            {
                "user_id": "user1",
                "file_name": "sinh_hoc.pdf",
                "content": "Tế bào là đơn vị cơ bản của sự sống. Tất cả các sinh vật đều được cấu tạo từ tế bào. Tế bào có khả năng sinh sản, trao đổi chất và đáp ứng với môi trường."
            },
            {
                "user_id": "user1",
                "file_name": "lich_su.pdf",
                "content": "Cách mạng tháng 8 năm 1945 là một sự kiện lịch sử trọng đại của dân tộc Việt Nam. Ngày 19/8/1945, nhân dân Hà Nội đã nổi dậy giành chính quyền."
            }
        ]
        
        saved_docs = []
        for doc in sample_docs:
            doc_id = semantic_manager.save_document(
                doc["user_id"],
                doc["file_name"], 
                doc["content"]
            )
            saved_docs.append({"id": doc_id, "file_name": doc["file_name"]})
            print(f"✅ Saved: {doc['file_name']} (ID: {doc_id})")
        
        # Test 2: Semantic search queries
        print("\n🔍 Test 2: Testing semantic search queries...")
        print("-" * 40)
        
        test_queries = [
            "Công thức tính cạnh huyền là gì?",
            "Lực và gia tốc có mối quan hệ gì?",
            "Phản ứng hóa học có tuân theo định luật gì?",
            "Tế bào có đặc điểm gì?",
            "Sự kiện lịch sử quan trọng năm 1945 là gì?"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            results = semantic_manager.search_similar(query, top_k=2)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"  {i}. File: {result.get('file_name', 'Unknown')}")
                    print(f"     Content: {result.get('content', '')[:80]}...")
                    print(f"     Score: {result.get('score', 'N/A')}")
            else:
                print("  ❌ No results found")
        
        # Test 3: User-specific search
        print("\n👤 Test 3: User-specific search...")
        print("-" * 40)
        
        user_results = semantic_manager.search_similar("định lý toán học", top_k=3, user_id="user1")
        print(f"🔍 Search for 'định lý toán học' (user1 only):")
        for i, result in enumerate(user_results, 1):
            print(f"  {i}. File: {result.get('file_name', 'Unknown')}")
            print(f"     Content: {result.get('content', '')[:60]}...")
        
        # Test 4: Get user documents
        print("\n📄 Test 4: Getting user documents...")
        print("-" * 40)
        
        user_docs = semantic_manager.get_user_documents("user1", limit=10)
        print(f"📁 User 'user1' has {len(user_docs)} documents:")
        for doc in user_docs:
            print(f"  - {doc.get('file_name', 'Unknown')}")
            print(f"    Created: {doc.get('created_at', 'Unknown')}")
            print(f"    Content length: {doc.get('content_length', 'Unknown')} characters")
        
        # Test 5: Delete a document
        print("\n🗑️ Test 5: Deleting a document...")
        print("-" * 40)
        
        if saved_docs:
            doc_to_delete = saved_docs[0]
            if semantic_manager.delete_document(doc_to_delete["id"], "user1"):
                print(f"✅ Document '{doc_to_delete['file_name']}' deleted successfully")
            else:
                print(f"❌ Failed to delete document '{doc_to_delete['file_name']}'")
        
        # Close connection
        semantic_manager.close_connection()
        
        print("\n🎉 All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_semantic_search()
