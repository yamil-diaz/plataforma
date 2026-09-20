import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    data = json.load(f)
diag = data['diagnosis']

# books_suspicious_content
print('=== books_suspicious_content ===')
val = diag.get('books_suspicious_content', [])
if isinstance(val, list):
    for item in val:
        print('  ', item)

# repeated_paragraphs
print()
print('=== repeated_paragraphs (first 20) ===')
val = diag.get('repeated_paragraphs', [])
if isinstance(val, list):
    for item in val[:20]:
        print('  ', item)
    print(f'  ... total: {len(val)}')