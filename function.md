📘 AI Study Assistant – RAG-based (English Exam Preparation)
1. Giới thiệu

Đề tài xây dựng một AI Trợ lý học tập ôn thi môn Tiếng Anh dựa trên mô hình RAG (Retrieval-Augmented Generation).
Người dùng có thể upload file tài liệu ôn tập (PDF/DOCX/TXT), hệ thống sẽ lưu trữ, phân tích và trả lời các câu hỏi dựa trên nội dung tài liệu.

2. Công nghệ & Tools sử dụng
🔹 Ngôn ngữ & Framework

Python (FastAPI hoặc Flask làm backend)

LangChain / LangGraph để điều phối agent & tools

MongoDB Atlas (Database + Vector Store)

🔹 Embedding & LLM

OpenAI GPT-4.1 hoặc GPT-4.1-mini để sinh embedding & trả lời

text-embedding-3-small hoặc text-embedding-3-large cho tạo vector embedding

🔹 Tools bắt buộc (≥10 tools)

File Upload Tool – tải file PDF/DOCX/TXT

File Parser Tool – trích xuất text từ file

Text Splitter Tool – chia nhỏ text thành chunks

Embedding Tool – sinh vector embeddings

MongoDB Store Tool – lưu embedding + metadata vào MongoDB

Vector Search Tool – tìm đoạn liên quan khi người dùng hỏi

Q&A Tool (LLM Query) – gọi GPT-4.1 để sinh câu trả lời

Quiz Generator Tool – tạo câu hỏi trắc nghiệm luyện thi

Summary Tool – tóm tắt tài liệu ôn tập

Export Tool – xuất kết quả ra PDF/Word/JSON

3. Kiến trúc Hệ thống (RAG Flow)

Luồng hoạt động Upload & Query

User Upload File → qua Upload Tool

File Parser Tool → trích xuất text

Text Splitter Tool → chia nhỏ text thành chunks

Embedding Tool → tạo embeddings từ chunks

MongoDB Store Tool → lưu {chunk_text, embedding, file_id, metadata}

User đặt câu hỏi → query đến hệ thống

Vector Search Tool → tìm top-k chunks liên quan từ MongoDB

Q&A Tool (LLM) → kết hợp context + câu hỏi → sinh câu trả lời

Kết quả trả về → có thể hiển thị hoặc export bằng Export Tool

4. Database Design (MongoDB Atlas)
{
  "file_id": "123abc",
  "file_name": "grammar_notes.pdf",
  "chunk_text": "Present Perfect is used for...",
  "embedding": [0.123, -0.234, ...],
  "page_number": 5,
  "created_at": "2025-08-22"
}

5. Output formats

Plain text → trả lời trực tiếp trên UI/Chat

Quiz (JSON/MCQ) → luyện thi trắc nghiệm

Summary (Text/PDF) → ôn tập nhanh

6. Điểm nhấn để thuyết trình

Áp dụng RAG (truy xuất tri thức từ MongoDB thay vì LLM “bịa”)

Có 10 tools rõ ràng → đảm bảo yêu cầu đề tài

Tập trung vào ôn thi Tiếng Anh → thực tế & dễ minh họa demo