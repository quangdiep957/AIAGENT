# tools.py
from langchain.tools import tool
import requests
from semantic_document_manager import SemanticDocumentManager

@tool
def get_weather(city: str) -> str:
    """Trả về thông tin thời tiết của một thành phố."""
    url = f"https://wttr.in/{city}?format=3"
    response = requests.get(url)
    print(f"[LOG] Tool used: get_weather | input={city}")
    return response.text

@tool
def calculate_sum(numbers: str) -> str:
    """Tính tổng của hai số nguyên được cung cấp dưới dạng chuỗi cách nhau bằng dấu phẩy. Ví dụ: '5,3' sẽ trả về 8."""
    try:
        # Tách chuỗi thành các số
        num_list = [int(x.strip()) for x in numbers.split(',')]
        if len(num_list) != 2:
            return "Lỗi: Tool chỉ hỗ trợ đúng 2 số, cách nhau bằng dấu phẩy"
        
        a, b = num_list
        result = a + b
        print(f"[LOG] Tool used: calculate_sum | input={numbers}")
        return f"Tổng của {a} + {b} = {result}"
    except ValueError:
        return "Lỗi: Vui lòng nhập đúng định dạng số, ví dụ: '5,3'"

@tool
def semantic_search(query: str) -> str:
    """ƯU TIÊN DÙNG TRƯỚC. Tìm kiếm ngữ nghĩa trên TẤT CẢ collections (MongoDB) và trả về top kết quả.
    Chỉ nên dùng Wikipedia khi công cụ này không có kết quả phù hợp. Trả về 'NO_HITS' nếu không có.
    """
    SIMILARITY_THRESHOLD = 0.35
    sem = SemanticDocumentManager()
    try:
        results = sem.search_similar_all_collections(query, top_k=3)
        good = [r for r in results if r.get("score", 0) >= SIMILARITY_THRESHOLD]
        if not good:
            print(f"[LOG] Tool used: semantic_search | input={query} | hits=0 (all cols)")
            return "NO_HITS"
        lines = []
        for r in good:
            title = r.get("file_name", "Document")
            score = r.get("score", 0)
            col = r.get("_collection", "?")
            preview = (r.get("content", "") or "")[:160].replace('\n',' ')
            lines.append(f"- [{col}] {title} | score={score:.3f} | {preview}...")
        print(f"[LOG] Tool used: semantic_search | input={query} | hits={len(lines)} (all cols)")
        return "\n".join(lines)
    except Exception as e:
        return f"Lỗi semantic_search: {e}"
    finally:
        sem.close_connection()

@tool
def wiki_search(query: str) -> str:
    """Tìm kiếm Wikipedia (vi/en) và trả về top kết quả dạng danh sách có tiêu đề, tóm tắt ngắn và URL.
    Chỉ dùng khi semantic_search trả về 'NO_HITS' hoặc không đủ thông tin từ tài liệu người dùng.
    """
    def _search(lang: str):
        # Wikipedia Search API (REST)
        # Tài liệu: https://api.wikimedia.org/wiki/REST_API#Search
        url = f"https://{lang}.wikipedia.org/w/rest.php/v1/search/title"
        params = {"q": query, "limit": 5}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    
    def _page_url(lang: str, title: str) -> str:
        from urllib.parse import quote
        return f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
    
    try:
        data = _search("vi")
        items = data.get("pages", [])
        lang_used = "vi"
        if not items:
            data = _search("en")
            items = data.get("pages", [])
            lang_used = "en"
        if not items:
            return "Không tìm thấy kết quả trên Wikipedia."
        
        results = []
        for it in items:
            title = it.get("title", "")
            description = it.get("description", "") or ""
            url = _page_url(lang_used, title)
            results.append({"title": title, "description": description, "url": url, "lang": lang_used})
        
        print(f"[LOG] Tool used: wiki_search | input={query} | lang={lang_used} | hits={len(results)}")
        lines = [f"- {x['title']} ({x['lang']}): {x['description']} - {x['url']}" for x in results]
        return "\n".join(lines)
    except Exception as e:
        return f"Lỗi khi gọi Wikipedia: {e}"

@tool
def wiki_summary(title_and_lang: str) -> str:
    """Lấy tóm tắt ngắn cho một bài Wikipedia.
    Đầu vào: "title|lang". Ví dụ: "Pythagorean theorem|en" hoặc "Định luật II Newton|vi".
    Trả về: tiêu đề, tóm tắt, và URL bài viết.
    """
    try:
        if "|" in title_and_lang:
            title, lang = [x.strip() for x in title_and_lang.split("|", 1)]
        else:
            title, lang = title_and_lang.strip(), "vi"
        
        # Summary API
        from urllib.parse import quote
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        extract = data.get("extract") or data.get("description") or "Không có tóm tắt."
        fullurl = data.get("content_urls", {}).get("desktop", {}).get("page") or data.get("titles", {}).get("canonical")
        from urllib.parse import quote as _q
        fullurl = fullurl or f"https://{lang}.wikipedia.org/wiki/{_q(title)}"
        print(f"[LOG] Tool used: wiki_summary | title={title} | lang={lang}")
        return f"{data.get('title', title)} ({lang})\n{extract}\n{fullurl}"
    except Exception as e:
        return f"Lỗi khi lấy tóm tắt Wikipedia: {e}"