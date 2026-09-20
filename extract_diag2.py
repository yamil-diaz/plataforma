import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    data = json.load(f)
diag = data['diagnosis']

# identical_pages_across_books
print('=== identical_pages_across_books ===')
val = diag.get('identical_pages_across_books', [])
if isinstance(val, list) and val:
    item = val[0]
    print('Content:', item['content'][:60])
    print('Count:', item['n'])
    print('Page IDs:', item['page_ids'][:10])
    print('Book IDs:', item['book_ids'][:10])
    print('Total page IDs:', len(item['page_ids']))
    print('Total book IDs:', len(item['book_ids']))