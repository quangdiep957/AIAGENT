#!/usr/bin/env python3

from tools.ocr_tool import OCRTool

# Test OCR tool
if __name__ == "__main__":
    print("🧪 Testing OCR Tool...")
    
    # Initialize OCR tool
    ocr_tool = OCRTool(ocr_engine="auto")
    
    # Test with the user's image
    image_path = r"c:\Users\noadv\Desktop\H13-QTEENS-scaled.jpg"
    
    print(f"\n📄 Testing with image: {image_path}")
    result = ocr_tool.extract_text_from_image(image_path)
    
    print(f"\n📊 Result:")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Text length: {len(result['text'])}")
        print(f"Text preview: {result['text'][:200]}...")
    else:
        print(f"Error: {result['error']}")
