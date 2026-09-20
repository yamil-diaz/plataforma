import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    data = json.load(f)
diag = data['diagnosis']

# identical_book_content
print('=== identical_book_content ===')
val = diag.get('identical_book_content', [])
if isinstance(val, list) and val:
    item = val[0]
    print('Content:', item['content'][:60])
    print('Count:', item['n'])
    print('IDs:', item['ids'])
    print('Titles:', item['titles'])