import pandas as pd
import sys

file_path = sys.argv[1] if len(sys.argv) > 1 else '../odoo-dictionary/Models (ir.model) (1).xlsx'

df = pd.read_excel(file_path, nrows=3)
print(f"File: {file_path}")
print(f"\nColumns ({len(df.columns)}):")
for col in df.columns:
    print(f"  - {col}")

print(f"\nFirst row:")
for k, v in df.iloc[0].to_dict().items():
    print(f"  {k}: {v}")

print(f"\nTotal rows in sample: {len(df)}")
