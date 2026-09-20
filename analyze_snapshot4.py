import json

with open('backend/diag_result.json', 'r', encoding='utf-16') as f:
    snapshot = json.load(f)

diag = snapshot['diagnosis']

# Check if page_count_vs_max_page is actually empty or has different structure
print('page_count_vs_max_page:', diag['page_count_vs_max_page'])
print('type:', type(diag['page_count_vs_max_page']))
print('len:', len(diag['page_count_vs_max_page']))

# Check all keys and their lengths
for key, val in diag.items():
    if isinstance(val, list):
        print(f"  {key}: {len(val)} items")
    elif isinstance(val, dict):
        print(f"  {key}: dict with {len(val)} keys")
    else:
        print(f"  {key}: {type(val)}")