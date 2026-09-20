import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    data = json.load(f)
diag = data['diagnosis']

# 1. identical_book_content - 35 books with placeholder content
print('=== 1. IDENTICAL BOOK CONTENT (placeholder) ===')
val = diag.get('identical_book_content', [])
if val:
    item = val[0]
    ids = item['ids']
    titles = item['titles']
    for i, (bid, title) in enumerate(zip(ids, titles)):
        print(f'  ID {bid}: {title}')

print(f'\nTotal: {len(ids)} books')

# 2. identical_pages_across_books - 35 pages with placeholder content
print('\n=== 2. IDENTICAL PAGES ACROSS BOOKS ===')
val = diag.get('identical_pages_across_books', [])
if val:
    item = val[0]
    page_ids = item['page_ids']
    book_ids = item['book_ids']
    for pid, bid in zip(page_ids[:10], book_ids[:10]):
        print(f'  Page ID {pid} -> Book ID {bid}')
    print(f'  ... total {len(page_ids)} pages across {len(book_ids)} books')

# 3. books_suspicious_content
print('\n=== 3. BOOKS SUSPICIOUS CONTENT ===')
val = diag.get('books_suspicious_content', [])
for item in val:
    print(f'  ID {item["id"]}: {item["title"]}')

# 4. repeated_paragraphs
print('\n=== 4. REPEATED PARAGRAPHS (first 20) ===')
val = diag.get('repeated_paragraphs', [])
for item in val[:20]:
    par_preview = item['par'][:60] if isinstance(item['par'], str) else str(item['par'])
    print(f'  Book ID {item["book_id"]}: {item["title"]} | par: "{par_preview}"... | count: {item["n"]}')
print(f'  ... total: {len(val)} books')

# 5. near_identical_content
print('\n=== 5. NEAR IDENTICAL CONTENT (first 20) ===')
val = diag.get('near_identical_content', [])
for item in val[:20]:
    print(f'  ID {item["id_a"]} ({item["title_a"]}) ~ ID {item["id_b"]} ({item["title_b"]})')
print(f'  ... total: {len(val)} pairs')

# 6. duplicate_title_author
print('\n=== 6. DUPLICATE TITLE/AUTHOR ===')
val = diag.get('duplicate_title_author', [])
for item in val:
    print(f'  {item}')

# 7. books_published_status
print('\n=== 7. BOOKS PUBLISHED STATUS ===')
val = diag.get('books_published_status', [])
if val:
    print(val)

# 8. row_counts for key tables
print('\n=== 8. ROW COUNTS ===')
val = diag.get('row_counts', [])
for item in val:
    if 'book' in item['table_name'].lower():
        print(f'  {item["table_name"]}: {item["live_rows"]} live, {item["dead_rows"]} dead')