"""
Test script to demonstrate MongoDB connection and data retrieval
"""
from database import DatabaseManager
import json

def test_connection():
    """Test MongoDB connection and basic operations"""
    try:
        print("🚀 Starting MongoDB connection test...")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        print("\n" + "="*50)
        print("📋 DATABASE INFORMATION")
        print("="*50)
        
        # Get all collections
        collections = db_manager.get_collections()
        print(f"📁 Available collections: {collections}")
        
        if not collections:
            print("⚠️  No collections found in the database")
            return
        
        # Demonstrate operations on each collection
        for collection_name in collections[:3]:  # Limit to first 3 collections
            print(f"\n" + "-"*40)
            print(f"📊 COLLECTION: {collection_name}")
            print("-"*40)
            
            # Count documents
            count = db_manager.count_documents(collection_name)
            print(f"📈 Total documents: {count}")
            
            if count > 0:
                # Get sample documents
                print(f"\n📄 Sample documents (limit 3):")
                sample_docs = db_manager.get_data_from_collection(collection_name, limit=3)
                
                for i, doc in enumerate(sample_docs, 1):
                    print(f"\n  Document {i}:")
                    # Convert ObjectId to string for JSON serialization
                    doc_copy = {}
                    for key, value in doc.items():
                        if hasattr(value, '__str__') and 'ObjectId' in str(type(value)):
                            doc_copy[key] = str(value)
                        else:
                            doc_copy[key] = value
                    
                    # Pretty print first few fields
                    fields_shown = 0
                    for key, value in doc_copy.items():
                        if fields_shown >= 5:  # Limit fields shown
                            break
                        print(f"    {key}: {value}")
                        fields_shown += 1
                    
                    if len(doc_copy) > 5:
                        print(f"    ... and {len(doc_copy) - 5} more fields")
        
        print(f"\n" + "="*50)
        print("✅ Database operations completed successfully!")
        print("="*50)
        
        # Close connection
        db_manager.close_connection()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def test_specific_queries():
    """Test specific database queries"""
    try:
        print("\n🔍 Testing specific database queries...")
        
        db_manager = DatabaseManager()
        collections = db_manager.get_collections()
        
        if collections:
            collection_name = collections[0]
            print(f"\n🎯 Testing queries on collection: {collection_name}")
            
            # Example: Find documents with specific criteria
            # Adjust these queries based on your actual data structure
            
            # Query 1: Get all documents (limited)
            all_docs = db_manager.get_data_from_collection(collection_name, limit=5)
            print(f"\n📄 All documents (first 5): {len(all_docs)} found")
            
            # Query 2: Search with filter (example)
            # This is just an example - adjust the filter based on your data
            # filter_example = {"status": "active"}  # Example filter
            # filtered_docs = db_manager.get_data_from_collection(collection_name, limit=5, filter_query=filter_example)
            # print(f"📄 Filtered documents: {len(filtered_docs)} found")
            
        db_manager.close_connection()
        
    except Exception as e:
        print(f"❌ Query test failed: {e}")

if __name__ == "__main__":
    # Run connection test
    test_connection()
    
    # Run specific queries test
    test_specific_queries()
