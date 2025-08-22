"""
OCR Tool - Optical Character Recognition
Đọc chữ từ ảnh và PDF scan sử dụng Tesseract OCR và EasyOCR
"""

import os
import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import base64
import io

# Import các thư viện OCR
try:
    import pytesseract
    import tesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

class OCRTool:
    """Tool OCR để đọc text từ ảnh và PDF scan"""
    
    def __init__(self, ocr_engine: str = "auto"):
        """
        Khởi tạo OCRTool
        
        Args:
            ocr_engine (str): OCR engine sử dụng ("tesseract", "easyocr", "auto")
        """
        self.ocr_engine = ocr_engine
        self.easyocr_reader = None
        
        # Khởi tạo EasyOCR reader nếu có
        if EASYOCR_AVAILABLE and ocr_engine in ["easyocr", "auto"]:
            try:
                # Hỗ trợ tiếng Việt và tiếng Anh
                self.easyocr_reader = easyocr.Reader(['vi', 'en'], gpu=False)
            except Exception as e:
                print(f"Không thể khởi tạo EasyOCR: {e}")
        
        # Cấu hình Tesseract
        if TESSERACT_AVAILABLE:
            # Đường dẫn Tesseract (có thể cần điều chỉnh theo hệ thống)
            # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            pass
    
    def _preprocess_image(self, image_path: str, enhance: bool = True) -> np.ndarray:
        """
        Tiền xử lý ảnh để cải thiện độ chính xác OCR
        
        Args:
            image_path (str): Đường dẫn ảnh
            enhance (bool): Có enhance ảnh không
            
        Returns:
            np.ndarray: Ảnh đã được xử lý
        """
        try:
            # Đọc ảnh bằng OpenCV
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Không thể đọc ảnh")
            
            if enhance:
                # Chuyển sang grayscale
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                
                # Khử noise bằng Gaussian blur
                denoised = cv2.GaussianBlur(gray, (5, 5), 0)
                
                # Tăng contrast bằng CLAHE
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(denoised)
                
                # Threshold để tạo ảnh binary
                _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                return binary
            else:
                return image
                
        except Exception as e:
            print(f"Lỗi khi xử lý ảnh: {e}")
            # Fallback: đọc ảnh gốc
            return cv2.imread(image_path)
    
    def _preprocess_image_pil(self, image_path: str) -> Image.Image:
        """
        Tiền xử lý ảnh bằng PIL
        
        Args:
            image_path (str): Đường dẫn ảnh
            
        Returns:
            Image.Image: Ảnh đã được xử lý
        """
        try:
            image = Image.open(image_path)
            
            # Convert sang grayscale nếu cần
            if image.mode != 'L':
                image = image.convert('L')
            
            # Tăng contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Tăng độ sắc nét
            image = image.filter(ImageFilter.SHARPEN)
            
            return image
            
        except Exception as e:
            print(f"Lỗi khi xử lý ảnh PIL: {e}")
            return Image.open(image_path)
    
    def _ocr_with_tesseract(self, image_path: str, languages: str = "vie+eng") -> Dict[str, Any]:
        """
        OCR sử dụng Tesseract
        
        Args:
            image_path (str): Đường dẫn ảnh
            languages (str): Ngôn ngữ OCR
            
        Returns:
            Dict[str, Any]: Kết quả OCR
        """
        try:
            if not TESSERACT_AVAILABLE:
                return {
                    "success": False,
                    "error": "Tesseract chưa được cài đặt"
                }
            
            # Tiền xử lý ảnh
            if PIL_AVAILABLE:
                processed_image = self._preprocess_image_pil(image_path)
            else:
                processed_image = image_path
            
            # Cấu hình Tesseract
            config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼỀỀỂưăạảấầẩẫậắằẳẵặẹẻẽềềểỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪễệỉịọỏốồổỗộớờởỡợụủứừỬỮỰỲỴÝỶỸửữựỳỵýỷỹ0123456789.,!?:;()[]{}\"\\'-+*/=@#$%^&_|~`<> \\n\\t'
            
            # Lấy text
            text = pytesseract.image_to_string(processed_image, lang=languages, config=config)
            
            # Lấy thông tin chi tiết (bounding boxes)
            data = pytesseract.image_to_data(processed_image, lang=languages, output_type=pytesseract.Output.DICT)
            
            # Tạo danh sách từ với vị trí
            words = []
            confidences = []
            
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:  # Chỉ lấy từ có confidence > 0
                    words.append({
                        "text": data['text'][i],
                        "confidence": int(data['conf'][i]),
                        "bbox": {
                            "x": int(data['left'][i]),
                            "y": int(data['top'][i]),
                            "width": int(data['width'][i]),
                            "height": int(data['height'][i])
                        }
                    })
                    confidences.append(int(data['conf'][i]))
            
            # Tính confidence trung bình
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "success": True,
                "engine": "tesseract",
                "text": text.strip(),
                "words": words,
                "word_count": len([w for w in words if w['text'].strip()]),
                "average_confidence": avg_confidence,
                "languages": languages
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi Tesseract OCR: {str(e)}",
                "engine": "tesseract"
            }
    
    def _ocr_with_easyocr(self, image_path: str) -> Dict[str, Any]:
        """
        OCR sử dụng EasyOCR
        
        Args:
            image_path (str): Đường dẫn ảnh
            
        Returns:
            Dict[str, Any]: Kết quả OCR
        """
        try:
            if not EASYOCR_AVAILABLE or self.easyocr_reader is None:
                return {
                    "success": False,
                    "error": "EasyOCR chưa được cài đặt hoặc khởi tạo"
                }
            
            # Tiền xử lý ảnh
            processed_image = self._preprocess_image(image_path)
            
            # OCR với EasyOCR
            results = self.easyocr_reader.readtext(processed_image)
            
            # Chuyển đổi kết quả
            text_parts = []
            words = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                if confidence > 0.1:  # Lọc kết quả có confidence thấp
                    text_parts.append(text)
                    words.append({
                        "text": text,
                        "confidence": float(confidence * 100),  # Convert to percentage
                        "bbox": {
                            "points": bbox  # EasyOCR trả về 4 điểm góc
                        }
                    })
                    confidences.append(confidence * 100)
            
            # Kết hợp text
            full_text = " ".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "success": True,
                "engine": "easyocr",
                "text": full_text,
                "words": words,
                "word_count": len(words),
                "average_confidence": avg_confidence,
                "languages": ["vi", "en"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi EasyOCR: {str(e)}",
                "engine": "easyocr"
            }
    
    def extract_text_from_image(self, image_path: str, engine: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text từ ảnh
        
        Args:
            image_path (str): Đường dẫn ảnh
            engine (Optional[str]): OCR engine cụ thể
            
        Returns:
            Dict[str, Any]: Kết quả OCR
        """
        try:
            # Kiểm tra file có tồn tại
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": "File ảnh không tồn tại"
                }
            
            # Xác định engine sử dụng
            use_engine = engine or self.ocr_engine
            
            if use_engine == "auto":
                # Thử EasyOCR trước, fallback sang Tesseract
                if EASYOCR_AVAILABLE and self.easyocr_reader:
                    result = self._ocr_with_easyocr(image_path)
                    if result["success"]:
                        return result
                
                if TESSERACT_AVAILABLE:
                    return self._ocr_with_tesseract(image_path)
                else:
                    return {
                        "success": False,
                        "error": "Không có OCR engine nào khả dụng"
                    }
            
            elif use_engine == "easyocr":
                return self._ocr_with_easyocr(image_path)
            
            elif use_engine == "tesseract":
                return self._ocr_with_tesseract(image_path)
            
            else:
                return {
                    "success": False,
                    "error": f"OCR engine '{use_engine}' không được hỗ trợ"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi extract text: {str(e)}"
            }
    
    def process_pdf_scan(self, pdf_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Xử lý PDF scan (convert thành ảnh và OCR)
        
        Args:
            pdf_path (str): Đường dẫn file PDF
            output_dir (Optional[str]): Thư mục lưu ảnh tạm
            
        Returns:
            Dict[str, Any]: Kết quả OCR tất cả trang
        """
        try:
            if not PDF2IMAGE_AVAILABLE:
                return {
                    "success": False,
                    "error": "pdf2image chưa được cài đặt"
                }
            
            if not os.path.exists(pdf_path):
                return {
                    "success": False,
                    "error": "File PDF không tồn tại"
                }
            
            # Tạo thư mục tạm nếu cần
            if output_dir is None:
                output_dir = "temp_images"
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Convert PDF thành ảnh
            pages = pdf2image.convert_from_path(pdf_path)
            
            all_results = []
            total_text = ""
            
            for page_num, page in enumerate(pages, 1):
                # Lưu page thành ảnh tạm
                temp_image_path = os.path.join(output_dir, f"page_{page_num}.png")
                page.save(temp_image_path, 'PNG')
                
                # OCR cho page này
                page_result = self.extract_text_from_image(temp_image_path)
                
                if page_result["success"]:
                    page_result["page_number"] = page_num
                    all_results.append(page_result)
                    total_text += page_result.get("text", "") + "\n"
                
                # Xóa ảnh tạm
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
            
            # Xóa thư mục tạm nếu rỗng
            try:
                os.rmdir(output_dir)
            except:
                pass
            
            # Tính toán thống kê
            total_words = sum(result.get("word_count", 0) for result in all_results)
            avg_confidence = sum(result.get("average_confidence", 0) for result in all_results) / len(all_results) if all_results else 0
            
            return {
                "success": True,
                "file_type": "pdf_scan",
                "total_pages": len(pages),
                "processed_pages": len(all_results),
                "pages": all_results,
                "total_text": total_text.strip(),
                "total_word_count": total_words,
                "average_confidence": avg_confidence,
                "processing_date": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi xử lý PDF scan: {str(e)}"
            }
    
    def batch_ocr(self, image_paths: List[str]) -> Dict[str, Any]:
        """
        Xử lý OCR nhiều ảnh cùng lúc
        
        Args:
            image_paths (List[str]): Danh sách đường dẫn ảnh
            
        Returns:
            Dict[str, Any]: Kết quả OCR tất cả ảnh
        """
        try:
            results = []
            total_text = ""
            
            for i, image_path in enumerate(image_paths):
                print(f"Processing image {i+1}/{len(image_paths)}: {os.path.basename(image_path)}")
                
                result = self.extract_text_from_image(image_path)
                result["image_index"] = i
                result["image_name"] = os.path.basename(image_path)
                
                results.append(result)
                
                if result["success"]:
                    total_text += result.get("text", "") + "\n"
            
            # Thống kê
            successful = [r for r in results if r["success"]]
            total_words = sum(r.get("word_count", 0) for r in successful)
            avg_confidence = sum(r.get("average_confidence", 0) for r in successful) / len(successful) if successful else 0
            
            return {
                "success": len(successful) > 0,
                "total_images": len(image_paths),
                "successful_images": len(successful),
                "results": results,
                "combined_text": total_text.strip(),
                "total_word_count": total_words,
                "average_confidence": avg_confidence,
                "processing_date": datetime.utcnow()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi khi xử lý batch OCR: {str(e)}"
            }
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """
        Lấy danh sách format được hỗ trợ
        
        Returns:
            Dict[str, List[str]]: Danh sách format
        """
        return {
            "image_formats": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"],
            "pdf_scan": [".pdf"] if PDF2IMAGE_AVAILABLE else [],
            "available_engines": {
                "tesseract": TESSERACT_AVAILABLE,
                "easyocr": EASYOCR_AVAILABLE and self.easyocr_reader is not None
            }
        }

# Example usage
if __name__ == "__main__":
    # Demo usage
    ocr = OCRTool()
    
    print("=== OCR Tool Demo ===")
    print(f"Supported formats: {ocr.get_supported_formats()}")
    
    # Tạo ảnh test đơn giản (nếu có PIL)
    if PIL_AVAILABLE:
        from PIL import Image, ImageDraw, ImageFont
        
        # Tạo ảnh test
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            # Thử dùng font hệ thống
            font = ImageFont.load_default()
        except:
            font = None
        
        draw.text((50, 50), "Hello World!", fill='black', font=font)
        draw.text((50, 100), "Xin chào Việt Nam!", fill='black', font=font)
        
        test_image = "test_ocr_image.png"
        img.save(test_image)
        
        # Test OCR
        result = ocr.extract_text_from_image(test_image)
        print(f"OCR result: {result}")
        
        # Cleanup
        if os.path.exists(test_image):
            os.remove(test_image)
    else:
        print("PIL không khả dụng, không thể tạo ảnh test")
