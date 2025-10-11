"""
Test compound name parsing in field mapper.

This script specifically tests whether compound column names like
"customer_name", "product_price", etc. are correctly parsed and mapped.
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.field_mapper.main import DeterministicFieldMapper
import pandas as pd

print("=" * 80)
print("TESTING COMPOUND NAME PARSING")
print("=" * 80)

# Initialize mapper
print("\n1. Initializing mapper...")
mapper = DeterministicFieldMapper(
    dictionary_path="/home/ben/Documents/GitHub/data-migrator/odoo-dictionary"
)

# Test 1: Mixed compound names with module filtering
print("\n" + "=" * 80)
print("TEST: Compound Names with Module Selection")
print("=" * 80)

df_compound = pd.DataFrame({
    # Customer-related columns
    "customer_name": ["Acme Corp", "Tech Ltd", "Global Inc"],
    "customer_email": ["acme@example.com", "tech@example.com", "global@example.com"],
    "customer_phone": ["+1234567890", "+0987654321", "+1122334455"],

    # Product-related columns
    "product_name": ["Widget A", "Gadget B", "Tool C"],
    "product_price": [19.99, 29.99, 39.99],
    "product_sku": ["WDG-001", "GDT-002", "TL-003"],

    # Order-related columns
    "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "order_quantity": [10, 20, 30],
    "order_total": [199.90, 599.80, 1199.70],
})

print("\nMapping with modules: ['contacts', 'products', 'sales_crm']")
mappings = mapper.map_dataframe(
    df_compound,
    sheet_name="CompoundNames",
    selected_modules=["contacts", "products", "sales_crm"]
)

print("\n" + "-" * 80)
print("RESULTS:")
print("-" * 80)

# Group results by entity prefix
customer_fields = []
product_fields = []
order_fields = []
other_fields = []

for col_name, field_mappings in mappings.items():
    if field_mappings:
        best = field_mappings[0]
        mapping_info = f"{col_name:20} -> {best.target_model:20}.{best.target_field:20} (conf: {best.confidence:.2f})"

        # Categorize by prefix
        if col_name.startswith("customer_"):
            customer_fields.append(mapping_info)
        elif col_name.startswith("product_"):
            product_fields.append(mapping_info)
        elif col_name.startswith("order_"):
            order_fields.append(mapping_info)
        else:
            other_fields.append(mapping_info)
    else:
        print(f"  ✗ {col_name:20} -> No mapping found")

# Display grouped results
print("\nCustomer Fields (should map to res.partner):")
for field in customer_fields:
    is_correct = "res.partner" in field
    status = "✓" if is_correct else "✗"
    print(f"  {status} {field}")

print("\nProduct Fields (should map to product.product or product.template):")
for field in product_fields:
    is_correct = "product.product" in field or "product.template" in field
    status = "✓" if is_correct else "✗"
    print(f"  {status} {field}")

print("\nOrder Fields (should map to sale.order or sale.order.line):")
for field in order_fields:
    is_correct = "sale.order" in field
    status = "✓" if is_correct else "✗"
    print(f"  {status} {field}")

if other_fields:
    print("\nOther Fields:")
    for field in other_fields:
        print(f"  ? {field}")

# Calculate success rates
print("\n" + "=" * 80)
print("SUMMARY:")
print("=" * 80)

total_cols = len(mappings)
customer_correct = sum(1 for f in customer_fields if "res.partner" in f)
product_correct = sum(1 for f in product_fields if "product.product" in f or "product.template" in f)
order_correct = sum(1 for f in order_fields if "sale.order" in f)

print(f"Customer fields: {customer_correct}/{len(customer_fields)} correct")
print(f"Product fields:  {product_correct}/{len(product_fields)} correct")
print(f"Order fields:    {order_correct}/{len(order_fields)} correct")

total_correct = customer_correct + product_correct + order_correct
print(f"\nOverall: {total_correct}/{total_cols} fields correctly mapped ({total_correct*100//total_cols}%)")

if total_correct < total_cols:
    print("\n⚠️  Some compound names are not being parsed correctly.")
    print("   The compound name parser may need enhancement.")
else:
    print("\n✅ All compound names parsed and mapped correctly!")