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
    """ƯU TIÊN DÙNG TRƯỚC. Tìm kiếm ngữ nghĩa trên TẤT CẢ collections (MongoDB). Trả về 'NO_HITS' nếu không có."""
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
    """Tìm kiếm Wikipedia (vi/en) và trả về top kết quả (tiêu đề, mô tả, URL). Chỉ dùng khi semantic_search 'NO_HITS'."""
    def _search(lang: str):
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
    """Lấy tóm tắt bài Wikipedia. Đầu vào: "title|lang" (vd: "Pythagorean theorem|en")."""
    try:
        if "|" in title_and_lang:
            title, lang = [x.strip() for x in title_and_lang.split("|", 1)]
        else:
            title, lang = title_and_lang.strip(), "vi"
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

@tool("plan_study_schedule")
def plan_study_schedule(input: str) -> str:
    """Tạo kế hoạch/lịch học cá nhân hóa từ yêu cầu người dùng.
    Đầu vào có thể là:
    - Chuỗi: "goal|weeks|sessions_per_week|session_minutes|level|constraints"
    - Danh sách 1 phần tử: ["goal|weeks|..."] (nếu agent truyền nhầm, hãy dán vào đây như chuỗi)
    - JSON (chuỗi) với keys: goal, weeks, sessions_per_week, session_minutes, level, constraints
    Trả về: bản trình bày kế hoạch dễ đọc + JSON.
    """
    try:
        raw = input
        # Nếu agent truyền dạng list JSON trong chuỗi, hoặc list text, cố gắng bóc ra
        if isinstance(raw, list):
            raw = raw[0] if raw else ""
        
        goal = "Kế hoạch học tập"; weeks = 4; spw = 4; mins = 60; level = "intermediate"; constraints = None
        
        # Thử parse chuỗi JSON
        parsed_as_json = False
        d = None
        try:
            import json
            d = json.loads(raw) if isinstance(raw, str) else None
            if isinstance(d, dict):
                parsed_as_json = True
        except Exception:
            d = None
        
        if parsed_as_json and isinstance(d, dict):
            goal = d.get("goal", goal)
            weeks = int(d.get("weeks", weeks))
            spw = int(d.get("sessions_per_week", spw))
            mins = int(d.get("session_minutes", mins))
            level = d.get("level", level)
            constraints = d.get("constraints", constraints)
        else:
            # fallback: chuỗi pipe
            if not raw or not str(raw).strip():
                return (
                    "Thiếu đầu vào cho plan_study_schedule. Cách 1: goal|weeks|sessions_per_week|session_minutes|level|constraints\n"
                    "Cách 2 (JSON): {\"goal\":\"...\",\"weeks\":6,\"sessions_per_week\":4,\"session_minutes\":60,\"level\":\"beginner\",\"constraints\":\"...\"}"
                )
            parts = [x.strip() for x in str(raw).split("|")]
            goal = parts[0] if len(parts) > 0 and parts[0] else goal
            weeks = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else weeks
            spw = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else spw
            mins = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else mins
            level = parts[4] if len(parts) > 4 and parts[4] else level
            constraints = parts[5] if len(parts) > 5 and parts[5] else constraints

        from study_planner import plan_study
        result = plan_study(
            user_query=goal,
            duration_weeks=weeks,
            sessions_per_week=spw,
            session_minutes=mins,
            user_level=level,
            constraints=constraints
        )
        import json as _json
        plan = result.get("plan", {}) if isinstance(result, dict) else {}
        resources = result.get("resources", {}) if isinstance(result, dict) else {}
        
        # Render human-friendly output
        lines = []
        lines.append(f"🎯 Mục tiêu: {goal}")
        lines.append(f"⏱️ Thời lượng: {weeks} tuần · {spw} buổi/tuần · {mins} phút/buổi · Trình độ: {level}")
        if constraints:
            lines.append(f"⚙️ Ràng buộc: {constraints}")
        
        overview = plan.get("overview")
        if overview:
            lines.append("\n## Tổng quan")
            lines.append(str(overview))
        
        prereq = plan.get("prerequisites")
        if prereq:
            lines.append("\n## Kiến thức nền tảng")
            if isinstance(prereq, list):
                for it in prereq:
                    lines.append(f"- {it}")
            else:
                lines.append(str(prereq))
        
        weekly = plan.get("weekly_plan")
        if weekly:
            lines.append("\n## Kế hoạch theo tuần")
            if isinstance(weekly, list):
                for i, wk in enumerate(weekly, 1):
                    lines.append(f"### Tuần {i}")
                    if isinstance(wk, dict):
                        for k, v in wk.items():
                            if isinstance(v, list):
                                lines.append(f"- {k}:")
                                for x in v:
                                    lines.append(f"  - {x}")
                            else:
                                lines.append(f"- {k}: {v}")
                    else:
                        lines.append(f"- {wk}")
            elif isinstance(weekly, dict):
                for wk_name, wk in weekly.items():
                    lines.append(f"### {wk_name}")
                    if isinstance(wk, dict):
                        for k, v in wk.items():
                            if isinstance(v, list):
                                lines.append(f"- {k}:")
                                for x in v:
                                    lines.append(f"  - {x}")
                            else:
                                lines.append(f"- {k}: {v}")
                    else:
                        lines.append(f"- {wk}")
        
        samples = plan.get("daily_schedule_samples")
        if samples:
            lines.append("\n## Ví dụ lịch học trong tuần")
            if isinstance(samples, list):
                for s in samples:
                    lines.append(f"- {s}")
            elif isinstance(samples, dict):
                for day, s in samples.items():
                    lines.append(f"- {day}: {s}")
            else:
                lines.append(str(samples))
        
        assess = plan.get("assessment_strategy") or plan.get("assessment")
        if assess:
            lines.append("\n## Đánh giá & Ôn tập")
            if isinstance(assess, list):
                for it in assess:
                    lines.append(f"- {it}")
            else:
                lines.append(str(assess))
        
        lines.append("\n## Nguồn tài nguyên đã dùng")
        lines.append(f"- Nguồn: {resources.get('source', 'unknown')}")
        if isinstance(resources.get('items'), list):
            for it in resources['items'][:5]:
                title = it.get('file_name') or it.get('title') or 'Tài liệu'
                lines.append(f"  - {title}")
        
        # JSON ở cuối để tham khảo/ghi log
        lines.append("\n---\n(JSON kế hoạch)\n")
        lines.append(_json.dumps(result, ensure_ascii=False, indent=2))
        
        return "\n".join(lines)
    except Exception as e:
        return f"Lỗi tạo kế hoạch học: {e}"


@tool("plan_study_auto")
def plan_study_auto(input: str) -> str:
    """Phân tích yêu cầu tự do của người dùng (tiếng Việt/Anh) để suy ra: goal, weeks, sessions_per_week, session_minutes, level, constraints; sau đó tạo kế hoạch học tương ứng và trả JSON kết quả. Không yêu cầu tham số cố định."""
    try:
        if not input or not input.strip():
            return "Vui lòng mô tả mục tiêu học và kỳ vọng lịch học (ví dụ: 'Ôn thi tiếng Anh lớp 10 trong 6 tuần, 4 buổi/tuần, học buổi tối')."
        from langchain_openai import ChatOpenAI
        import json
        from study_planner import plan_study
        import config  # ensure dotenv
        
        llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
        sys = (
            "Trích xuất tham số lập kế hoạch học từ mô tả: goal, weeks (int), sessions_per_week (int), "
            "session_minutes (int, mặc định 60 nếu không rõ), level (beginner/intermediate/advanced), constraints (text). "
            "Nếu không nêu rõ, đặt giá trị hợp lý mặc định (weeks=4, sessions_per_week=4, session_minutes=60, level='intermediate'). "
            "Chỉ trả về JSON với các khóa trên, không thêm lời giải thích."
        )
        usr = input
        resp = llm.invoke([
            {"role": "system", "content": sys},
            {"role": "user", "content": usr}
        ])
        content = resp.content if hasattr(resp, "content") else str(resp)
        try:
            params = json.loads(content)
        except Exception:
            params = {
                "goal": input,
                "weeks": 4,
                "sessions_per_week": 4,
                "session_minutes": 60,
                "level": "intermediate",
                "constraints": None
            }
        result = plan_study(
            user_query=params.get("goal", input),
            duration_weeks=int(params.get("weeks", 4)),
            sessions_per_week=int(params.get("sessions_per_week", 4)),
            session_minutes=int(params.get("session_minutes", 60)),
            user_level=str(params.get("level", "intermediate")),
            constraints=params.get("constraints")
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Lỗi plan_study_auto: {e}"
