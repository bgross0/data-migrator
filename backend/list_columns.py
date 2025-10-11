import sqlite3
import json

conn = sqlite3.connect('data_migrator.db')

# Get all column profiles
query = '''
SELECT cp.name as column_name, cp.dtype_guess, cp.sample_values, s.name as sheet_name, d.name as dataset_name
FROM column_profiles cp
JOIN sheets s ON cp.sheet_id = s.id
JOIN datasets d ON s.dataset_id = d.id
ORDER BY d.name, s.name, cp.name
'''
cursor = conn.execute(query)
results = cursor.fetchall()

print('All column profiles:')
print('=' * 70)
current_dataset = None
current_sheet = None
for row in results:
    col_name, dtype, sample_values, sheet_name, dataset_name = row
    if dataset_name != current_dataset:
        print(f'\n\nDataset: {dataset_name}')
        print('=' * 50)
        current_dataset = dataset_name
        current_sheet = None
    if sheet_name != current_sheet:
        print(f'\n  Sheet: {sheet_name}')
        print('  ' + '-' * 40)
        current_sheet = sheet_name
    samples = json.loads(sample_values) if sample_values else []
    samples_str = str(samples[:2])[:35] if samples else '[]'
    print(f'    {col_name:25} | {dtype:10} | {samples_str}')

conn.close()