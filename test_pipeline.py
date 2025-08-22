#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.ocr_tool import OCRTool
from services.embedding_service import EmbeddingService
from database import DatabaseManager

def test_full_pipeline():
    print("🔬 Testing Full Processing Pipeline...")
    
    # Test files
    test_files = [
        r'c:\Users\noadv\Desktop\ta1.png',
        r'c:\Users\noadv\Desktop\H13-QTEENS-scaled.jpg'
    ]
    
    ocr = OCRTool()
    embedding_service = EmbeddingService()
    db_manager = DatabaseManager()
    
    for file_path in test_files:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            continue
            
        print(f"\n📄 Testing: {os.path.basename(file_path)}")
        
        # Step 1: OCR
        print("🔍 Step 1: OCR Extraction...")
        ocr_result = ocr.extract_text_from_image(file_path)
        
        if not ocr_result["success"]:
            print(f"❌ OCR Failed: {ocr_result['error']}")
            continue
            
        extracted_text = ocr_result["text"]
        print(f"✅ OCR Success! Length: {len(extracted_text)} chars")
        print(f"📝 Sample: {extracted_text[:200]}...")
        
        # Step 2: Processing
        print("\n🔧 Step 2: Embedding Processing...")
        file_id = f"test_{os.path.basename(file_path)}_{int(time.time())}"
        
        process_result = embedding_service.process_file_content(
            file_id=file_id,
            content=extracted_text,
            metadata={
                "test_mode": True,
                "source_file": file_path
            }
        )
        
        if process_result["success"]:
            print(f"✅ Processing Success! {process_result['total_chunks']} chunks created")
            
            # Step 3: Verify Database Storage
            print("\n📊 Step 3: Database Verification...")
            collection = db_manager.db["document_embeddings"]
            docs = list(collection.find({"file_id": file_id}))
            
            print(f"📝 Found {len(docs)} documents in database")
            
            for i, doc in enumerate(docs):
                content_in_db = doc.get("content", "")
                print(f"  Chunk {i}: {len(content_in_db)} chars")
                print(f"    Sample: {content_in_db[:100]}...")
                
                if len(content_in_db) < 50:
                    print(f"    ⚠️ WARNING: Very short content!")
                    
        else:
            print(f"❌ Processing Failed: {process_result['error']}")

if __name__ == "__main__":
    import time
    test_full_pipeline()
