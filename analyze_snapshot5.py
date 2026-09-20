import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    snapshot = json.load(f)

diag = snapshot['diagnosis']

# Check near_identical_content - this might have page-level data
print('=== near_identical_content (first 20) ===')
for item in diag['near_identical_content'][:20]:
    print(f"  {item}")

# Check repeated_paragraphs more
print()
print('=== repeated_paragraphs (all) ===')
for item in diag['repeated_paragraphs']:
    print(f"  ID={item['book_id']} Title='{item['title']}' n={item['n']}")

# Check identical_pages_across_books
print()
print('=== identical_pages_across_books ===')
for item in diag['identical_pages_across_books']:
    print(f"  {item}")