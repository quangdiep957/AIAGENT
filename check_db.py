#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymongo
from database import DatabaseManager

db_manager = DatabaseManager()
collection = db_manager.db['document_embeddings']

print('🔍 Checking all documents in database...')
docs = list(collection.find({}, {'file_id': 1, 'content': 1, 'char_count': 1, 'created_at': 1}).sort('created_at', -1).limit(10))

for i, doc in enumerate(docs):
    content = doc.get('content', '')
    char_count = doc.get('char_count', 0)
    print(f'{i+1}. File: {doc.get("file_id", "unknown")}')
    print(f'   Length: {len(content)} chars (recorded: {char_count})')
    print(f'   Sample: {content[:150]}...')
    print(f'   Created: {doc.get("created_at", "unknown")}')
    print()
