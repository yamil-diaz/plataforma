import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    snapshot = json.load(f)

diag = snapshot['diagnosis']

# Check El Principito results
print('=== el_principito_results ===')
for item in diag['el_principito_results']:
    print(f"  {item}")

# Check page_count_vs_max_page for IDs around 18 and 128
print()
print('=== page_count_vs_max_page (IDs 1-20 and 120-135) ===')
for item in diag['page_count_vs_max_page']:
    if item['id'] <= 20 or (item['id'] >= 120 and item['id'] <= 135):
        print(f"  ID={item['id']} Title='{item['title']}' page_count={item['page_count']} max_page={item['max_page']}")

# Check identical_book_content
print()
print('=== identical_book_content ===')
for item in diag['identical_book_content']:
    print(f"  {item}")

# Check books_suspicious_content
print()
print('=== books_suspicious_content ===')
for item in diag['books_suspicious_content']:
    print(f"  ID={item['id']} Title='{item['title']}'")

# Check repeated_paragraphs
print()
print('=== repeated_paragraphs (first 20) ===')
for item in diag['repeated_paragraphs'][:20]:
    print(f"  ID={item['book_id']} Title='{item['title']}' n={item['n']}")

# Check books_empty_or_placeholder
print()
print('=== books_empty_or_placeholder ===')
for item in diag['books_empty_or_placeholder']:
    print(f"  ID={item['id']} Title='{item['title']}'")

# Check page duplicates
print()
print('=== page_duplicates_book_page ===')
for item in diag['page_duplicates_book_page']:
    print(f"  {item}")

# Check empty pages
print()
print('=== empty_pages ===')
for item in diag['empty_pages']:
    print(f"  {item}")

# Check page numbering gaps
print()
print('=== page_numbering_gaps ===')
for item in diag['page_numbering_gaps']:
    print(f"  {item}")