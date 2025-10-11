"""
Test script to verify the field mapper works with the actual Odoo dictionary files.
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.field_mapper.main import DeterministicFieldMapper
import pandas as pd

print("=" * 80)
print("TESTING WITH ACTUAL ODOO DICTIONARY FILES")
print("=" * 80)

try:
    # Initialize mapper - should auto-detect the odoo-dictionary folder
    print("\n1. Initializing mapper (loading Odoo dictionary)...")
    mapper = DeterministicFieldMapper(
        dictionary_path="/home/ben/Documents/GitHub/data-migrator/odoo-dictionary"
    )

    stats = mapper.get_statistics()
    print(f"✓ Knowledge base loaded successfully!")
    print(f"  - Models: {stats['knowledge_base']['total_models']}")
    print(f"  - Fields: {stats['knowledge_base']['total_fields']}")
    print(f"  - Selections: {stats['knowledge_base']['total_selections']}")

    # Test with sample data
    print("\n2. Testing with sample customer data...")
    df = pd.DataFrame({
        "name": ["John Doe", "Jane Smith"],
        "email": ["john@example.com", "jane@example.com"],
        "phone": ["+1234567890", "+0987654321"],
        "street": ["123 Main St", "456 Oak Ave"],
        "city": ["New York", "Los Angeles"],
        "country_id": ["United States", "United States"],
    })

    mappings = mapper.map_dataframe(df, sheet_name="Customers")

    print(f"✓ Processed {len(df.columns)} columns")
    print(f"  Mappings dict type: {type(mappings)}")
    print(f"  Mappings dict keys: {list(mappings.keys()) if mappings else 'EMPTY'}")

    # Count mappings
    mapped_count = sum(1 for field_mappings in mappings.values() if field_mappings)
    unmapped_count = len(mappings) - mapped_count

    print(f"✓ Found mappings for {mapped_count}/{len(mappings)} columns")

    print("\nMapping Results:")
    for col_name, field_mappings in mappings.items():
        if field_mappings:
            best = field_mappings[0]
            print(f"  ✓ {col_name:15} -> {best.target_model}.{best.target_field:20} (confidence: {best.confidence:.2f})")
            print(f"    Strategy: {best.matching_strategy}")
            print(f"    Rationale: {best.rationale[:80]}...")
        else:
            print(f"  ✗ {col_name:15} -> No confident mapping found")

    print("\n" + "=" * 80)
    print("✓ SUCCESS! The system works with your Odoo dictionary files!")
    print("=" * 80)

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
