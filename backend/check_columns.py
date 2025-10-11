import pandas as pd
import sqlite3
import json

# Connect to database
conn = sqlite3.connect('data_migrator.db')

# Get column profiles for the Financial Sample dataset
query = '''
SELECT cp.name as column_name, cp.dtype_guess, cp.sample_values, s.name as sheet_name
FROM column_profiles cp
JOIN sheets s ON cp.sheet_id = s.id
JOIN datasets d ON s.dataset_id = d.id
WHERE d.name LIKE '%Financial%'
ORDER BY s.name, cp.name
'''
cursor = conn.execute(query)
results = cursor.fetchall()

print('Financial Sample columns by sheet:')
print('=' * 70)
current_sheet = None
for row in results:
    col_name, dtype, sample_values, sheet_name = row
    if sheet_name != current_sheet:
        print(f'\nSheet: {sheet_name}')
        print('-' * 50)
        current_sheet = sheet_name
    samples = json.loads(sample_values) if sample_values else []
    samples_str = str(samples[:2])[:40] if samples else '[]'
    print(f'  {col_name:25} | {dtype:10} | {samples_str}')

conn.close()