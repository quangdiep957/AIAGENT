from typing import List, Dict, Any, Optional
import json

from semantic_document_manager import SemanticDocumentManager
from tools.builtin_tools import wiki_search, wiki_summary
from langchain_openai import ChatOpenAI
import config  # ensure dotenv loaded

SIMILARITY_THRESHOLD = 0.35


def _compact_resources(resources: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    compact: Dict[str, Any] = {"source": resources.get("source") if resources else None, "items": []}
    if resources and isinstance(resources.get("items"), list):
        for it in resources["items"][:5]:
            if isinstance(it, dict):
                preview = (it.get("content", "") or "")[:200].replace("\n", " ")
                compact["items"].append({
                    "title": it.get("file_name") or it.get("title") or "resource",
                    "score": it.get("score"),
                    "collection": it.get("_collection"),
                    "preview": preview
                })
            else:
                compact["items"].append(str(it)[:200])
    return compact


def collect_resources(topic: str, top_k: int = 5, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Thu thập tài nguyên từ MongoDB (semantic, all collections). Fallback Wikipedia nếu thiếu.
    """
    sem = SemanticDocumentManager()
    try:
        sem_results = sem.search_similar_all_collections(topic, top_k=top_k, user_id=user_id)
        good = [r for r in sem_results if r.get("score", 0) >= SIMILARITY_THRESHOLD]
        resources: Dict[str, Any] = {"source": "mongo_semantic", "items": good}
        if not good:
            # fallback
            wiki_list = wiki_search.run(topic) if hasattr(wiki_search, "run") else wiki_search.invoke(topic)
            first_summary = None
            if isinstance(wiki_list, str) and wiki_list.strip():
                first_line = wiki_list.splitlines()[0]
                if first_line.startswith("- ") and " (" in first_line:
                    title = first_line[2:first_line.index(" (" )].strip()
                    lang = "vi" if "(vi)" in first_line else "en"
                    first_summary = wiki_summary.run(f"{title}|{lang}") if hasattr(wiki_summary, "run") else wiki_summary.invoke(f"{title}|{lang}")
            resources = {
                "source": "wikipedia",
                "items": [{"title": topic, "summary": first_summary or wiki_list}]
            }
        return resources
    finally:
        sem.close_connection()


def generate_study_plan(
    goal: str,
    duration_weeks: int = 4,
    sessions_per_week: int = 4,
    session_minutes: int = 60,
    user_level: str = "intermediate",
    constraints: Optional[str] = None,
    resources: Optional[Dict[str, Any]] = None,
    model: str = "gpt-4.1-mini"
) -> Dict[str, Any]:
    """
    Sinh kế hoạch học tập chi tiết dựa trên mục tiêu và tài nguyên có sẵn.
    Trả về dict có keys: overview, prerequisites, weekly_plan, daily_schedule_samples, resources_used.
    """
    # Dọn gọn tài nguyên để giảm token và tăng tốc
    compact = _compact_resources(resources)

    llm = ChatOpenAI(model=model, temperature=0.2, max_tokens=1200)

    system = (
        "Bạn là một gia sư học tập tạo kế hoạch học tập chi tiết, cân bằng lý thuyết và bài tập. "
        "Ưu tiên sử dụng tài liệu đã có của người dùng nếu phù hợp. Kế hoạch cần cụ thể, khả thi, và có kiểm tra đánh giá." 
    )

    prompt = f"""
Mục tiêu học tập: {goal}
Thời lượng: {duration_weeks} tuần; mỗi tuần {sessions_per_week} buổi; mỗi buổi {session_minutes} phút
Trình độ người học: {user_level}
Ràng buộc: {constraints or 'Không có'}

Tài nguyên sẵn có (rút gọn, JSON):
{json.dumps(compact or {}, ensure_ascii=False, indent=2)}

Yêu cầu:
1) Tóm tắt mục tiêu và lộ trình tổng quan (overview)
2) Liệt kê kiến thức nền tảng cần có (prerequisites) và cách bù đắp nếu thiếu
3) Lập kế hoạch theo tuần (weekly_plan), mỗi tuần liệt kê các buổi học: mục tiêu, nội dung, bài tập, tài nguyên tham chiếu (chỉ rõ nguồn)
4) Đưa ví dụ lịch hằng ngày (daily_schedule_samples) dựa trên {sessions_per_week} buổi/tuần, mỗi buổi {session_minutes} phút
5) Chiến lược ôn tập, kiểm tra định kỳ, tiêu chí đánh giá tiến bộ
6) Liệt kê tài nguyên đã dùng (resources_used) với nguồn Mongo/Wikipedia

Đầu ra ở dạng JSON thuần có các keys: overview, prerequisites, weekly_plan, daily_schedule_samples, assessment_strategy, resources_used.
"""

    result = llm.invoke([
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ])

    # Cố gắng parse JSON
    content = result.content if hasattr(result, "content") else str(result)
    try:
        data = json.loads(content)
    except Exception:
        # Nếu model trả text thường, cố gắng tìm block JSON
        import re
        match = re.search(r"\{[\s\S]*\}$", content.strip())
        if match:
            data = json.loads(match.group(0))
        else:
            data = {"raw": content}
    return data


def plan_study(
    user_query: str,
    duration_weeks: int = 4,
    sessions_per_week: int = 4,
    session_minutes: int = 60,
    user_level: str = "intermediate",
    constraints: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pipeline: thu thập tài nguyên -> sinh kế hoạch -> trả về kết quả cấu trúc.
    """
    # giảm top_k để nhanh hơn
    resources_full = collect_resources(user_query, top_k=3, user_id=user_id)
    plan = generate_study_plan(
        goal=user_query,
        duration_weeks=duration_weeks,
        sessions_per_week=sessions_per_week,
        session_minutes=session_minutes,
        user_level=user_level,
        constraints=constraints,
        resources=resources_full,
        model="gpt-4.1-mini"
    )
    # Trả về resources đã compact để giảm log và kích thước output
    return {"resources": _compact_resources(resources_full), "plan": plan}
