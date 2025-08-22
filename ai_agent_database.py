"""
AI Agent with MongoDB Integration
Demonstrates how to use database operations within the AI agent workflow
"""

from database import DatabaseManager
import json
from typing import List, Dict, Any

class AIAgentDatabase:
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def get_movie_info(self, movie_title: str = None, genre: str = None, limit: int = 5) -> List[Dict]:
        """
        Get movie information from database
        
        Args:
            movie_title (str): Specific movie title to search for
            genre (str): Genre to filter by
            limit (int): Maximum number of results
        
        Returns:
            List[Dict]: List of movie documents
        """
        try:
            filter_query = {}
            
            if movie_title:
                # Case-insensitive search for movie title
                filter_query["title"] = {"$regex": movie_title, "$options": "i"}
            
            if genre:
                # Search for specific genre
                filter_query["genres"] = {"$in": [genre]}
            
            # Search in movies collection
            if "movies" in self.db_manager.get_collections():
                movies = self.db_manager.get_data_from_collection(
                    "movies", 
                    limit=limit, 
                    filter_query=filter_query if filter_query else None
                )
            else:
                # Fallback to embedded_movies if movies collection not available
                movies = self.db_manager.get_data_from_collection(
                    "embedded_movies", 
                    limit=limit, 
                    filter_query=filter_query if filter_query else None
                )
            
            return movies
            
        except Exception as e:
            print(f"❌ Error getting movie info: {e}")
            return []
    
    def get_user_info(self, user_name: str = None, limit: int = 5) -> List[Dict]:
        """
        Get user information from database
        
        Args:
            user_name (str): Specific user name to search for
            limit (int): Maximum number of results
        
        Returns:
            List[Dict]: List of user documents
        """
        try:
            filter_query = {}
            
            if user_name:
                filter_query["name"] = {"$regex": user_name, "$options": "i"}
            
            users = self.db_manager.get_data_from_collection(
                "users", 
                limit=limit,
                filter_query=filter_query if filter_query else None
            )
            
            # Remove password field for security
            for user in users:
                if "password" in user:
                    user.pop("password")
            
            return users
            
        except Exception as e:
            print(f"❌ Error getting user info: {e}")
            return []
    
    def get_theater_info(self, city: str = None, state: str = None, limit: int = 5) -> List[Dict]:
        """
        Get theater information from database
        
        Args:
            city (str): City to filter by
            state (str): State to filter by
            limit (int): Maximum number of results
        
        Returns:
            List[Dict]: List of theater documents
        """
        try:
            filter_query = {}
            
            if city:
                filter_query["location.address.city"] = {"$regex": city, "$options": "i"}
            
            if state:
                filter_query["location.address.state"] = {"$regex": state, "$options": "i"}
            
            theaters = self.db_manager.get_data_from_collection(
                "theaters", 
                limit=limit,
                filter_query=filter_query if filter_query else None
            )
            
            return theaters
            
        except Exception as e:
            print(f"❌ Error getting theater info: {e}")
            return []
    
    def get_database_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the database content
        
        Returns:
            Dict: Database summary information
        """
        try:
            collections = self.db_manager.get_collections()
            summary = {
                "collections": {},
                "total_collections": len(collections)
            }
            
            for collection in collections:
                count = self.db_manager.count_documents(collection)
                summary["collections"][collection] = {
                    "document_count": count
                }
            
            return summary
            
        except Exception as e:
            print(f"❌ Error getting database summary: {e}")
            return {}
    
    def search_data(self, search_term: str, collection: str = "movies", limit: int = 5) -> List[Dict]:
        """
        Generic search function across different fields
        
        Args:
            search_term (str): Term to search for
            collection (str): Collection to search in
            limit (int): Maximum number of results
        
        Returns:
            List[Dict]: List of matching documents
        """
        try:
            # For movies, search in title, plot, and genres
            if collection in ["movies", "embedded_movies"]:
                search_query = {
                    "$or": [
                        {"title": {"$regex": search_term, "$options": "i"}},
                        {"plot": {"$regex": search_term, "$options": "i"}},
                        {"genres": {"$regex": search_term, "$options": "i"}}
                    ]
                }
            elif collection == "users":
                search_query = {
                    "$or": [
                        {"name": {"$regex": search_term, "$options": "i"}},
                        {"email": {"$regex": search_term, "$options": "i"}}
                    ]
                }
            elif collection == "theaters":
                search_query = {
                    "$or": [
                        {"location.address.city": {"$regex": search_term, "$options": "i"}},
                        {"location.address.state": {"$regex": search_term, "$options": "i"}},
                        {"location.address.street1": {"$regex": search_term, "$options": "i"}}
                    ]
                }
            else:
                # Generic text search
                search_query = {"$text": {"$search": search_term}}
            
            results = self.db_manager.search_documents(collection, search_query, limit)
            return results
            
        except Exception as e:
            print(f"❌ Error searching data: {e}")
            return []
    
    def close_connection(self):
        """Close database connection"""
        self.db_manager.close_connection()

def demo_ai_agent_database():
    """Demonstrate AI agent database operations"""
    print("🤖 AI Agent Database Demo")
    print("=" * 50)
    
    # Initialize AI agent database
    ai_db = AIAgentDatabase()
    
    try:
        # Get database summary
        print("\n📊 Database Summary:")
        summary = ai_db.get_database_summary()
        for collection, info in summary.get("collections", {}).items():
            print(f"  📁 {collection}: {info['document_count']} documents")
        
        # Search for movies
        print("\n🎬 Searching for Action movies:")
        action_movies = ai_db.get_movie_info(genre="Action", limit=3)
        for movie in action_movies:
            title = movie.get("title", "Unknown")
            plot = movie.get("plot", "No plot available")[:100] + "..."
            print(f"  🎥 {title}")
            print(f"     Plot: {plot}")
        
        # Search for users
        print("\n👥 Sample users:")
        users = ai_db.get_user_info(limit=3)
        for user in users:
            name = user.get("name", "Unknown")
            email = user.get("email", "No email")
            print(f"  👤 {name} ({email})")
        
        # Search for theaters in California
        print("\n🎭 Theaters in California:")
        ca_theaters = ai_db.get_theater_info(state="CA", limit=3)
        for theater in ca_theaters:
            theater_id = theater.get("theaterId", "Unknown")
            location = theater.get("location", {}).get("address", {})
            city = location.get("city", "Unknown")
            street = location.get("street1", "Unknown")
            print(f"  🏛️  Theater {theater_id} - {street}, {city}")
        
        # Generic search
        print("\n🔍 Searching for 'Star Wars':")
        search_results = ai_db.search_data("Star Wars", "embedded_movies", limit=2)
        for movie in search_results:
            title = movie.get("title", "Unknown")
            year = movie.get("year", "Unknown")
            print(f"  ⭐ {title} ({year})")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    finally:
        # Close connection
        ai_db.close_connection()
        print("\n✅ Demo completed!")

if __name__ == "__main__":
    demo_ai_agent_database()
