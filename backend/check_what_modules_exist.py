"""
Check what Odoo modules ARE actually in the knowledge base.
"""
import sys
from pathlib import Path
from collections import Counter

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.field_mapper.core.knowledge_base import OdooKnowledgeBase

print("Loading knowledge base...")
kb = OdooKnowledgeBase(dictionary_path="/home/ben/Documents/GitHub/data-migrator/odoo-dictionary")
kb.load_from_dictionary()

print("\n" + "=" * 80)
print("MODULES ACTUALLY IN KNOWLEDGE BASE")
print("=" * 80)

# Count models by module prefix
module_counter = Counter()
for model_name in kb.models.keys():
    if "." in model_name:
        prefix = model_name.split(".")[0]
        module_counter[prefix] += 1

print(f"\nTotal unique module prefixes: {len(module_counter)}")
print(f"Total models: {sum(module_counter.values())}")

print("\n" + "-" * 80)
print("Module prefixes by model count:")
print("-" * 80)

for module, count in module_counter.most_common():
    print(f"  {module:25} - {count:3} models")

print("\n" + "-" * 80)
print("MAJOR MODULES THAT ARE MISSING:")
print("-" * 80)

missing_modules = [
    "fleet - Vehicle fleet management",
    "maintenance - Equipment maintenance",
    "quality - Quality control",
    "event - Event management",
    "survey - Surveys and forms",
    "helpdesk - Ticket management",
    "planning - Resource planning",
    "approvals - Approval workflows",
    "documents - Document management",
    "sign - Document signing",
    "website_slides - eLearning",
    "appointment - Appointment booking",
    "social - Social media",
    "marketing_automation - Marketing campaigns",
    "field_service - Field service",
    "mrp_plm - Product lifecycle management",
    "estate - Real estate",
    "subscriptions - Recurring billing",
    "timesheet_grid - Timesheet grid view",
    "fsm - Field service management",
    "iot - Internet of Things",
    "voip - Voice over IP",
    "knowledge - Knowledge base",
    "website_forum - Forum/Community",
    "website_blog - Blog",
    "website_event - Event website",
    "website_hr_recruitment - Job board",
    "l10n_* - Country-specific localization",
]

print("\nMajor Odoo modules/apps NOT in our knowledge base:")
for module in missing_modules:
    print(f"  ✗ {module}")

print("\n" + "=" * 80)
print("IMPLICATIONS:")
print("=" * 80)
print("""
The field mapper is limited to ONLY these core modules:
- Sales & CRM
- Accounting & Finance
- Contacts & Partners
- Products & Inventory (basic)
- Purchase
- HR (basic)
- Projects
- Manufacturing (MRP)
- Website (basic)
- POS

It CANNOT map fields for:
- Fleet management data
- Maintenance/asset data
- Quality control data
- Event management
- Surveys/forms
- Helpdesk tickets
- Document management
- eLearning courses
- Appointments
- Field service
- Real estate
- Subscriptions
- And many more specialized modules

This is a SIGNIFICANT limitation for real-world usage.
""")