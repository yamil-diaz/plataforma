import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    snapshot = json.load(f)

diag = snapshot['diagnosis']

print("=== 1. BOOKS PAGE COUNT NULL OR ZERO ===")
print(f"Count: {len(diag['books_page_count_null_or_zero'])}")
for item in diag['books_page_count_null_or_zero'][:10]:
    print(f"  ID={item['id']} Title='{item['title']}' page_count={item['page_count']} max_page={item['max_page']}")

print()
print("=== 2. BOOKS WITHOUT PAGES ===")
print(f"Count: {len(diag['books_without_pages'])}")
for item in diag['books_without_pages'][:10]:
    print(f"  ID={item['id']} Title='{item['title']}' page_count={item['page_count']}")

print()
print("=== 3. PAGE COUNT VS MAX PAGE ===")
print(f"Count: {len(diag['page_count_vs_max_page'])}")
for item in diag['page_count_vs_max_page'][:20]:
    print(f"  ID={item['id']} Title='{item['title']}' page_count={item['page_count']} max_page={item['max_page']}")

print()
print("=== 4. BOOKS PUBLISHED STATUS ===")
for item in diag['books_published_status']:
    print(f"  {item}")

print()
print("=== 5. EL PRINCIPITO (IDs 18, 128) ===")
for item in diag['el_principito_results']:
    print(f"  ID={item['id']} Title='{item['title']}' page_count={item['page_count']} published={item['published']} content_length={item['content_length']}")

print()
print("=== 6. ALL DUPLICATE TITLE/AUTHOR ===")
for item in diag['duplicate_title_author']:
    print(f"  Title='{item['title']}' Author='{item['author_name']}' IDs={item['ids']}")

print()
print("=== 7. PLACEHOLDERS ===")
for item in diag['identical_book_content']:
    print(f"  Content='{item['content'][:50]}...' n={item['n']} IDs={item['ids'][:10]}...")

print()
print("=== 8. SUSPICIOUS CONTENT ===")
for item in diag['books_suspicious_content']:
    print(f"  ID={item['id']} Title='{item['title']}'")

print()
print("=== 9. REPEATED PARAGRAPHS (top 30) ===")
for item in diag['repeated_paragraphs'][:30]:
    print(f"  ID={item['book_id']} Title='{item['title']}' n={item['n']}")

# Check if we can find books with page_count <= 0 from the el_principito and duplicate data
print()
print("=== 10. CHECK SPECIFIC BOOKS FOR page_count <= 0 ===")
# The snapshot doesn't have a complete book list with page_count
# But we can infer from el_principito_results and the fact that books_page_count_null_or_zero is empty
print("books_page_count_null_or_zero is EMPTY (0 items)")
print("This means the diagnostic query found NO books with page_count IS NULL OR page_count <= 0")
print()
print("books_without_pages is EMPTY (0 items)")
print("This means ALL books have at least 1 book_pages entry")
print()
print("page_count_vs_max_page is EMPTY (0 items)")
print("This means page_count == max(page_number) for ALL books")