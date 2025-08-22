"""
Updated main.py with MongoDB integration
Demonstrates how to use database in the AI agent workflow
"""

from graph import build_graph
from ai_agent_database import AIAgentDatabase
import json

def process_user_query_with_database(user_input: str):
    """
    Process user query with database integration
    
    Args:
        user_input (str): User's query
    
    Returns:
        dict: Response with database data if relevant
    """
    
    # Initialize database
    ai_db = AIAgentDatabase()
    
    try:
        # Check if query is related to movies, users, or theaters
        query_lower = user_input.lower()
        
        response = {
            "input": user_input,
            "database_data": None,
            "ai_response": None
        }
        
        # Movie-related queries
        if any(keyword in query_lower for keyword in ["movie", "film", "cinema", "phim"]):
            print("🎬 Detected movie-related query, searching database...")
            
            # Extract potential movie title or genre
            if "action" in query_lower:
                movies = ai_db.get_movie_info(genre="Action", limit=5)
                response["database_data"] = {
                    "type": "movies",
                    "query": "Action movies",
                    "results": movies
                }
            elif "comedy" in query_lower:
                movies = ai_db.get_movie_info(genre="Comedy", limit=5)
                response["database_data"] = {
                    "type": "movies", 
                    "query": "Comedy movies",
                    "results": movies
                }
            else:
                # Generic movie search
                movies = ai_db.get_movie_info(limit=5)
                response["database_data"] = {
                    "type": "movies",
                    "query": "Recent movies",
                    "results": movies
                }
        
        # User-related queries
        elif any(keyword in query_lower for keyword in ["user", "member", "người dùng"]):
            print("👥 Detected user-related query, searching database...")
            users = ai_db.get_user_info(limit=5)
            response["database_data"] = {
                "type": "users",
                "query": "Users",
                "results": users
            }
        
        # Theater-related queries
        elif any(keyword in query_lower for keyword in ["theater", "cinema", "rạp"]):
            print("🎭 Detected theater-related query, searching database...")
            theaters = ai_db.get_theater_info(limit=5)
            response["database_data"] = {
                "type": "theaters",
                "query": "Theaters",
                "results": theaters
            }
        
        # Search queries
        elif any(keyword in query_lower for keyword in ["search", "find", "tìm"]):
            print("🔍 Detected search query...")
            # Extract search term (simple implementation)
            search_terms = user_input.split()
            if len(search_terms) > 1:
                search_term = search_terms[-1]  # Use last word as search term
                results = ai_db.search_data(search_term, "movies", limit=3)
                response["database_data"] = {
                    "type": "search",
                    "query": f"Search for '{search_term}'",
                    "results": results
                }
        
        # Now process with AI agent
        workflow = build_graph()
        
        # If we have database data, include it in the context
        if response["database_data"]:
            enhanced_input = f"{user_input}\\n\\nDatabase context: {json.dumps(response['database_data'], default=str, indent=2)}"
            ai_result = workflow.invoke({"input": enhanced_input})
        else:
            ai_result = workflow.invoke({"input": user_input})
        
        response["ai_response"] = ai_result["output"]
        
        return response
        
    except Exception as e:
        print(f"❌ Error processing query: {e}")
        return {
            "input": user_input,
            "error": str(e),
            "ai_response": None
        }
    
    finally:
        ai_db.close_connection()

def main():
    """Main function with database integration"""
    print("🤖 AI Agent with MongoDB Integration")
    print("=" * 50)
    
    # Test queries
    test_queries = [
        "Recommend me some action movies",
        "Show me information about users",
        "Find theaters in California", 
        "Search for Star Wars movies",
        "Calculate 5 + 5"  # Non-database query
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\\n{i}. Testing query: '{query}'")
        print("-" * 40)
        
        result = process_user_query_with_database(query)
        
        # Display database results if available
        if result.get("database_data"):
            db_data = result["database_data"]
            print(f"📊 Database results for {db_data['query']}:")
            
            results = db_data["results"]
            if db_data["type"] == "movies":
                for movie in results[:3]:  # Show first 3
                    title = movie.get("title", "Unknown")
                    year = movie.get("year", "Unknown")
                    genres = movie.get("genres", [])
                    print(f"  🎥 {title} ({year}) - {', '.join(genres[:2])}")
            
            elif db_data["type"] == "users":
                for user in results[:3]:
                    name = user.get("name", "Unknown")
                    email = user.get("email", "No email")
                    print(f"  👤 {name} - {email}")
            
            elif db_data["type"] == "theaters":
                for theater in results[:3]:
                    theater_id = theater.get("theaterId", "Unknown")
                    location = theater.get("location", {}).get("address", {})
                    city = location.get("city", "Unknown")
                    state = location.get("state", "Unknown")
                    print(f"  🏛️  Theater {theater_id} - {city}, {state}")
            
            elif db_data["type"] == "search":
                for item in results[:3]:
                    if "title" in item:
                        title = item.get("title", "Unknown")
                        year = item.get("year", "Unknown")
                        print(f"  ⭐ {title} ({year})")
        
        # Display AI response
        if result.get("ai_response"):
            print(f"\\n🤖 AI Response: {result['ai_response']}")
        
        if result.get("error"):
            print(f"❌ Error: {result['error']}")
        
        print()

if __name__ == "__main__":
    main()
