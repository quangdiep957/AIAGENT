# 🚀 AI Agent Base with LangChain + LangGraph

## 📌 Mô tả
Dự án này là **khung cơ bản (base)** để dựng hệ thống **AI Agent** sử dụng:
- [LangChain](https://www.langchain.com/) → xử lý pipeline và công cụ
- [LangGraph](https://github.com/langchain-ai/langgraph) → xây dựng graph workflow
- OpenAI API (hoặc model khác) → LLM xử lý chính

Hiện tại project đã dựng **workflow cơ bản** gồm:
1. **Nhận input từ người dùng**
2. **Đi qua LLM Agent xử lý**
3. **Tạo ra response cuối cùng**

Bạn có thể dễ dàng mở rộng thêm các Agent và Tool mới vào `graph.py` để xử lý các nghiệp vụ phức tạp hơn.

---

## 📂 Cấu trúc thư mục
AIAGENT/
│── main.py # Entry point, chạy graph
│── graph.py # Xây dựng workflow graph
│── agents.py # Khai báo LLM / Agent
│── tools.py # Các tool mở rộng (API call, DB query, …)
│── requirements.txt # Các thư viện cần cài
│── README.md # Tài liệu này

yaml
Copy
Edit

---

## ⚙️ Cài đặt & chạy

### 1️⃣ Clone repo
```bash
git clone https://github.com/your-repo/AIAGENT.git
cd AIAGENT
2️⃣ Tạo môi trường ảo
bash
Copy
Edit
python -m venv venv
source venv/bin/activate   # MacOS/Linux
venv\Scripts\activate      # Windows
3️⃣ Cài dependencies
bash
Copy
Edit
pip install -r requirements.txt
4️⃣ Tạo file .env
Trong thư mục gốc, tạo file .env và thêm:

ini
Copy
Edit
OPENAI_API_KEY=your_api_key_here
5️⃣ Chạy project
bash
Copy
Edit
python main.py
🔄 Luồng hoạt động
main.py gọi build_graph() từ graph.py.

graph.py định nghĩa workflow gồm các node (Agent/Tool).

agents.py cung cấp get_llm() để tạo LLM (ví dụ ChatOpenAI).

Dữ liệu từ input sẽ đi qua graph → LLM → trả về response.

Bạn có thể mở rộng thêm tool ở tools.py (ví dụ gọi API ngoài, query database, …).

🔮 Mở rộng
Thêm nhiều Agent khác nhau (QA agent, Search agent, DB agent, …).

Thêm memory để giữ context nhiều vòng hội thoại.

Tích hợp với UI (Streamlit, FastAPI, Gradio, …).

Tích hợp với message queue hoặc workflow engine.

👨‍💻 Ví dụ chạy
bash
Copy
Edit
$ python main.py
Input: Xin chào
Output: Xin chào! Tôi có thể giúp gì cho bạn hôm nay?