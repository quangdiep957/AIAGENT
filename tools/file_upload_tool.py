"""
File Upload Tool - Xử lý upload file từ user
Hỗ trợ: PDF, Word, Image, Text files
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import hashlib
import mimetypes
from bson import ObjectId

class FileUploadTool:
    """Tool xử lý upload file và lưu metadata"""
    
    # Các loại file được hỗ trợ
    SUPPORTED_EXTENSIONS = {
        'pdf': ['.pdf'],
        'word': ['.doc', '.docx'],
        'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'],
        'text': ['.txt', '.md', '.rtf']
    }
    
    # Kích thước file tối đa (bytes)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    def __init__(self, upload_dir: str = "uploads"):
        """
        Khởi tạo FileUploadTool
        
        Args:
            upload_dir (str): Thư mục lưu trữ file upload
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        # Tạo các thư mục con theo loại file
        for file_type in self.SUPPORTED_EXTENSIONS.keys():
            (self.upload_dir / file_type).mkdir(exist_ok=True)
    
    def _get_file_type(self, file_path: str) -> Optional[str]:
        """
        Xác định loại file dựa trên extension
        
        Args:
            file_path (str): Đường dẫn file
            
        Returns:
            Optional[str]: Loại file hoặc None nếu không hỗ trợ
        """
        file_extension = Path(file_path).suffix.lower()
        
        for file_type, extensions in self.SUPPORTED_EXTENSIONS.items():
            if file_extension in extensions:
                return file_type
        
        return None
    
    def _generate_unique_filename(self, original_filename: str, file_type: str) -> str:
        """
        Tạo tên file unique để tránh trùng lặp
        
        Args:
            original_filename (str): Tên file gốc
            file_type (str): Loại file
            
        Returns:
            str: Tên file unique
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = Path(original_filename).stem
        extension = Path(original_filename).suffix
        
        # Tạo hash ngắn từ tên file gốc
        hash_short = hashlib.md5(original_filename.encode()).hexdigest()[:8]
        
        unique_filename = f"{name}_{timestamp}_{hash_short}{extension}"
        return unique_filename
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Tính hash MD5 của file để kiểm tra duplicate
        
        Args:
            file_path (str): Đường dẫn file
            
        Returns:
            str: MD5 hash của file
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate file trước khi upload
        
        Args:
            file_path (str): Đường dẫn file cần validate
            
        Returns:
            Dict[str, Any]: Kết quả validation
        """
        result = {
            "valid": False,
            "file_type": None,
            "file_size": 0,
            "errors": []
        }
        
        try:
            # Kiểm tra file có tồn tại không
            if not os.path.exists(file_path):
                result["errors"].append("File không tồn tại")
                return result
            
            # Kiểm tra kích thước file
            file_size = os.path.getsize(file_path)
            result["file_size"] = file_size
            
            if file_size > self.MAX_FILE_SIZE:
                result["errors"].append(f"File quá lớn. Kích thước tối đa: {self.MAX_FILE_SIZE / (1024*1024):.1f}MB")
                return result
            
            if file_size == 0:
                result["errors"].append("File rỗng")
                return result
            
            # Kiểm tra loại file
            file_type = self._get_file_type(file_path)
            if not file_type:
                supported_ext = [ext for exts in self.SUPPORTED_EXTENSIONS.values() for ext in exts]
                result["errors"].append(f"Loại file không được hỗ trợ. Các loại file hỗ trợ: {', '.join(supported_ext)}")
                return result
            
            result["file_type"] = file_type
            result["valid"] = True
            
        except Exception as e:
            result["errors"].append(f"Lỗi khi validate file: {str(e)}")
        
        return result
    
    def upload_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Upload file và tạo metadata
        
        Args:
            file_path (str): Đường dẫn file cần upload
            metadata (Optional[Dict]): Metadata bổ sung
            
        Returns:
            Dict[str, Any]: Thông tin file đã upload
        """
        try:
            # Validate file
            validation = self.validate_file(file_path)
            if not validation["valid"]:
                return {
                    "success": False,
                    "errors": validation["errors"]
                }
            
            # Thông tin file gốc
            original_filename = os.path.basename(file_path)
            file_type = validation["file_type"]
            file_size = validation["file_size"]
            
            # Tạo tên file unique
            unique_filename = self._generate_unique_filename(original_filename, file_type)
            
            # Đường dẫn lưu file
            target_dir = self.upload_dir / file_type
            target_path = target_dir / unique_filename
            
            # Copy file đến thư mục upload
            shutil.copy2(file_path, target_path)
            
            # Tính hash của file
            file_hash = self._calculate_file_hash(str(target_path))
            
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(str(target_path))
            
            # Tạo document metadata cho MongoDB
            file_document = {
                "_id": ObjectId(),
                "filename": original_filename,
                "unique_filename": unique_filename,
                "file_type": file_type,
                "mime_type": mime_type,
                "file_path": str(target_path.relative_to(self.upload_dir)),
                "absolute_path": str(target_path),
                "file_size": file_size,
                "file_hash": file_hash,
                "upload_date": datetime.utcnow(),
                "processed": False,
                "metadata": metadata or {},
                "status": "uploaded"
            }
            
            return {
                "success": True,
                "file_id": str(file_document["_id"]),
                "document": file_document,
                "message": f"File '{original_filename}' đã được upload thành công"
            }
            
        except Exception as e:
            return {
                "success": False,
                "errors": [f"Lỗi khi upload file: {str(e)}"]
            }
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết của file
        
        Args:
            file_path (str): Đường dẫn file
            
        Returns:
            Dict[str, Any]: Thông tin file
        """
        try:
            if not os.path.exists(file_path):
                return {"error": "File không tồn tại"}
            
            stat = os.stat(file_path)
            mime_type, encoding = mimetypes.guess_type(file_path)
            
            return {
                "filename": os.path.basename(file_path),
                "file_size": stat.st_size,
                "file_type": self._get_file_type(file_path),
                "mime_type": mime_type,
                "encoding": encoding,
                "created_time": datetime.fromtimestamp(stat.st_ctime),
                "modified_time": datetime.fromtimestamp(stat.st_mtime),
                "file_hash": self._calculate_file_hash(file_path)
            }
            
        except Exception as e:
            return {"error": f"Lỗi khi lấy thông tin file: {str(e)}"}
    
    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """
        Xóa file đã upload
        
        Args:
            file_path (str): Đường dẫn file cần xóa
            
        Returns:
            Dict[str, Any]: Kết quả xóa file
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return {
                    "success": True,
                    "message": "File đã được xóa thành công"
                }
            else:
                return {
                    "success": False,
                    "error": "File không tồn tại"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi xóa file: {str(e)}"
            }

# Example usage
if __name__ == "__main__":
    # Demo usage
    uploader = FileUploadTool()
    
    # Test file info
    print("=== File Upload Tool Demo ===")
    
    # Tạo file test
    test_file = "test_document.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Đây là nội dung test cho file upload tool.")
    
    # Get file info
    info = uploader.get_file_info(test_file)
    print(f"File info: {info}")
    
    # Upload file
    result = uploader.upload_file(test_file, {
        "subject": "Test",
        "topic": "File Upload Demo",
        "language": "vi"
    })
    
    print(f"Upload result: {result}")
    
    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
