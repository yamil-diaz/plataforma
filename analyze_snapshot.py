import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    snapshot = json.load(f)

diag = snapshot['diagnosis']

# Check books with page_count = 0 or NULL
print('=== books_page_count_null_or_zero ===')
for item in diag['books_page_count_null_or_zero']:
    print(f"  ID={item['id']} Title='{item['title']}' page_count={item['page_count']} max_page={item['max_page']}")

print()
print('=== books_without_pages ===')
for item in diag['books_without_pages']:
    print(f"  ID={item['id']} Title='{item['title']}' page_count={item['page_count']}")

print()
print('=== page_count_vs_max_page (first 30) ===')
for item in diag['page_count_vs_max_page'][:30]:
    print(f"  ID={item['id']} Title='{item['title']}' page_count={item['page_count']} max_page={item['max_page']}")

# Check duplicate El Principito
print()
print('=== duplicate_title_author ===')
for item in diag['duplicate_title_author']:
    print(f"  Title='{item['title']}' Author='{item['author_name']}' IDs={item['ids']}")

# Check El Principito results
print()
print('=== el_principito_results ===')
for item in diag['el_principito_results']:
    print(f"  ID={item['id']} Title='{item['title']}' Author='{item['author_name']}' page_count={item['page_count']} max_page={item['max_page']} content_len={item['content_length']}")