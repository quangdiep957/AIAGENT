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
                print(f"✅ EasyOCR reader đã được khởi tạo thành công")
            except Exception as e:
                print(f"❌ Không thể khởi tạo EasyOCR: {e}")
                self.easyocr_reader = None
        
        # Kiểm tra Tesseract
        self.tesseract_available = False
        if TESSERACT_AVAILABLE:
            try:
                # Kiểm tra đơn giản bằng cách test version
                version = pytesseract.get_tesseract_version()
                self.tesseract_available = True
                print(f"✅ Tesseract version {version} đã được phát hiện")
            except Exception as e:
                print(f"❌ Tesseract không khả dụng: {e}")
                # Thử test khác
                try:
                    # Test với string đơn giản
                    from PIL import Image
                    import io
                    
                    # Tạo ảnh test trong memory
                    test_img = Image.new('RGB', (100, 30), color='white')
                    from PIL import ImageDraw
                    draw = ImageDraw.Draw(test_img)
                    draw.text((10, 10), "test", fill='black')
                    
                    # Convert to bytes
                    img_byte_arr = io.BytesIO()
                    test_img.save(img_byte_arr, format='PNG')
                    img_byte_arr.seek(0)
                    
                    # Test OCR
                    result = pytesseract.image_to_string(Image.open(img_byte_arr))
                    self.tesseract_available = True
                    print(f"✅ Tesseract hoạt động với memory test")
                except Exception as test_error:
                    print(f"❌ Tesseract test cuối cũng thất bại: {test_error}")
                    self.tesseract_available = False
        
        # Debug availability
        print(f"🔍 OCR Engine Status:")
        print(f"  - TESSERACT_AVAILABLE: {TESSERACT_AVAILABLE}")
        print(f"  - Tesseract working: {self.tesseract_available}")
        print(f"  - EASYOCR_AVAILABLE: {EASYOCR_AVAILABLE}")
        print(f"  - EasyOCR Reader: {self.easyocr_reader is not None}")
        print(f"  - Selected engine: {ocr_engine}")
        
        # Cấu hình Tesseract
        if TESSERACT_AVAILABLE:
            # Đường dẫn Tesseract (có thể cần điều chỉnh theo hệ thống)
            # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            pass
    
    def _preprocess_image(self, image_path: str, enhance: bool = True, max_size: int = 2048, for_vietnamese: bool = True) -> np.ndarray:
        """
        Tiền xử lý ảnh để cải thiện độ chính xác OCR
        
        Args:
            image_path (str): Đường dẫn ảnh
            enhance (bool): Có enhance ảnh không
            max_size (int): Kích thước tối đa cho cạnh dài nhất
            for_vietnamese (bool): Có tối ưu cho tiếng Việt không
            
        Returns:
            np.ndarray: Ảnh đã được xử lý
        """
        try:
            # Đọc ảnh bằng OpenCV
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Không thể đọc ảnh")
            
            # Resize ảnh nếu quá lớn để tránh lỗi memory
            height, width = image.shape[:2]
            if max(height, width) > max_size:
                scale = max_size / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
                print(f"🔧 Resized image from {width}x{height} to {new_width}x{new_height}")
            
            if enhance:
                # Chuyển sang grayscale
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                
                if for_vietnamese:
                    # Preprocessing đặc biệt cho tiếng Việt
                    print("🔧 Applying Vietnamese text preprocessing...")
                    
                    # Tăng kích thước nếu ảnh quá nhỏ
                    if min(gray.shape) < 600:
                        scale_factor = 600 / min(gray.shape)
                        new_w = int(gray.shape[1] * scale_factor)
                        new_h = int(gray.shape[0] * scale_factor)
                        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
                        print(f"🔧 Upscaled for better text recognition: {new_w}x{new_h}")
                    
                    # Tăng contrast mạnh hơn
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    enhanced = clahe.apply(gray)
                    
                    # Khử noise với median filter (tốt hơn cho text)
                    denoised = cv2.medianBlur(enhanced, 3)
                    
                    # Sharpen filter để làm rõ text
                    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                    sharpened = cv2.filter2D(denoised, -1, kernel)
                    
                    # Adaptive threshold tốt hơn cho text
                    processed = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                else:
                    # Preprocessing thông thường
                    # Khử noise bằng Gaussian blur
                    denoised = cv2.GaussianBlur(gray, (5, 5), 0)
                    
                    # Tăng contrast bằng CLAHE
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    enhanced = clahe.apply(denoised)
                    
                    # Threshold để tạo ảnh binary
                    _, processed = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                return processed
            else:
                return image
                
        except Exception as e:
            print(f"Lỗi khi xử lý ảnh: {e}")
            # Fallback: đọc ảnh gốc
            return cv2.imread(image_path)
    
    def _preprocess_image_pil(self, image_path: str) -> Any:
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
        OCR sử dụng Tesseract với cấu hình tối ưu cho tiếng Việt
        
        Args:
            image_path (str): Đường dẫn ảnh
            languages (str): Ngôn ngữ OCR
            
        Returns:
            Dict[str, Any]: Kết quả OCR
        """
        try:
            if not TESSERACT_AVAILABLE or not self.tesseract_available:
                return {
                    "success": False,
                    "error": "Tesseract chưa được cài đặt hoặc không hoạt động"
                }
            
            print("🚀 Trying Tesseract with Vietnamese optimization...")
            
            # Tiền xử lý ảnh với tối ưu cho tiếng Việt
            processed_image = self._preprocess_image(image_path, enhance=True, for_vietnamese=True)
            
            # Thử nhiều cấu hình PSM khác nhau cho tiếng Việt
            configs = [
                '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂĐĨŨƠăđĩũơƯĂẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼỀỀỂưăạảấầẩẫậắằẳẵặẹẻẽềềểỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪễệỉịọỏốồổỗộớờởỡợụủứừỬỮỰỲỴÝỶỸửữựỳỵỷỹ0123456789 .,;:!?()[]{}\"\'+-*/=<>%$&@#',
                '--oem 3 --psm 4',  # Single column of text
                '--oem 3 --psm 6',  # Single uniform block of text
                '--oem 3 --psm 8',  # Single word
                '--oem 3 --psm 3'   # Fully automatic page segmentation
            ]
            
            best_result = None
            best_confidence = 0
            
            for config in configs:
                try:
                    print(f"🔧 Trying config: {config}")
                    
                    # Lấy text với confidence
                    data = pytesseract.image_to_data(processed_image, lang=languages, config=config, output_type=pytesseract.Output.DICT)
                    
                    # Tính confidence trung bình
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    # Lấy text
                    text = pytesseract.image_to_string(processed_image, lang=languages, config=config)
                    text = text.strip()
                    
                    print(f"   📊 Text length: {len(text)}, Confidence: {avg_confidence:.1f}%")
                    
                    if len(text) > 10 and avg_confidence > best_confidence:
                        best_result = {
                            'text': text,
                            'confidence': avg_confidence,
                            'config': config
                        }
                        best_confidence = avg_confidence
                        
                except Exception as e:
                    print(f"   ❌ Config failed: {e}")
                    continue
            
            if best_result is None:
                return {
                    "success": False,
                    "error": "Không thể trích xuất text với bất kỳ cấu hình nào"
                }
            
            text = best_result['text']
            
            print(f"🎯 Best result: {len(text)} chars, confidence: {best_result['confidence']:.1f}%")
            print(f"📝 Sample: {text[:200]}...")
            
            # Tính word count
            words = text.split()
            word_count = len(words)
            
            return {
                "success": True,
                "text": text,
                "word_count": word_count,
                "average_confidence": best_result['confidence'],
                "engine": "tesseract",
                "language": languages,
                "config_used": best_result['config']
            }
            
            # Nếu không có kết quả, thử với PSM khác
            if not text.strip():
                print("🔄 Trying with different PSM settings...")
                config = '--oem 3 --psm 3'  # PSM 3: fully automatic page segmentation
                text = pytesseract.image_to_string(processed_image, lang=languages, config=config)
            
            # Lấy thông tin chi tiết (bounding boxes)
            data = pytesseract.image_to_data(processed_image, lang=languages, output_type=pytesseract.Output.DICT)
            
            # Tạo danh sách từ với vị trí
            words = []
            confidences = []
            
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:  # Chỉ lấy từ có confidence > 0
                    word_text = data['text'][i].strip()
                    if word_text:  # Chỉ thêm từ không rỗng
                        words.append({
                            "text": word_text,
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
            
            print(f"📊 Tesseract results: {len(text)} chars, {len(words)} words, avg confidence: {avg_confidence:.1f}")
            
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
            
            # Tiền xử lý ảnh (resize để tránh lỗi memory)
            print(f"🔧 Preprocessing image for EasyOCR...")
            processed_image = self._preprocess_image(image_path, enhance=True, max_size=1024)
            
            # OCR với EasyOCR
            try:
                print(f"🚀 Running EasyOCR...")
                results = self.easyocr_reader.readtext(processed_image)
                print(f"📊 EasyOCR found {len(results)} text regions")
            except Exception as e:
                if "memory" in str(e).lower() or "alloc" in str(e).lower():
                    # Thử với ảnh nhỏ hơn nữa
                    print("⚠️ Memory error, trying with smaller image...")
                    processed_image = self._preprocess_image(image_path, enhance=True, max_size=512)
                    results = self.easyocr_reader.readtext(processed_image)
                    print(f"📊 EasyOCR found {len(results)} text regions (smaller image)")
                else:
                    raise e
            
            # Chuyển đổi kết quả
            text_parts = []
            words = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                print(f"  📝 Found: '{text}' (confidence: {confidence:.3f})")
                if confidence > 0.3:  # Giảm threshold để lấy nhiều text hơn
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
            
            print(f"📊 EasyOCR results: {len(full_text)} chars, {len(words)} words, avg confidence: {avg_confidence:.1f}%")
            
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
                print(f"🔍 Auto mode - checking engines...")
                print(f"  - EasyOCR available: {EASYOCR_AVAILABLE}")
                print(f"  - EasyOCR reader initialized: {self.easyocr_reader is not None}")
                print(f"  - Tesseract available: {TESSERACT_AVAILABLE}")
                
                # Ưu tiên Tesseract cho tiếng Việt (tốt hơn cho văn bản giáo dục)
                if self.tesseract_available:
                    print("🚀 Trying Tesseract first (better for Vietnamese)...")
                    result = self._ocr_with_tesseract(image_path)
                    if result["success"] and len(result["text"]) > 20:  # Chỉ chấp nhận nếu có đủ text
                        print("✅ Tesseract succeeded with good result")
                        return result
                    else:
                        error_msg = result.get('error', f'Short text: {len(result.get("text", ""))} chars')
                        print(f"❌ Tesseract failed or low quality: {error_msg}")
                
                # Fallback sang EasyOCR
                if EASYOCR_AVAILABLE and self.easyocr_reader:
                    print("🚀 Trying EasyOCR as fallback...")
                    result = self._ocr_with_easyocr(image_path)
                    if result["success"]:
                        print("✅ EasyOCR succeeded")
                        return result
                    else:
                        print(f"❌ EasyOCR failed: {result.get('error', 'Unknown error')}")
                
                return {
                    "success": False,
                    "error": f"Không có OCR engine nào khả dụng hoặc tất cả đều thất bại. EasyOCR: {EASYOCR_AVAILABLE and self.easyocr_reader is not None}, Tesseract: {self.tesseract_available}"
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
            # Fallback khi tất cả OCR engines đều thất bại
            return {
                "success": False,
                "error": f"Lỗi OCR: {str(e)}. Suggestion: File ảnh có thể quá lớn hoặc OCR engines chưa được cài đặt đúng cách.",
                "fallback_info": {
                    "message": "Không thể đọc text từ ảnh, nhưng file đã được upload thành công",
                    "image_path": image_path,
                    "available_engines": {
                        "easyocr": EASYOCR_AVAILABLE and self.easyocr_reader is not None,
                        "tesseract": self.tesseract_available if hasattr(self, 'tesseract_available') else False
                    }
                }
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
