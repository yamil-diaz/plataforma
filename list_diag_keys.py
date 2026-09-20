import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    data = json.load(f)
diag = data['diagnosis']

# Get all diagnostics that can help identify affected books
print('=== all diagnostic keys and counts ===')
for k in sorted(diag.keys()):
    v = diag[k]
    if isinstance(v, list):
        print(f'{k}: {len(v)} items')
    else:
        print(f'{k}: {type(v).__name__}')