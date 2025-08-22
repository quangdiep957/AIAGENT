"""
Embedding Tool - Tạo vector embeddings từ text sử dụng OpenAI API
Hỗ trợ chunking text và batch processing
"""

import os
import re
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import hashlib
import tiktoken
from openai import OpenAI
from config import OPENAI_API_KEY

class EmbeddingTool:
    """Tool tạo vector embeddings từ text"""
    
    # Các model embedding của OpenAI
    EMBEDDING_MODELS = {
        "text-embedding-3-small": {
            "dimensions": 1536,
            "max_tokens": 8192,
            "cost_per_1k": 0.00002  # USD
        },
        "text-embedding-3-large": {
            "dimensions": 3072,
            "max_tokens": 8192,
            "cost_per_1k": 0.00013  # USD
        },
        "text-embedding-ada-002": {
            "dimensions": 1536,
            "max_tokens": 8192,
            "cost_per_1k": 0.0001  # USD
        }
    }
    
    def __init__(self, model: str = "text-embedding-3-small", api_key: Optional[str] = None):
        """
        Khởi tạo EmbeddingTool
        
        Args:
            model (str): Tên model embedding
            api_key (Optional[str]): OpenAI API key
        """
        self.model = model
        self.api_key = api_key or OPENAI_API_KEY
        
        if not self.api_key:
            raise ValueError("OpenAI API key không được cung cấp")
        
        # Khởi tạo OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        
        # Khởi tạo tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            print(f"Không thể khởi tạo tokenizer: {e}")
            self.tokenizer = None
        
        # Validate model
        if model not in self.EMBEDDING_MODELS:
            raise ValueError(f"Model '{model}' không được hỗ trợ. Các model hỗ trợ: {list(self.EMBEDDING_MODELS.keys())}")
        
        self.model_info = self.EMBEDDING_MODELS[model]
        
        # Thống kê usage
        self.usage_stats = {
            "total_tokens": 0,
            "total_requests": 0,
            "total_cost": 0.0
        }
    
    def _count_tokens(self, text: str) -> int:
        """
        Đếm số tokens trong text
        
        Args:
            text (str): Text cần đếm
            
        Returns:
            int: Số tokens
        """
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except:
                pass
        
        # Fallback: ước tính dựa trên số từ
        return len(text.split()) * 1.3  # Rough estimate
    
    def _clean_text(self, text: str) -> str:
        """
        Làm sạch text trước khi embedding
        
        Args:
            text (str): Text cần làm sạch
            
        Returns:
            str: Text đã được làm sạch
        """
        if not text:
            return ""
        
        # Loại bỏ ký tự điều khiển
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)
        
        # Chuẩn hóa khoảng trắng
        text = re.sub(r'\s+', ' ', text)
        
        # Loại bỏ khoảng trắng đầu/cuối
        text = text.strip()
        
        return text
    
    def _split_text_by_tokens(self, text: str, max_tokens: int = None, overlap_tokens: int = 50) -> List[str]:
        """
        Chia text thành chunks dựa trên số tokens
        
        Args:
            text (str): Text cần chia
            max_tokens (int): Số tokens tối đa mỗi chunk
            overlap_tokens (int): Số tokens overlap giữa các chunk
            
        Returns:
            List[str]: Danh sách chunks
        """
        if max_tokens is None:
            max_tokens = self.model_info["max_tokens"] - 100  # Để lại buffer
        
        if not self.tokenizer:
            # Fallback: chia theo số ký tự
            return self._split_text_by_chars(text, max_tokens * 4, overlap_tokens * 4)
        
        try:
            tokens = self.tokenizer.encode(text)
            
            if len(tokens) <= max_tokens:
                return [text]
            
            chunks = []
            start = 0
            
            while start < len(tokens):
                end = start + max_tokens
                chunk_tokens = tokens[start:end]
                
                # Decode về text
                chunk_text = self.tokenizer.decode(chunk_tokens)
                chunks.append(chunk_text)
                
                # Di chuyển start với overlap
                start = end - overlap_tokens
            
            return chunks
            
        except Exception as e:
            print(f"Lỗi khi chia text theo tokens: {e}")
            # Fallback
            return self._split_text_by_chars(text, max_tokens * 4, overlap_tokens * 4)
    
    def _split_text_by_chars(self, text: str, max_chars: int = 3000, overlap_chars: int = 200) -> List[str]:
        """
        Chia text thành chunks dựa trên số ký tự
        
        Args:
            text (str): Text cần chia
            max_chars (int): Số ký tự tối đa mỗi chunk
            overlap_chars (int): Số ký tự overlap
            
        Returns:
            List[str]: Danh sách chunks
        """
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_chars
            
            # Nếu không phải chunk cuối, tìm điểm cắt hợp lý
            if end < len(text):
                # Tìm dấu câu gần nhất
                for i in range(end, max(start + max_chars - overlap_chars, end - 200), -1):
                    if text[i] in '.!?;:\n':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap_chars if end < len(text) else end
        
        return chunks
    
    def create_embedding(self, text: str, normalize: bool = True) -> Dict[str, Any]:
        """
        Tạo embedding cho một đoạn text
        
        Args:
            text (str): Text cần tạo embedding
            normalize (bool): Có normalize vector không
            
        Returns:
            Dict[str, Any]: Kết quả embedding
        """
        try:
            # Làm sạch text
            clean_text = self._clean_text(text)
            if not clean_text:
                return {
                    "success": False,
                    "error": "Text rỗng sau khi làm sạch"
                }
            
            # Đếm tokens
            token_count = self._count_tokens(clean_text)
            
            # Kiểm tra giới hạn tokens
            if token_count > self.model_info["max_tokens"]:
                return {
                    "success": False,
                    "error": f"Text quá dài ({token_count} tokens). Giới hạn: {self.model_info['max_tokens']} tokens"
                }
            
            # Gọi OpenAI API
            response = self.client.embeddings.create(
                input=clean_text,
                model=self.model
            )
            
            # Lấy embedding vector
            embedding = response.data[0].embedding
            
            # Normalize vector nếu cần
            if normalize:
                import math
                magnitude = math.sqrt(sum(x**2 for x in embedding))
                if magnitude > 0:
                    embedding = [x / magnitude for x in embedding]
            
            # Cập nhật usage stats
            self.usage_stats["total_tokens"] += token_count
            self.usage_stats["total_requests"] += 1
            self.usage_stats["total_cost"] += (token_count / 1000) * self.model_info["cost_per_1k"]
            
            return {
                "success": True,
                "embedding": embedding,
                "dimensions": len(embedding),
                "token_count": token_count,
                "model": self.model,
                "text_length": len(clean_text),
                "created_at": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi tạo embedding: {str(e)}"
            }
    
    def create_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> Dict[str, Any]:
        """
        Tạo embeddings cho nhiều text cùng lúc
        
        Args:
            texts (List[str]): Danh sách texts
            batch_size (int): Số text xử lý mỗi batch
            
        Returns:
            Dict[str, Any]: Kết quả embeddings
        """
        try:
            if not texts:
                return {
                    "success": False,
                    "error": "Danh sách texts rỗng"
                }
            
            all_embeddings = []
            total_tokens = 0
            failed_indices = []
            
            # Xử lý từng batch
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Làm sạch texts
                clean_texts = [self._clean_text(text) for text in batch_texts]
                
                # Lọc text rỗng
                valid_texts = [(idx, text) for idx, text in enumerate(clean_texts) if text]
                
                if not valid_texts:
                    failed_indices.extend(range(i, i + len(batch_texts)))
                    continue
                
                try:
                    # Gọi API cho batch
                    response = self.client.embeddings.create(
                        input=[text for _, text in valid_texts],
                        model=self.model
                    )
                    
                    # Lưu kết quả
                    for j, (original_idx, text) in enumerate(valid_texts):
                        embedding = response.data[j].embedding
                        token_count = self._count_tokens(text)
                        total_tokens += token_count
                        
                        all_embeddings.append({
                            "index": i + original_idx,
                            "embedding": embedding,
                            "token_count": token_count,
                            "text_length": len(text)
                        })
                    
                    # Rate limiting
                    time.sleep(0.1)  # Tránh hit rate limit
                    
                except Exception as batch_error:
                    print(f"Lỗi batch {i}-{i+batch_size}: {batch_error}")
                    failed_indices.extend(range(i, i + len(batch_texts)))
            
            # Cập nhật usage stats
            self.usage_stats["total_tokens"] += total_tokens
            self.usage_stats["total_requests"] += len(texts) - len(failed_indices)
            self.usage_stats["total_cost"] += (total_tokens / 1000) * self.model_info["cost_per_1k"]
            
            return {
                "success": len(all_embeddings) > 0,
                "embeddings": all_embeddings,
                "total_processed": len(all_embeddings),
                "total_failed": len(failed_indices),
                "failed_indices": failed_indices,
                "total_tokens": total_tokens,
                "model": self.model,
                "created_at": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi tạo batch embeddings: {str(e)}"
            }
    
    def chunk_and_embed(self, text: str, chunk_size_tokens: int = None, overlap_tokens: int = 50) -> Dict[str, Any]:
        """
        Chia text thành chunks và tạo embedding cho từng chunk
        
        Args:
            text (str): Text cần xử lý
            chunk_size_tokens (int): Kích thước chunk (tokens)
            overlap_tokens (int): Overlap giữa chunks
            
        Returns:
            Dict[str, Any]: Kết quả chunks và embeddings
        """
        try:
            # Làm sạch text
            clean_text = self._clean_text(text)
            if not clean_text:
                return {
                    "success": False,
                    "error": "Text rỗng sau khi làm sạch"
                }
            
            # Chia thành chunks
            if chunk_size_tokens is None:
                chunk_size_tokens = self.model_info["max_tokens"] - 100
            
            chunks = self._split_text_by_tokens(clean_text, chunk_size_tokens, overlap_tokens)
            
            if not chunks:
                return {
                    "success": False,
                    "error": "Không thể chia text thành chunks"
                }
            
            # Tạo embeddings cho từng chunk
            chunk_embeddings = []
            total_tokens = 0
            
            for i, chunk in enumerate(chunks):
                result = self.create_embedding(chunk)
                
                if result["success"]:
                    chunk_embeddings.append({
                        "chunk_index": i,
                        "content": chunk,
                        "embedding": result["embedding"],
                        "token_count": result["token_count"],
                        "text_length": len(chunk),
                        "start_position": clean_text.find(chunk[:50]),  # Ước tính vị trí
                    })
                    total_tokens += result["token_count"]
                else:
                    print(f"Lỗi embedding chunk {i}: {result['error']}")
            
            return {
                "success": len(chunk_embeddings) > 0,
                "original_text": clean_text,
                "total_chunks": len(chunks),
                "successful_chunks": len(chunk_embeddings),
                "chunks": chunk_embeddings,
                "total_tokens": total_tokens,
                "model": self.model,
                "chunk_size_tokens": chunk_size_tokens,
                "overlap_tokens": overlap_tokens,
                "created_at": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi chunk và embed: {str(e)}"
            }
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Tính cosine similarity giữa 2 embeddings
        
        Args:
            embedding1 (List[float]): Vector embedding 1
            embedding2 (List[float]): Vector embedding 2
            
        Returns:
            float: Cosine similarity (0-1)
        """
        try:
            import math
            
            # Tính dot product
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            
            # Tính magnitude
            mag1 = math.sqrt(sum(a * a for a in embedding1))
            mag2 = math.sqrt(sum(b * b for b in embedding2))
            
            if mag1 == 0 or mag2 == 0:
                return 0.0
            
            # Cosine similarity
            similarity = dot_product / (mag1 * mag2)
            
            # Đảm bảo kết quả trong khoảng [0, 1]
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            print(f"Lỗi khi tính similarity: {e}")
            return 0.0
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê sử dụng
        
        Returns:
            Dict[str, Any]: Thống kê usage
        """
        return {
            **self.usage_stats,
            "model": self.model,
            "cost_per_1k_tokens": self.model_info["cost_per_1k"],
            "max_tokens_per_request": self.model_info["max_tokens"],
            "embedding_dimensions": self.model_info["dimensions"]
        }
    
    def create_text_hash(self, text: str) -> str:
        """
        Tạo hash để identify text unique
        
        Args:
            text (str): Text cần hash
            
        Returns:
            str: MD5 hash
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()

# Example usage
if __name__ == "__main__":
    # Demo usage (cần OpenAI API key)
    try:
        embedding_tool = EmbeddingTool()
        
        print("=== Embedding Tool Demo ===")
        
        # Test text
        test_text = """
        Đây là một đoạn văn bản test để demo Embedding Tool.
        Tool này có thể tạo vector embeddings từ text sử dụng OpenAI API.
        Nó hỗ trợ chia text thành chunks và xử lý batch.
        """
        
        # Tạo embedding đơn
        result = embedding_tool.create_embedding(test_text)
        if result["success"]:
            print(f"✅ Embedding thành công:")
            print(f"   Dimensions: {result['dimensions']}")
            print(f"   Tokens: {result['token_count']}")
            print(f"   Text length: {result['text_length']}")
        else:
            print(f"❌ Lỗi: {result['error']}")
        
        # Test chunk và embed
        long_text = test_text * 10  # Tạo text dài
        chunk_result = embedding_tool.chunk_and_embed(long_text, chunk_size_tokens=100)
        
        if chunk_result["success"]:
            print(f"\n✅ Chunk và embed thành công:")
            print(f"   Total chunks: {chunk_result['total_chunks']}")
            print(f"   Successful chunks: {chunk_result['successful_chunks']}")
            print(f"   Total tokens: {chunk_result['total_tokens']}")
        
        # Usage stats
        stats = embedding_tool.get_usage_stats()
        print(f"\n📊 Usage Stats:")
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Total tokens: {stats['total_tokens']}")
        print(f"   Estimated cost: ${stats['total_cost']:.6f}")
        
    except Exception as e:
        print(f"Demo không thể chạy: {e}")
        print("Cần cài đặt OpenAI API key và các dependencies")
