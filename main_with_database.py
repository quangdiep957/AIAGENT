"""
Updated main.py with MongoDB integration
Demonstrates how to use database in the AI agent workflow
"""

from graph import build_graph
from ai_agent_database import AIAgentDatabase
import json
# Fallback retrieval imports
from semantic_document_manager import SemanticDocumentManager
from tools import wiki_search, wiki_summary

# Threshold cho độ tương tự (cosine) để chấp nhận kết quả semantic từ Mongo
SIMILARITY_THRESHOLD = 0.35


def retrieve_with_fallback(query: str, top_k: int = 3, user_id: str | None = None):
    """
    Ưu tiên tìm trong Mongo (semantic). Chỉ gọi Wikipedia nếu Mongo không có kết quả
    hoặc điểm tương tự thấp hơn ngưỡng.
    """
    sem = SemanticDocumentManager()
    try:
        sem_results = sem.search_similar(query, top_k=top_k, user_id=user_id)
        good = [r for r in sem_results if r.get("score", 0) >= SIMILARITY_THRESHOLD]
        if good:
            return {"source": "mongo_semantic", "results": good}

        # Không đủ tốt từ Mongo -> fallback Wikipedia
        wiki_list = wiki_search.invoke(query)
        first_title = None
        summary = None
        if wiki_list and isinstance(wiki_list, str):
            lines = [ln for ln in wiki_list.splitlines() if ln.strip()]
            if lines:
                first_line = lines[0]
                # Dòng: "- Title (vi|en): desc - url"
                if first_line.startswith("- ") and " (" in first_line:
                    first_title = first_line[2:first_line.index(" (" )].strip()
                    lang = "vi" if "(vi)" in first_line else "en"
                    summary = wiki_summary.invoke(f"{first_title}|{lang}")
        if not summary:
            summary = wiki_list or "Không tìm thấy kết quả trên Wikipedia."

        return {
            "source": "wikipedia",
            "results": [{"title": first_title or "Wikipedia", "summary": summary}]
        }
    finally:
        sem.close_connection()


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
                # Ưu tiên semantic Mongo, fallback Wikipedia
                fallback_data = retrieve_with_fallback(search_term, top_k=3, user_id=None)
                response["database_data"] = {
                    "type": fallback_data["source"],
                    "query": search_term,
                    "results": fallback_data["results"]
                }
        
        # Nếu không thuộc các nhóm trên, vẫn áp dụng chiến lược fallback
        if response["database_data"] is None:
            fb = retrieve_with_fallback(user_input, top_k=3, user_id=None)
            response["database_data"] = {
                "type": fb["source"],
                "query": user_input,
                "results": fb["results"]
            }
        
        # Now process with AI agent
        workflow = build_graph()
        
        # If we have database data, include it in the context
        if response["database_data"]:
            enhanced_input = f"{user_input}\n\nDatabase context: {json.dumps(response['database_data'], default=str, indent=2)}"
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
        print(f"\n{i}. Testing query: '{query}'")
        print("-" * 40)
        
        result = process_user_query_with_database(query)
        
        # Display database results if available
        if result.get("database_data"):
            db_data = result["database_data"]
            print(f"📊 Database results for {db_data['query']} (type={db_data['type']}):")
            
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
            
            elif db_data["type"] in ("semantic", "mongo_semantic"):
                for item in results[:3]:
                    title = item.get("file_name", "Document")
                    score = item.get("score", 0)
                    print(f"  ⭐ {title} - score={score:.3f}")
            
            elif db_data["type"] == "wikipedia":
                for item in results[:1]:
                    title = item.get("title", "Wikipedia")
                    summary = (item.get("summary", "") or "").splitlines()[0][:120]
                    print(f"  🌐 {title}: {summary}...")
        
        # Display AI response
        if result.get("ai_response"):
            print(f"\n🤖 AI Response: {result['ai_response']}")
        
        if result.get("error"):
            print(f"❌ Error: {result['error']}")
        
        print()

if __name__ == "__main__":
    main()
