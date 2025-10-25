# Export to odoo-migrate Guide

## Overview

This feature bridges **data-migrator's interactive cleanup** with **odoo-migrate's deterministic pipeline**.

### Workflow

```
1. Upload messy spreadsheet to data-migrator
   ↓
2. Auto-profile detects issues (spaces, formats, etc.)
   ↓
3. Configure mappings + transforms in UI
   ↓
4. Export to odoo-migrate format (transforms ALREADY applied!)
   ↓
5. Use odoo-migrate CLI for production deployment
```

## How to Use

### Step 1: Clean Data in data-migrator

1. Upload your spreadsheet via the web UI
2. Review auto-detected issues in the profiling dashboard
3. Configure field mappings (data-migrator suggests Odoo fields)
4. Apply transforms (trim, normalize phones, etc.)
5. Preview cleaned data

### Step 2: Export to odoo-migrate

**API Endpoint:**
```bash
POST /api/v1/datasets/{dataset_id}/export/odoo-migrate
```

**Response:** ZIP file containing:

```
dataset_123_odoo_migrate.zip
├── config/
│   ├── project.yml          # Project configuration
│   ├── ids.yml              # External ID patterns
│   ├── mappings/
│   │   └── res.partner.yml  # Field mappings (NO transforms!)
│   └── lookups/
│       └── tags.csv         # Lookup tables
└── data/
    └── raw/
        └── customers.csv    # CLEANED CSV (transforms already applied!)
```

**Preview Export (optional):**
```bash
GET /api/v1/datasets/{dataset_id}/export/odoo-migrate/preview
```

Returns metadata about what will be exported without generating the ZIP.

### Step 3: Use with odoo-migrate

1. **Extract the ZIP:**
   ```bash
   cd /path/to/odoo-migrate
   unzip dataset_123_odoo_migrate.zip
   ```

2. **Prepare source data:**
   ```bash
   odoo-migrate source prepare
   ```

3. **Transform (mapping only, data already clean!):**
   ```bash
   odoo-migrate transform execute config/mappings/res.partner.yml
   ```

4. **Validate:**
   ```bash
   odoo-migrate validate check
   ```

5. **Initialize run:**
   ```bash
   odoo-migrate load init --order "res.partner"
   ```

6. **Dry-run (test mode):**
   ```bash
   odoo-migrate load run RUN_ID \
     --url https://your-odoo.com \
     --db production \
     --username admin \
     --password secret \
     --test
   ```

7. **Execute actual load:**
   ```bash
   odoo-migrate load run RUN_ID \
     --url https://your-odoo.com \
     --db production \
     --username admin \
     --password secret
   ```

## Key Concepts

### ✅ Transforms Applied in Export

**Important:** The exported CSV files have **transforms already applied**!

**Example:**

**Before (source data):**
```csv
Email,Phone
  SALES@ACME.COM ,(555) 123-4567
```

**After export (data/raw/customers.csv):**
```csv
Email,Phone
sales@acme.com,+15551234567
```

**YAML mapping (config/mappings/res.partner.yml):**
```yaml
fields:
  email: { source: "Email" }     # NO transforms!
  phone: { source: "Phone" }     # NO transforms!
```

Why? Because transforms were applied during export!

### ✅ External ID Patterns

data-migrator detects unique keys (like `ref`, `code`, `customer_id`) and generates patterns:

```yaml
# config/ids.yml
default_namespace: migr
patterns:
  res.partner: "migr.partner.{ref}"
  sale.order: "migr.order.{order_number}"
```

This enables **idempotent loads** in odoo-migrate (safe to re-run).

### ✅ Version Control Ready

All exported configs are YAML/CSV - perfect for git:

```bash
git add config/
git commit -m "Add customer migration config from data-migrator"
git push
```

## Benefits

| Feature | data-migrator | odoo-migrate |
|---------|---------------|--------------|
| **Discovery** | ✅ Interactive UI | ❌ Manual inspection |
| **Profiling** | ✅ Auto-detect issues | ❌ None |
| **Field Mapping** | ✅ AI/fuzzy suggestions | ❌ Manual YAML |
| **Data Cleaning** | ✅ Visual transforms | ⚠️ Config-driven |
| **Preview** | ✅ Before/after view | ⚠️ Dry-run only |
| **Repeatability** | ❌ UI-based | ✅ Config-based |
| **Version Control** | ❌ Database | ✅ YAML files |
| **Idempotent Loads** | ⚠️ Limited | ✅ External IDs |
| **Production Deploy** | ❌ Manual | ✅ CLI automation |

**Best of Both Worlds:**
- Use data-migrator for **discovery & cleanup** (one-time)
- Use odoo-migrate for **execution & deployment** (repeatable)

## Example Workflow

### Scenario: Import 10,000 customer records

**Week 1: Discovery (data-migrator)**
```
1. Upload messy_customers.xlsx
2. Profiler shows:
   - 247 emails with spaces
   - 189 phone numbers in 3 formats
   - 42 records missing country codes
3. User applies transforms in UI
4. Preview looks good
5. Export to odoo-migrate
```

**Week 2: Testing (odoo-migrate)**
```
1. Extract export ZIP
2. Run validation: odoo-migrate validate check
3. Dry-run to UAT environment
4. Fix any issues by re-exporting from data-migrator
5. Commit final configs to git
```

**Week 3: Production (odoo-migrate)**
```
1. Pull configs from git
2. Run to production with --test first
3. Execute actual load
4. Verify in Odoo
5. Re-run safely if needed (idempotent!)
```

## Troubleshooting

### Export fails with "Dataset not found"

Check that the dataset has:
- At least one sheet
- At least one chosen mapping
- Source file is still accessible

### Exported YAML has no fields

Ensure mappings are marked as `chosen=True` and have `target_model` + `target_field` set.

### odoo-migrate validation fails

1. Check exported YAML structure matches odoo-migrate format
2. Run preview endpoint first to verify structure
3. Ensure external ID patterns don't conflict

### Transforms not working

**Remember:** Transforms are applied DURING export!

The YAML mapping should NOT have transform directives. If you see transforms in YAML, something is wrong with the export logic.

## Support

For issues:
1. Check logs in data-migrator backend
2. Use preview endpoint to debug export structure
3. Validate exported files with odoo-migrate CLI
4. Review odoo-migrate documentation at `/home/ben/Documents/GitHub/odoo-migrate/`
