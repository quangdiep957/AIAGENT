# 🗄️ Database Module - Hướng Dẫn Sử Dụng

## 📁 Cấu Trúc File

Sau khi refactor, code database được chia thành các file riêng biệt để dễ đọc và maintain:

```
database/
├── database.py                    # Module chính (import các class)
├── database_manager.py            # DatabaseManager - Quản lý MongoDB cơ bản
├── semantic_document_manager.py   # SemanticDocumentManager - Quản lý documents với AI
└── README_database.md            # Hướng dẫn này
```

## 🎯 Các Class Chính

### 1. DatabaseManager (`database_manager.py`)
**Chức năng**: Quản lý kết nối MongoDB cơ bản
- ✅ Kết nối database
- ✅ Quản lý collections
- ✅ CRUD operations cơ bản
- ✅ Đếm documents
- ✅ Tìm kiếm text đơn giản

**Cách sử dụng**:
```python
from database_manager import DatabaseManager

# Khởi tạo
db_manager = DatabaseManager()

# Lấy collections
collections = db_manager.get_collections()

# Lấy dữ liệu
data = db_manager.get_data_from_collection("users", limit=10)

# Đóng kết nối
db_manager.close_connection()
```

### 2. SemanticDocumentManager (`semantic_document_manager.py`)
**Chức năng**: Quản lý documents với AI semantic search
- 🧠 OpenAI embeddings
- 🔍 Semantic search với cosine similarity
- 👤 Quản lý theo user
- 📄 CRUD operations đầy đủ
- 🗑️ Xóa documents

**Cách sử dụng**:
```python
from semantic_document_manager import SemanticDocumentManager

# Khởi tạo
semantic_manager = SemanticDocumentManager()

# Lưu document
doc_id = semantic_manager.save_document(
    user_id="user1",
    file_name="document.pdf",
    content="Nội dung document..."
)

# Tìm kiếm semantic
results = semantic_manager.search_similar("câu hỏi tìm kiếm", top_k=3)

# Lấy documents của user
user_docs = semantic_manager.get_user_documents("user1")

# Xóa document
semantic_manager.delete_document(doc_id, "user1")

# Đóng kết nối
semantic_manager.close_connection()
```

## 🚀 Cách Test

### Test DatabaseManager cơ bản:
```bash
python database_manager.py
```

### Test SemanticDocumentManager:
```bash
python semantic_document_manager.py
```

### Test tất cả tính năng:
```bash
python database.py
```

## 🔧 Cấu Hình

Đảm bảo file `.env` có các biến:
```env
OPENAI_API_KEY="your_openai_api_key"
CONNECTION="your_mongodb_connection_string"
```

## 💡 Lợi Ích Sau Khi Refactor

1. **Dễ đọc**: Mỗi file chỉ chứa một class, dễ hiểu
2. **Dễ maintain**: Sửa lỗi hoặc thêm tính năng chỉ cần sửa file tương ứng
3. **Tái sử dụng**: Có thể import riêng từng class khi cần
4. **Test riêng biệt**: Mỗi class có thể test độc lập
5. **Code sạch**: Không bị lẫn lộn giữa các chức năng

## 📚 Ví Dụ Sử Dụng Trong Dự Án

```python
# Trong main_with_database.py
from database import DatabaseManager, SemanticDocumentManager

# Sử dụng DatabaseManager cho dữ liệu cơ bản
db_manager = DatabaseManager()
users = db_manager.get_data_from_collection("users")

# Sử dụng SemanticDocumentManager cho tìm kiếm documents
semantic_manager = SemanticDocumentManager()
documents = semantic_manager.search_similar("AI và machine learning")
```

## 🆘 Troubleshooting

### Lỗi thường gặp:
1. **Không tìm thấy OPENAI_API_KEY**: Kiểm tra file `.env`
2. **Không kết nối được MongoDB**: Kiểm tra connection string
3. **ModuleNotFoundError**: Cài đặt các dependencies cần thiết

### Dependencies cần thiết:
```bash
pip install pymongo python-dotenv langchain-openai numpy
```

## 🎉 Kết Luận

Sau khi refactor, code database trở nên:
- 📖 **Dễ đọc** hơn cho người mới
- 🔧 **Dễ maintain** và debug
- 🚀 **Dễ mở rộng** tính năng mới
- 🧪 **Dễ test** từng component riêng biệt

Bây giờ bạn có thể dễ dàng hiểu và sử dụng từng class một cách độc lập!
