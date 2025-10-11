"""
Test script with debug output to verify improved field mapping.
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.field_mapper.main import DeterministicFieldMapper
from app.field_mapper.matching.business_context_analyzer import BusinessContextAnalyzer
from app.field_mapper.matching.cell_data_analyzer import CellDataAnalyzer
import pandas as pd

print("=" * 80)
print("TESTING IMPROVED FIELD MAPPER WITH DEBUG OUTPUT")
print("=" * 80)

# Initialize mapper
print("\n1. Initializing mapper...")
mapper = DeterministicFieldMapper(
    dictionary_path="/home/ben/Documents/GitHub/data-migrator/odoo-dictionary"
)

# Test with sample customer data
print("\n2. Creating sample customer data...")
df = pd.DataFrame({
    "name": ["John Doe", "Jane Smith", "Acme Corp", "Tech Industries"],
    "email": ["john@example.com", "jane@example.com", "info@acme.com", "contact@tech.com"],
    "phone": ["+1234567890", "+0987654321", "+1122334455", "+9988776655"],
    "street": ["123 Main St", "456 Oak Ave", "789 Business Blvd", "321 Tech Park"],
    "city": ["New York", "Los Angeles", "Chicago", "San Francisco"],
    "country_id": ["United States", "United States", "United States", "United States"],
})

print(f"Sample data:\n{df.head()}")

# Profile the data first
print("\n3. Profiling columns...")
from app.field_mapper.profiling.column_profiler import ColumnProfiler
profiler = ColumnProfiler()
profiles = profiler.profile_dataframe(df, sheet_name="Customers")

# Test business context detection
print("\n4. Analyzing business context...")
analyzer = BusinessContextAnalyzer()
detected_models = analyzer.get_recommended_models(profiles, max_models=5)
primary_domain = analyzer.detect_primary_domain(profiles)

print(f"Primary domain detected: {primary_domain}")
print(f"Recommended models: {detected_models}")

# Test cell data analysis
print("\n5. Analyzing cell values...")
cell_analyzer = CellDataAnalyzer()
for profile in profiles[:3]:  # Test first 3 columns
    analysis = cell_analyzer.analyze_column(profile)
    print(f"  {profile.column_name}: entity_type={analysis.entity_type}, category={analysis.value_category}")

# Map the dataframe
print("\n6. Running field mapping...")
mappings = mapper.map_dataframe(df, sheet_name="Customers")

print("\n" + "=" * 80)
print("MAPPING RESULTS:")
print("=" * 80)

for col_name, field_mappings in mappings.items():
    if field_mappings:
        best = field_mappings[0]
        status = "✓" if best.target_model == "res.partner" else "✗"
        print(f"{status} {col_name:15} -> {best.target_model}.{best.target_field:20} (confidence: {best.confidence:.2f})")

        # Show alternatives
        if len(field_mappings) > 1:
            for i, alt in enumerate(field_mappings[1:3], 1):
                print(f"  Alt {i}: {alt.target_model}.{alt.target_field} ({alt.confidence:.2f})")
    else:
        print(f"✗ {col_name:15} -> No mapping found")

# Calculate success rate
correct_mappings = sum(1 for col, mappings in mappings.items()
                      if mappings and mappings[0].target_model == "res.partner")
total_columns = len(mappings)

print("\n" + "=" * 80)
print(f"SUCCESS RATE: {correct_mappings}/{total_columns} columns correctly mapped to res.partner")
print("=" * 80)