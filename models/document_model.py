"""
Document Model - Schema cho documents trong MongoDB
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

class DocumentModel:
    """Schema cho document objects"""
    
    @staticmethod
    def create_file_document(filename: str, 
                           file_type: str, 
                           file_path: str, 
                           file_size: int,
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Tạo document schema cho uploaded files
        
        Args:
            filename (str): Tên file gốc
            file_type (str): Loại file (pdf, word, image, text)
            file_path (str): Đường dẫn file
            file_size (int): Kích thước file
            metadata (Dict): Metadata bổ sung
            
        Returns:
            Dict[str, Any]: Document schema
        """
        return {
            "_id": str(uuid.uuid4()),
            "filename": filename,
            "file_type": file_type,
            "file_path": file_path,
            "file_size": file_size,
            "upload_date": datetime.utcnow(),
            "processed": False,
            "processing_status": "uploaded",  # uploaded, processing, completed, failed
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    @staticmethod
    def create_content_document(file_id: str,
                              content: str,
                              content_type: str = "text",
                              page_number: int = None,
                              chunk_index: int = None,
                              metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Tạo document schema cho extracted content
        
        Args:
            file_id (str): ID của file gốc
            content (str): Nội dung đã extract
            content_type (str): Loại content (text, table, image_text)
            page_number (int): Số trang (nếu có)
            chunk_index (int): Index của chunk
            metadata (Dict): Metadata bổ sung
            
        Returns:
            Dict[str, Any]: Content document schema
        """
        return {
            "_id": str(uuid.uuid4()),
            "file_id": file_id,
            "content": content,
            "content_type": content_type,
            "page_number": page_number,
            "chunk_index": chunk_index,
            "word_count": len(content.split()) if content else 0,
            "char_count": len(content) if content else 0,
            "metadata": metadata or {},
            "extracted_at": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
    
    @staticmethod
    def create_embedding_document(file_id: str,
                                content: str,
                                embedding: List[float],
                                doc_type: str = "general",
                                topic: str = None,
                                chunk_index: int = 0,
                                metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Tạo document schema cho embeddings
        
        Args:
            file_id (str): ID của file gốc
            content (str): Nội dung text
            embedding (List[float]): Vector embedding
            doc_type (str): Loại document (grammar, vocabulary, reading, etc.)
            topic (str): Chủ đề
            chunk_index (int): Index của chunk
            metadata (Dict): Metadata bổ sung
            
        Returns:
            Dict[str, Any]: Embedding document schema
        """
        return {
            "_id": str(uuid.uuid4()),
            "file_id": file_id,
            "type": doc_type,
            "topic": topic,
            "content": content,
            "embedding": embedding,
            "chunk_index": chunk_index,
            "embedding_model": metadata.get("embedding_model", "text-embedding-3-small"),
            "embedding_dimensions": len(embedding),
            "word_count": len(content.split()) if content else 0,
            "char_count": len(content) if content else 0,
            "content_hash": metadata.get("content_hash"),
            "metadata": {
                "page_number": metadata.get("page_number"),
                "language": metadata.get("language", "vi"),
                "subject": metadata.get("subject"),
                "difficulty_level": metadata.get("difficulty_level"),
                "tags": metadata.get("tags", []),
                **metadata
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    @staticmethod
    def create_processing_log(file_id: str,
                            stage: str,
                            status: str,
                            message: str = None,
                            error_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Tạo log cho quá trình xử lý
        
        Args:
            file_id (str): ID của file
            stage (str): Giai đoạn xử lý (upload, extract, ocr, embed, etc.)
            status (str): Trạng thái (started, completed, failed)
            message (str): Thông điệp
            error_details (Dict): Chi tiết lỗi nếu có
            
        Returns:
            Dict[str, Any]: Processing log schema
        """
        return {
            "_id": str(uuid.uuid4()),
            "file_id": file_id,
            "stage": stage,
            "status": status,
            "message": message,
            "error_details": error_details,
            "timestamp": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
    
    @staticmethod
    def create_search_query_log(query_text: str,
                              search_type: str,
                              results_count: int,
                              filters: Dict[str, Any] = None,
                              user_id: str = None) -> Dict[str, Any]:
        """
        Tạo log cho search queries
        
        Args:
            query_text (str): Text query
            search_type (str): Loại search (vector, keyword, hybrid)
            results_count (int): Số kết quả trả về
            filters (Dict): Filters đã áp dụng
            user_id (str): ID người dùng
            
        Returns:
            Dict[str, Any]: Search query log schema
        """
        return {
            "_id": str(uuid.uuid4()),
            "query_text": query_text,
            "search_type": search_type,
            "results_count": results_count,
            "filters": filters or {},
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }

class DocumentValidator:
    """Validator cho document schemas"""
    
    @staticmethod
    def validate_file_document(doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate file document
        
        Args:
            doc (Dict): Document cần validate
            
        Returns:
            Dict[str, Any]: Kết quả validation
        """
        errors = []
        
        # Required fields
        required_fields = ["filename", "file_type", "file_path", "file_size"]
        for field in required_fields:
            if field not in doc or not doc[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate file_type
        valid_types = ["pdf", "word", "image", "text"]
        if doc.get("file_type") not in valid_types:
            errors.append(f"Invalid file_type. Valid types: {valid_types}")
        
        # Validate file_size
        if doc.get("file_size", 0) <= 0:
            errors.append("file_size must be positive")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    @staticmethod
    def validate_embedding_document(doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate embedding document
        
        Args:
            doc (Dict): Document cần validate
            
        Returns:
            Dict[str, Any]: Kết quả validation
        """
        errors = []
        
        # Required fields
        required_fields = ["file_id", "content", "embedding", "type"]
        for field in required_fields:
            if field not in doc:
                errors.append(f"Missing required field: {field}")
        
        # Validate embedding
        embedding = doc.get("embedding", [])
        if not isinstance(embedding, list) or len(embedding) == 0:
            errors.append("embedding must be a non-empty list")
        
        # Validate embedding dimensions
        if isinstance(embedding, list):
            if not all(isinstance(x, (int, float)) for x in embedding):
                errors.append("embedding must contain only numbers")
            
            valid_dimensions = [1536, 3072]  # OpenAI embedding dimensions
            if len(embedding) not in valid_dimensions:
                errors.append(f"embedding dimensions must be one of: {valid_dimensions}")
        
        # Validate content
        if not doc.get("content") or not isinstance(doc.get("content"), str):
            errors.append("content must be a non-empty string")
        
        # Validate type
        valid_types = ["grammar", "vocabulary", "reading", "listening", "writing", "general"]
        if doc.get("type") not in valid_types:
            errors.append(f"Invalid type. Valid types: {valid_types}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

class DocumentUtils:
    """Utility functions cho documents"""
    
    @staticmethod
    def classify_content_type(content: str) -> str:
        """
        Tự động phân loại content type
        
        Args:
            content (str): Nội dung cần phân loại
            
        Returns:
            str: Loại content
        """
        content_lower = content.lower()
        
        # Keywords cho các loại content
        grammar_keywords = ["grammar", "ngữ pháp", "tense", "verb", "noun", "adjective", "adverb"]
        vocabulary_keywords = ["vocabulary", "từ vựng", "word", "meaning", "definition"]
        reading_keywords = ["reading", "đọc hiểu", "passage", "text", "story"]
        listening_keywords = ["listening", "nghe", "audio", "pronunciation"]
        writing_keywords = ["writing", "viết", "essay", "composition"]
        
        # Đếm keywords
        scores = {
            "grammar": sum(1 for kw in grammar_keywords if kw in content_lower),
            "vocabulary": sum(1 for kw in vocabulary_keywords if kw in content_lower),
            "reading": sum(1 for kw in reading_keywords if kw in content_lower),
            "listening": sum(1 for kw in listening_keywords if kw in content_lower),
            "writing": sum(1 for kw in writing_keywords if kw in content_lower)
        }
        
        # Trả về type có score cao nhất
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return "general"
    
    @staticmethod
    def extract_topic(content: str) -> Optional[str]:
        """
        Tự động extract topic từ content
        
        Args:
            content (str): Nội dung
            
        Returns:
            Optional[str]: Topic nếu tìm thấy
        """
        import re
        
        # Tìm patterns cho topics
        topic_patterns = [
            r"lesson\s+\d+[:\s]*([^.\n]+)",  # Lesson 1: Past Perfect
            r"unit\s+\d+[:\s]*([^.\n]+)",   # Unit 2: Vocabulary
            r"chapter\s+\d+[:\s]*([^.\n]+)", # Chapter 3: Grammar
            r"topic[:\s]*([^.\n]+)",         # Topic: Present Simple
            r"([A-Z][^.\n]{5,50})"          # Capitalized phrases
        ]
        
        content_lines = content.split('\n')[:5]  # Chỉ xem 5 dòng đầu
        
        for line in content_lines:
            for pattern in topic_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    topic = match.group(1).strip()
                    if len(topic) > 5 and len(topic) < 100:
                        return topic
        
        return None
    
    @staticmethod
    def estimate_difficulty_level(content: str) -> str:
        """
        Ước tính độ khó của content
        
        Args:
            content (str): Nội dung
            
        Returns:
            str: Mức độ khó (beginner, intermediate, advanced)
        """
        # Các indicator cho độ khó
        beginner_indicators = ["basic", "simple", "easy", "introduction", "begin"]
        intermediate_indicators = ["intermediate", "medium", "practice", "exercise"]
        advanced_indicators = ["advanced", "complex", "difficult", "expert"]
        
        content_lower = content.lower()
        words = content_lower.split()
        
        # Đếm syllables trung bình (rough estimate)
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        
        # Đếm indicators
        beginner_score = sum(1 for ind in beginner_indicators if ind in content_lower)
        intermediate_score = sum(1 for ind in intermediate_indicators if ind in content_lower)
        advanced_score = sum(1 for ind in advanced_indicators if ind in content_lower)
        
        # Logic phân loại
        if advanced_score > 0 or avg_word_length > 7:
            return "advanced"
        elif intermediate_score > 0 or avg_word_length > 5:
            return "intermediate"
        else:
            return "beginner"
    
    @staticmethod
    def generate_tags(content: str, content_type: str) -> List[str]:
        """
        Tự động generate tags cho content
        
        Args:
            content (str): Nội dung
            content_type (str): Loại content
            
        Returns:
            List[str]: Danh sách tags
        """
        tags = []
        content_lower = content.lower()
        
        # Tags chung
        if "english" in content_lower:
            tags.append("english")
        if "vietnamese" in content_lower or "tiếng việt" in content_lower:
            tags.append("vietnamese")
        
        # Tags theo content type
        if content_type == "grammar":
            grammar_tags = ["present simple", "past simple", "present perfect", "past perfect",
                          "future", "conditional", "passive voice", "modal verbs"]
            tags.extend([tag for tag in grammar_tags if tag in content_lower])
        
        elif content_type == "vocabulary":
            vocab_tags = ["nouns", "verbs", "adjectives", "adverbs", "phrasal verbs",
                         "idioms", "collocations"]
            tags.extend([tag for tag in vocab_tags if tag in content_lower])
        
        # Loại bỏ duplicates
        return list(set(tags))

# Example usage
if __name__ == "__main__":
    print("=== Document Model Demo ===")
    
    # Tạo file document
    file_doc = DocumentModel.create_file_document(
        filename="grammar_lesson.pdf",
        file_type="pdf",
        file_path="uploads/pdf/grammar_lesson.pdf",
        file_size=1024000,
        metadata={"subject": "English", "language": "vi"}
    )
    print(f"File document: {file_doc}")
    
    # Validate
    validation = DocumentValidator.validate_file_document(file_doc)
    print(f"Validation result: {validation}")
    
    # Test content classification
    test_content = "This lesson covers the Past Perfect tense in English grammar."
    content_type = DocumentUtils.classify_content_type(test_content)
    topic = DocumentUtils.extract_topic(test_content)
    difficulty = DocumentUtils.estimate_difficulty_level(test_content)
    tags = DocumentUtils.generate_tags(test_content, content_type)
    
    print(f"Content type: {content_type}")
    print(f"Topic: {topic}")
    print(f"Difficulty: {difficulty}")
    print(f"Tags: {tags}")
