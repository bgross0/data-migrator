# Missing Models in Registry - Action Required

## Issue Summary

The registry file `backend/registry/odoo.yaml` has **7 models** listed in `import_order` but **without field definitions**. This causes template instantiation to fail.

## Missing Models

The following models are in `import_order` but lack definitions:

1. **res.partner.industry** (line 6 of import_order)
2. **crm.team** (line 14)
3. **utm.source** (line 15)
4. **utm.medium** (line 16)
5. **crm.lost.reason** (line 18)
6. **mail.activity** (line 20)
7. **project.project** (line 21)

## Impact on Templates

### ❌ Broken Templates (3 of 5):

**sales_crm.json** - References 4 missing models:
- crm.team
- utm.source
- utm.medium
- crm.lost.reason

**projects.json** - References 1 missing model:
- project.project

**complete_migration.json** - References ALL 7 missing models

### ✅ Working Templates (2 of 5):
- accounting.json
- essential_setup.json

## Recommended Actions

### Option 1: Remove from import_order (Quick Fix)

If these models are not needed for your use case:

```yaml
# Edit backend/registry/odoo.yaml and remove these lines from import_order:
- res.partner.industry
- crm.team
- utm.source
- utm.medium
- crm.lost.reason
- mail.activity
- project.project
```

### Option 2: Add Model Definitions (Complete Fix)

If you need these models, add their field definitions. Example template:

```yaml
crm.team:
  csv: export_crm_team.csv
  id_template: "team_{slug(name)}"
  headers: ["id", "name", "active"]
  fields:
    id:
      derived: true
    name:
      required: true
      type: string
    active:
      type: bool
      default: true

utm.source:
  csv: export_utm_source.csv
  id_template: "utm_source_{slug(name)}"
  headers: ["id", "name"]
  fields:
    id:
      derived: true
    name:
      required: true
      type: string

utm.medium:
  csv: export_utm_medium.csv
  id_template: "utm_medium_{slug(name)}"
  headers: ["id", "name"]
  fields:
    id:
      derived: true
    name:
      required: true
      type: string

crm.lost.reason:
  csv: export_crm_lost_reason.csv
  id_template: "lost_reason_{slug(name)}"
  headers: ["id", "name", "active"]
  fields:
    id:
      derived: true
    name:
      required: true
      type: string
    active:
      type: bool
      default: true

project.project:
  csv: export_project_project.csv
  id_template: "project_{slug(name)}"
  headers: ["id", "name", "active", "user_id", "user_id/id", "partner_id", "partner_id/id"]
  fields:
    id:
      derived: true
    name:
      required: true
      type: string
    active:
      type: bool
      default: true
    user_id:
      type: m2o
      target: res.users
    user_id/id:
      type: m2o
      target: res.users
      external_field: user_id
    partner_id:
      type: m2o
      target: res.partner
    partner_id/id:
      type: m2o
      target: res.partner
      external_field: partner_id

mail.activity:
  csv: export_mail_activity.csv
  id_template: "activity_{slug(summary)}"
  headers: ["id", "summary", "activity_type_id", "activity_type_id/id", "res_model", "res_id", "user_id", "user_id/id", "date_deadline"]
  fields:
    id:
      derived: true
    summary:
      type: string
    activity_type_id:
      type: m2o
      target: mail.activity.type
    activity_type_id/id:
      type: m2o
      target: mail.activity.type
      external_field: activity_type_id
    res_model:
      type: string
    res_id:
      type: int
    user_id:
      type: m2o
      target: res.users
    user_id/id:
      type: m2o
      target: res.users
      external_field: user_id
    date_deadline:
      type: date
      transform: normalize_date_any

res.partner.industry:
  csv: export_res_partner_industry.csv
  id_template: "industry_{slug(name)}"
  headers: ["id", "name", "full_name", "active"]
  fields:
    id:
      derived: true
    name:
      required: true
      type: string
    full_name:
      type: string
    active:
      type: bool
      default: true
```

### Option 3: Use Existing Odoo Data (Hybrid)

If these models reference data already in Odoo (not being imported):
1. Remove from `import_order`
2. Keep field references that use them (they'll resolve to existing Odoo records)

## Next Steps

1. Decide which option fits your use case
2. Make the corresponding changes to `backend/registry/odoo.yaml`
3. Test template instantiation again

## Related Files
- Registry: `backend/registry/odoo.yaml`
- Affected templates: `backend/templates/{sales_crm,projects,complete_migration}.json`
- Template service: `backend/app/services/template_service.py`
