"""
Check what fields are available in sale.order and sale.order.line models.
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.field_mapper.core.knowledge_base import OdooKnowledgeBase

print("Loading knowledge base...")
kb = OdooKnowledgeBase(dictionary_path="/home/ben/Documents/GitHub/data-migrator/odoo-dictionary")
kb.load_from_dictionary()

print("\n" + "=" * 80)
print("Fields in sale.order.line that contain 'total' or 'amount':")
print("=" * 80)

for (model_name, field_name), field in kb.fields.items():
    if model_name == "sale.order.line":
        if "total" in field_name.lower() or "amount" in field_name.lower():
            print(f"  {field_name:30} ({field.field_type}) - {field.field_label or 'No label'}")

print("\n" + "=" * 80)
print("All fields in sale.order.line (first 20):")
print("=" * 80)

count = 0
for (model_name, field_name), field in kb.fields.items():
    if model_name == "sale.order.line":
        print(f"  {field_name:30} ({field.field_type})")
        count += 1
        if count >= 20:
            break

print(f"\n... and {sum(1 for (m, f) in kb.fields.keys() if m == 'sale.order.line') - 20} more fields")