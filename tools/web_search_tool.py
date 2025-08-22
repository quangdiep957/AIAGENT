"""
Web Search Tool - Tool tìm kiếm web với GPT-4.1 và đánh giá kết quả
"""

from langchain.tools import tool
from langchain_openai import ChatOpenAI
import requests
from typing import Dict, Any, List
import json
import time
from datetime import datetime

class WebSearchTool:
    """Tool tìm kiếm web với GPT-4.1"""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4.1", temperature=0.2)
        self.search_engines = {
            "duckduckgo": "https://api.duckduckgo.com/",
            "searx": "https://searx.space/search"  # Public instance
        }
    
    def search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict]:
        """Tìm kiếm qua DuckDuckGo API"""
        try:
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = requests.get(
                "https://api.duckduckgo.com/",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                # Lấy kết quả từ RelatedTopics
                if 'RelatedTopics' in data:
                    for topic in data['RelatedTopics'][:max_results]:
                        if isinstance(topic, dict) and 'Text' in topic:
                            results.append({
                                'title': topic.get('Text', '')[:100],
                                'content': topic.get('Text', ''),
                                'url': topic.get('FirstURL', ''),
                                'source': 'DuckDuckGo'
                            })
                
                # Nếu không có RelatedTopics, dùng Abstract
                if not results and 'Abstract' in data and data['Abstract']:
                    results.append({
                        'title': data.get('Heading', 'Search Result'),
                        'content': data['Abstract'],
                        'url': data.get('AbstractURL', ''),
                        'source': 'DuckDuckGo'
                    })
                
                return results
            
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
        
        return []
    
    def search_with_llm_fallback(self, query: str) -> List[Dict]:
        """Tìm kiếm với LLM fallback khi API không khả dụng"""
        try:
            # Thử tìm kiếm qua API trước
            results = self.search_duckduckgo(query)
            
            if results:
                return results
            
            # Fallback: Dùng LLM để tạo nội dung dựa trên kiến thức
            llm_prompt = f"""
            Người dùng tìm kiếm: "{query}"
            
            Vì không tìm thấy kết quả web search, hãy cung cấp thông tin hữu ích dựa trên kiến thức của bạn.
            Tập trung vào giáo dục tiếng Anh và học tập.
            
            Trả về JSON format:
            {{
                "title": "Tiêu đề thông tin",
                "content": "Nội dung chi tiết (tiếng Việt + English examples nếu có)",
                "source": "GPT-4.1 Knowledge",
                "relevance": "high/medium/low"
            }}
            """
            
            llm_response = self.llm.invoke(llm_prompt)
            
            try:
                # Parse JSON từ LLM response
                import re
                json_match = re.search(r'\{.*\}', llm_response.content, re.DOTALL)
                if json_match:
                    result_data = json.loads(json_match.group())
                    return [{
                        'title': result_data.get('title', 'Knowledge Base Result'),
                        'content': result_data.get('content', llm_response.content),
                        'url': '',
                        'source': 'GPT-4.1 Knowledge',
                        'relevance': result_data.get('relevance', 'medium')
                    }]
            except:
                # Nếu không parse được JSON, dùng raw content
                return [{
                    'title': f'Thông tin về: {query}',
                    'content': llm_response.content,
                    'url': '',
                    'source': 'GPT-4.1 Knowledge',
                    'relevance': 'medium'
                }]
                
        except Exception as e:
            return [{
                'title': 'Lỗi tìm kiếm',
                'content': f'Không thể tìm kiếm thông tin về "{query}". Lỗi: {str(e)}',
                'url': '',
                'source': 'Error',
                'relevance': 'low'
            }]
    
    def evaluate_search_results(self, query: str, results: List[Dict]) -> Dict[str, Any]:
        """Đánh giá kết quả tìm kiếm bằng LLM"""
        try:
            if not results:
                return {
                    "is_relevant": False,
                    "quality_score": 0,
                    "summary": "Không tìm thấy kết quả nào",
                    "recommendation": "llm_response"
                }
            
            # Tạo prompt đánh giá
            results_text = "\n\n".join([
                f"Kết quả {i+1}:\nTiêu đề: {r['title']}\nNội dung: {r['content'][:300]}..."
                for i, r in enumerate(results[:3])
            ])
            
            evaluation_prompt = f"""
            Câu hỏi gốc: "{query}"
            
            Kết quả tìm kiếm:
            {results_text}
            
            Hãy đánh giá:
            1. Các kết quả có liên quan đến câu hỏi không?
            2. Chất lượng thông tin (1-10)
            3. Có đủ thông tin để trả lời không?
            
            Trả về JSON:
            {{
                "is_relevant": true/false,
                "quality_score": 1-10,
                "summary": "Tóm tắt ngắn gọn về kết quả",
                "recommendation": "use_search" hoặc "llm_response"
            }}
            
            Lưu ý: Nếu kết quả tốt và liên quan, chọn "use_search". Nếu không đủ tốt, chọn "llm_response".
            """
            
            evaluation = self.llm.invoke(evaluation_prompt)
            
            try:
                # Parse JSON từ evaluation
                import re
                json_match = re.search(r'\{.*\}', evaluation.content, re.DOTALL)
                if json_match:
                    eval_data = json.loads(json_match.group())
                    return eval_data
            except:
                pass
            
            # Fallback evaluation
            return {
                "is_relevant": len(results) > 0,
                "quality_score": 5,
                "summary": f"Tìm thấy {len(results)} kết quả",
                "recommendation": "use_search" if results else "llm_response"
            }
            
        except Exception as e:
            return {
                "is_relevant": False,
                "quality_score": 0,
                "summary": f"Lỗi đánh giá: {str(e)}",
                "recommendation": "llm_response"
            }

# Khởi tạo tool instance
web_search_tool = WebSearchTool()

@tool
def search_web_with_evaluation(query: str) -> str:
    """
    Tìm kiếm thông tin trên web khi knowledge base không có, sau đó đánh giá kết quả
    
    Args:
        query: Câu hỏi hoặc từ khóa cần tìm kiếm
    
    Returns:
        Kết quả tìm kiếm đã được đánh giá hoặc gợi ý sử dụng LLM
    """
    try:
        # Bước 1: Tìm kiếm web
        search_results = web_search_tool.search_with_llm_fallback(query)
        
        if not search_results:
            return """🌐 **Không tìm thấy kết quả web**

❌ Không có thông tin từ tìm kiếm web
💡 **Gợi ý:** LLM sẽ trả lời dựa trên kiến thức có sẵn

**Trạng thái:** llm_response_needed"""
        
        # Bước 2: Đánh giá kết quả
        evaluation = web_search_tool.evaluate_search_results(query, search_results)
        
        # Bước 3: Quyết định response
        if evaluation.get("recommendation") == "use_search" and evaluation.get("quality_score", 0) >= 6:
            # Kết quả tốt, hiển thị search results
            formatted_results = []
            for i, result in enumerate(search_results[:3], 1):
                formatted_results.append(f"""
🔍 **Kết quả {i}**
📝 **Tiêu đề:** {result['title']}
🌐 **Nguồn:** {result['source']}
📄 **Nội dung:** {result['content'][:400]}{'...' if len(result['content']) > 400 else ''}
{f"🔗 **Link:** {result['url']}" if result['url'] else ''}
""")
            
            return f"""🌐 **Kết quả tìm kiếm web**

📊 **Đánh giá:** {evaluation['summary']}
⭐ **Chất lượng:** {evaluation['quality_score']}/10

{''.join(formatted_results)}

💡 **Dựa trên kết quả trên, tôi có thể giúp bạn trả lời câu hỏi chi tiết hơn.**
**Trạng thái:** search_results_ready"""
        
        else:
            # Kết quả không tốt, gợi ý dùng LLM
            return f"""🌐 **Kết quả tìm kiếm web không đạt yêu cầu**

📊 **Đánh giá:** {evaluation['summary']}
⭐ **Chất lượng:** {evaluation['quality_score']}/10

❌ **Lý do:** Thông tin không đủ chính xác hoặc không liên quan
💡 **Gợi ý:** LLM sẽ trả lời dựa trên kiến thức chuyên môn

**Trạng thái:** llm_response_needed"""
            
    except Exception as e:
        return f"""🌐 **Lỗi tìm kiếm web**

❌ **Lỗi:** {str(e)}
💡 **Gợi ý:** LLM sẽ trả lời dựa trên kiến thức có sẵn

**Trạng thái:** llm_response_needed"""

@tool
def generate_llm_response_for_query(query: str) -> str:
    """
    Tạo response bằng LLM khi web search không khả dụng hoặc không phù hợp
    
    Args:
        query: Câu hỏi cần trả lời
    
    Returns:
        Response từ LLM dựa trên kiến thức có sẵn
    """
    try:
        llm = ChatOpenAI(model="gpt-4.1", temperature=0.3)
        
        response_prompt = f"""
        Câu hỏi: "{query}"
        
        Bạn là AI Tutor chuyên về tiếng Anh. Hãy trả lời câu hỏi trên dựa trên kiến thức của bạn.
        
        Quy tắc:
        1. Trả lời bằng tiếng Việt để giải thích
        2. Giữ nguyên nội dung tiếng Anh (examples, grammar rules) 
        3. Cung cấp ví dụ cụ thể
        4. Tạo bài tập nếu phù hợp
        5. Đánh dấu rõ đây là response từ kiến thức AI
        
        Format response:
        🤖 **AI Tutor Response**
        [Nội dung trả lời chi tiết]
        
        💡 *Lưu ý: Thông tin này dựa trên kiến thức AI. Bạn có thể tham khảo thêm nguồn khác.*
        """
        
        llm_response = llm.invoke(response_prompt)
        return llm_response.content
        
    except Exception as e:
        return f"""🤖 **AI Tutor Response**

Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi: "{query}"

❌ **Lỗi:** {str(e)}

💡 **Gợi ý:** Bạn có thể:
- Diễn đạt lại câu hỏi
- Chia nhỏ câu hỏi thành nhiều phần
- Upload tài liệu liên quan để tôi có thêm ngữ cảnh

*Lưu ý: Đây là response tự động từ AI Tutor.*"""
