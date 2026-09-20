import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    snapshot = json.load(f)

diag = snapshot['diagnosis']

# Check all page_count_vs_max_page
print('=== ALL page_count_vs_max_page ===')
for item in diag['page_count_vs_max_page']:
    print(f"  ID={item['id']} Title='{item['title']}' page_count={item['page_count']} max_page={item['max_page']}")

# Check total books
print()
print('=== books_published_status ===')
for item in diag['books_published_status']:
    print(f"  {item}")