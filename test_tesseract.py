#!/usr/bin/env python3

import cv2
import pytesseract
import os

# Test with Tesseract instead of EasyOCR
print("🧪 Testing OCR with Tesseract...")

image_path = r"c:\Users\noadv\Desktop\H13-QTEENS-scaled.jpg"

if not os.path.exists(image_path):
    print(f"❌ Image file not found: {image_path}")
    exit(1)

try:
    # Load and resize image
    image = cv2.imread(image_path)
    if image is None:
        print("❌ Cannot read image")
        exit(1)
    
    height, width = image.shape[:2]
    print(f"📏 Original image size: {width}x{height}")
    
    # Resize if too large
    max_size = 1024
    if max(height, width) > max_size:
        scale = max_size / max(height, width)
        new_width = int(width * scale)
        new_height = int(height * scale)
        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        print(f"🔧 Resized to: {new_width}x{new_height}")
    
    # Convert to grayscale for better OCR
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Perform OCR with Tesseract
    print("🔍 Performing OCR with Tesseract...")
    
    # Configure for Vietnamese
    config = '--oem 3 --psm 6 -l vie+eng'
    text = pytesseract.image_to_string(gray, config=config)
    
    print(f"✅ OCR successful!")
    print(f"📄 Extracted text:\n{text}")
    
    if text.strip():
        print(f"📊 Text length: {len(text)} characters")
    else:
        print("⚠️ No text extracted")
        
except Exception as e:
    print(f"❌ OCR test failed: {e}")
    import traceback
    traceback.print_exc()
