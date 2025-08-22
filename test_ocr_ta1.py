#!/usr/bin/env python3

import sys
import os

# Test OCR directly trong virtual environment
print("🧪 Testing OCR with ta1.png...")

# Path to test image
test_image = r"c:\Users\noadv\Desktop\ta1.png"

if not os.path.exists(test_image):
    print(f"❌ Test image not found: {test_image}")
    print("Please make sure the file exists at this path")
    exit(1)

try:
    # Import OCR tool directly
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Import just what we need without the problematic tools module
    import pytesseract
    import easyocr
    import cv2
    from PIL import Image
    
    print("✅ All OCR libraries imported successfully")
    
    # Test image reading
    img = cv2.imread(test_image)
    if img is None:
        print(f"❌ Cannot read image with OpenCV: {test_image}")
        exit(1)
    
    print(f"✅ Image loaded successfully: {img.shape}")
    
    # Resize if too large
    height, width = img.shape[:2]
    if max(height, width) > 1024:
        scale = 1024 / max(height, width)
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        print(f"🔧 Resized to: {new_width}x{new_height}")
    
    # Save processed image
    temp_path = "temp_processed.png"
    cv2.imwrite(temp_path, img)
    
    # Test Tesseract
    print("\n🚀 Testing Tesseract...")
    try:
        text_tesseract = pytesseract.image_to_string(temp_path, lang='vie+eng', config='--oem 3 --psm 6')
        print(f"✅ Tesseract result ({len(text_tesseract)} chars):")
        print(f"Preview: {text_tesseract[:200]}...")
    except Exception as e:
        print(f"❌ Tesseract failed: {e}")
        text_tesseract = ""
    
    # Test EasyOCR
    print("\n🚀 Testing EasyOCR...")
    try:
        reader = easyocr.Reader(['vi', 'en'], gpu=False)
        results = reader.readtext(temp_path)
        
        text_parts = []
        for (bbox, text, confidence) in results:
            if confidence > 0.3:
                text_parts.append(text)
                print(f"  📝 '{text}' (confidence: {confidence:.3f})")
        
        text_easyocr = " ".join(text_parts)
        print(f"✅ EasyOCR result ({len(text_easyocr)} chars):")
        print(f"Full text: {text_easyocr}")
        
    except Exception as e:
        print(f"❌ EasyOCR failed: {e}")
        text_easyocr = ""
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"  - Tesseract: {len(text_tesseract)} characters")
    print(f"  - EasyOCR: {len(text_easyocr)} characters")
    
    if text_tesseract or text_easyocr:
        print("✅ At least one OCR engine extracted text successfully!")
    else:
        print("❌ Both OCR engines failed to extract text")
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
