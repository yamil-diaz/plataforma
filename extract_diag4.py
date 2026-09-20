import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    data = json.load(f)
diag = data['diagnosis']

# repeated_paragraphs
print('=== repeated_paragraphs (all) ===')
val = diag.get('repeated_paragraphs', [])
if isinstance(val, list):
    for item in val:
        print('  ', item)
    print(f'total: {len(val)}')