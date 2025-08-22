#!/usr/bin/env python3

import cv2
import easyocr
import os

# Test with smaller image size
print("🧪 Testing OCR with resized image...")

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
    max_size = 800
    if max(height, width) > max_size:
        scale = max_size / max(height, width)
        new_width = int(width * scale)
        new_height = int(height * scale)
        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        print(f"🔧 Resized to: {new_width}x{new_height}")
        
        # Save resized image temporarily
        temp_path = "temp_resized.jpg"
        cv2.imwrite(temp_path, image)
        
        # Use resized image for OCR
        image_path = temp_path
    
    # Initialize EasyOCR
    print("⚡ Initializing EasyOCR...")
    reader = easyocr.Reader(['vi', 'en'], gpu=False)
    
    # Perform OCR
    print("🔍 Performing OCR...")
    results = reader.readtext(image_path)
    
    print(f"✅ OCR successful! Found {len(results)} text regions")
    
    # Extract text
    text_parts = []
    for detection in results:
        bbox, text, confidence = detection
        if confidence > 0.3:  # Filter low confidence
            text_parts.append(text)
            print(f"  📝 '{text}' (confidence: {confidence:.2f})")
    
    full_text = " ".join(text_parts)
    print(f"\n📄 Full extracted text:\n{full_text}")
    
    # Cleanup
    if os.path.exists("temp_resized.jpg"):
        os.remove("temp_resized.jpg")
        
except Exception as e:
    print(f"❌ OCR test failed: {e}")
    import traceback
    traceback.print_exc()
