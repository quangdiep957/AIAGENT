from pymongo import MongoClient
from config import MONGODB_CONNECTION
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            logger.info("✅ Successfully connected to MongoDB!")
            
            # List all available databases
            db_names = self.client.list_database_names()
            logger.info(f"📁 Available databases: {db_names}")
            
            # Use the first non-system database or specify a default
            system_dbs = ['admin', 'local', 'config']
            user_dbs = [db for db in db_names if db not in system_dbs]
            
            # Prioritize study_db if it exists
            if 'study_db' in user_dbs:
                self.db = self.client['study_db']
                logger.info(f"🎯 Using database: study_db")
            elif user_dbs:
                self.db = self.client[user_dbs[0]]
                logger.info(f"🎯 Using database: {user_dbs[0]}")
            else:
                # If no user databases, create/use a default one
                self.db = self.client['study_db']
                logger.info("📝 Creating and using database: study_db")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
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

# Example usage functions
def demo_database_operations():
    """Demonstrate basic database operations"""
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get all collections
        collections = db_manager.get_collections()
        print(f"\n📁 Available collections: {collections}")
        
        # If there are collections, demonstrate data retrieval
        if collections:
            # Get data from the first collection
            first_collection = collections[0]
            print(f"\n📄 Sample data from '{first_collection}':")
            
            # Get document count
            count = db_manager.count_documents(first_collection)
            print(f"Total documents: {count}")
            
            # Get sample documents
            sample_data = db_manager.get_data_from_collection(first_collection, limit=5)
            for i, doc in enumerate(sample_data, 1):
                print(f"\nDocument {i}:")
                # Print first few fields of each document
                for key, value in list(doc.items())[:3]:
                    print(f"  {key}: {value}")
                if len(doc.items()) > 3:
                    print(f"  ... and {len(doc.items()) - 3} more fields")
        
        else:
            print("No collections found in the database")
        
        # Close connection
        db_manager.close_connection()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    demo_database_operations()
