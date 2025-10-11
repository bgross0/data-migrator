"""
Check if fleet module models and fields are in the knowledge base.
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.field_mapper.core.knowledge_base import OdooKnowledgeBase
from app.field_mapper.core.module_registry import get_module_registry

print("Loading knowledge base...")
kb = OdooKnowledgeBase(dictionary_path="/home/ben/Documents/GitHub/data-migrator/odoo-dictionary")
kb.load_from_dictionary()

print("\n" + "=" * 80)
print("FLEET MODULE COVERAGE CHECK")
print("=" * 80)

# Check for fleet models
fleet_models = []
for model_name in kb.models.keys():
    if "fleet" in model_name.lower():
        fleet_models.append(model_name)

print(f"\nFleet models found: {len(fleet_models)}")
if fleet_models:
    for model in sorted(fleet_models)[:10]:
        model_obj = kb.models.get(model)
        print(f"  - {model:40} {f'({model_obj.model_label})' if model_obj and model_obj.model_label else ''}")
    if len(fleet_models) > 10:
        print(f"  ... and {len(fleet_models) - 10} more")

# Check for fleet fields
fleet_fields = []
for (model_name, field_name), field in kb.fields.items():
    if "fleet" in model_name.lower():
        fleet_fields.append((model_name, field_name))

print(f"\nFleet fields found: {len(fleet_fields)}")
if fleet_fields:
    # Show sample fields from first fleet model
    first_model = fleet_fields[0][0] if fleet_fields else None
    if first_model:
        print(f"\nSample fields from '{first_model}':")
        count = 0
        for (model_name, field_name), field in kb.fields.items():
            if model_name == first_model:
                print(f"  - {field_name:30} ({field.field_type})")
                count += 1
                if count >= 10:
                    break

# Check module registry
print("\n" + "-" * 80)
print("MODULE REGISTRY CHECK")
print("-" * 80)

registry = get_module_registry()
print("\nChecking if fleet is in module registry...")
for group in registry.get_all_groups():
    if "fleet" in group.name.lower() or "vehicle" in group.description.lower():
        print(f"\n✓ Found: {group.name}")
        print(f"  Display: {group.display_name}")
        print(f"  Description: {group.description}")
        print(f"  Models: {group.models[:5]}...")

# Check for other common Odoo modules
print("\n" + "-" * 80)
print("OTHER MODULE COVERAGE CHECK")
print("-" * 80)

modules_to_check = [
    "fleet",
    "maintenance",
    "quality",
    "mrp_plm",
    "event",
    "survey",
    "helpdesk",
    "field_service",
    "planning",
    "approvals",
    "documents",
    "sign",
    "website_slides",  # eLearning
    "appointment",
    "social",
    "marketing_automation"
]

print("\nChecking for common Odoo modules in knowledge base:")
for module_prefix in modules_to_check:
    count = sum(1 for m in kb.models.keys() if m.startswith(f"{module_prefix}."))
    if count > 0:
        print(f"  ✓ {module_prefix:20} - {count} models found")
    else:
        print(f"  ✗ {module_prefix:20} - NOT FOUND")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total models in knowledge base: {len(kb.models)}")
print(f"Total fields in knowledge base: {len(kb.fields)}")

# List all unique module prefixes
prefixes = set()
for model_name in kb.models.keys():
    if "." in model_name:
        prefix = model_name.split(".")[0]
        prefixes.add(prefix)

print(f"\nUnique module prefixes found: {len(prefixes)}")
print("Prefixes:", ", ".join(sorted(list(prefixes))[:20]) + "...")