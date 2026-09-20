import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    snapshot = json.load(f)

diag = snapshot['diagnosis']

# 1. El Principito results
print('=== 1. EL PRINCIPITO ===')
for item in diag['el_principito_results']:
    print(f"  ID={item['id']} Title='{item['title']}' Author='{item['author_name']}' page_count={item['page_count']} published={item['published']} content_length={item['content_length']}")

# 2. Duplicate title/author
print()
print('=== 2. DUPLICADOS EXACTOS ===')
for item in diag['duplicate_title_author']:
    if item['title'].lower().strip() == 'el principito':
        print(f"  Title='{item['title']}' Author='{item['author_name']}' IDs={item['ids']}")

# 3. Identical book content (placeholders)
print()
print('=== 3. PLACEHOLDERS ===')
for item in diag['identical_book_content']:
    print(f"  Content='{item['content'][:50]}...' n={item['n']} IDs={item['ids'][:10]}...")

# 4. Suspicious content
print()
print('=== 4. SUSPICIOUS CONTENT ===')
for item in diag['books_suspicious_content']:
    print(f"  ID={item['id']} Title='{item['title']}'")

# 5. Repeated paragraphs (fabricated content)
print()
print('=== 5. REPEATED PARAGRAPHS (top 20) ===')
for item in diag['repeated_paragraphs'][:20]:
    title = item['title'].replace('\u2554', '?').replace('\u2550', '?').replace('\u2557', '?')
    print(f"  ID={item['book_id']} Title='{title}' n={item['n']}")

# 6. Total books published
print()
print('=== 6. BOOKS PUBLISHED STATUS ===')
for item in diag['books_published_status']:
    print(f"  {item}")

# 7. Critical columns check (page_count null/zero)
print()
print('=== 7. BOOKS PAGE COUNT NULL OR ZERO ===')
print(f"  Count: {len(diag['books_page_count_null_or_zero'])}")

# 8. Books without pages
print()
print('=== 8. BOOKS WITHOUT PAGES ===')
print(f"  Count: {len(diag['books_without_pages'])}")

# 9. Page count vs max page
print()
print('=== 9. PAGE COUNT VS MAX PAGE ===')
print(f"  Count: {len(diag['page_count_vs_max_page'])}")

# 10. Page duplicates
print()
print('=== 10. PAGE DUPLICATES ===')
print(f"  Count: {len(diag['page_duplicates_book_page'])}")

# 11. Empty pages
print()
print('=== 11. EMPTY PAGES ===')
print(f"  Count: {len(diag['empty_pages'])}")

# 12. Page numbering gaps
print()
print('=== 12. PAGE NUMBERING GAPS ===')
print(f"  Count: {len(diag['page_numbering_gaps'])}")

# 13. All duplicate title/author groups
print()
print('=== 13. ALL DUPLICATE GROUPS ===')
for item in diag['duplicate_title_author']:
    print(f"  Title='{item['title']}' Author='{item['author_name']}' IDs={item['ids']}")

# 14. Near identical content (summary)
print()
print('=== 14. NEAR IDENTICAL CONTENT (count) ===')
print(f"  {len(diag['near_identical_content'])} pairs")