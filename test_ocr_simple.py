#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test OCR imports directly
print("🧪 Testing OCR imports...")

try:
    import pytesseract
    print("✅ pytesseract imported successfully")
except ImportError as e:
    print(f"❌ pytesseract import failed: {e}")

try:
    import easyocr
    print("✅ easyocr imported successfully")
except ImportError as e:
    print(f"❌ easyocr import failed: {e}")

try:
    import cv2
    print("✅ opencv imported successfully")
except ImportError as e:
    print(f"❌ opencv import failed: {e}")

try:
    from PIL import Image
    print("✅ PIL imported successfully")
except ImportError as e:
    print(f"❌ PIL import failed: {e}")

# Test EasyOCR initialization
try:
    reader = easyocr.Reader(['vi', 'en'], gpu=False)
    print("✅ EasyOCR Reader initialized successfully")
    
    # Test with the user's image
    image_path = r"c:\Users\noadv\Desktop\H13-QTEENS-scaled.jpg"
    if os.path.exists(image_path):
        print(f"📄 Testing with image: {image_path}")
        result = reader.readtext(image_path)
        print(f"✅ OCR successful! Found {len(result)} text regions")
        
        # Extract text
        text = ""
        for detection in result:
            text += detection[1] + " "
        
        print(f"📝 Extracted text preview: {text[:200]}...")
    else:
        print(f"❌ Image file not found: {image_path}")
        
except Exception as e:
    print(f"❌ EasyOCR test failed: {e}")
