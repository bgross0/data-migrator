# End-to-End Testing Guide
## data-migrator → odoo-migrate Integration

This guide walks through testing the complete export bridge integration.

## Prerequisites

- ✅ data-migrator backend running (port 8000)
- ✅ data-migrator frontend running (port 5173)
- ✅ PostgreSQL database initialized with migrations
- ✅ odoo-migrate installed at `/home/ben/Documents/GitHub/odoo-migrate`
- ✅ Sample CSV file with messy data

## Test Scenario: Customer Import

We'll test importing a messy customer CSV with:
- Dirty emails (spaces, mixed case)
- Inconsistent phone formats
- Tags that need splitting

### Step 1: Prepare Test Data

Create `test_customers_messy.csv`:

```csv
Company Name,Email Address,Phone,Tags,Customer Code
Acme Corp,  SALES@ACME.COM ,(555) 123-4567,VIP;Wholesale,ACME001
Beta Inc,contact@beta.com  ,555.987.6543,Premium,BETA002
Gamma LLC,INFO@GAMMA.ORG,+1-555-246-8135,VIP;Premium,GAMMA003
```

### Step 2: Upload to data-migrator

1. **Start backend:**
   ```bash
   cd /home/ben/Documents/GitHub/data-migrator/backend
   source venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start frontend:**
   ```bash
   cd /home/ben/Documents/GitHub/data-migrator/frontend
   npm run dev
   ```

3. **Upload via UI:**
   - Navigate to http://localhost:5173
   - Click "Upload Dataset"
   - Upload `test_customers_messy.csv`
   - Wait for profiling to complete

### Step 3: Configure Mappings in data-migrator

1. **View Dataset:**
   - Navigate to Dataset detail page
   - Click "Configure Mappings"

2. **Set Field Mappings:**
   - `Company Name` → `res.partner.name` (no transforms)
   - `Email Address` → `res.partner.email`
     - Add transform: `trim`
     - Add transform: `lowercase`
   - `Phone` → `res.partner.phone`
     - Add transform: `phone_normalize` (country: US)
   - `Customer Code` → `res.partner.ref` (no transforms)
   - `Tags` → `res.partner.category_id/id`
     - Add transform: `split` (delimiter: `;`)
     - Add transform: `map` (table: `tags`)

3. **Mark all mappings as "chosen"**

### Step 4: Export to odoo-migrate

1. **Using UI:**
   - Go back to Dataset detail page
   - Click "📦 Export to odoo-migrate" button
   - Wait for download (should get `dataset_1_odoo_migrate.zip`)

2. **Using API (alternative):**
   ```bash
   curl -X POST http://localhost:8888/api/v1/datasets/1/export/odoo-migrate \
     -o export.zip
   ```

3. **Preview first (optional):**
   ```bash
   curl http://localhost:8888/api/v1/datasets/1/export/odoo-migrate/preview | jq
   ```

### Step 5: Verify ZIP Contents

```bash
unzip -l dataset_1_odoo_migrate.zip
```

**Expected structure:**
```
config/project.yml
config/ids.yml
config/mappings/res.partner.yml
config/lookups/tags.csv
data/raw/res.partner.csv
```

### Step 6: Inspect Generated Files

**Check config/mappings/res.partner.yml:**

```yaml
model: res.partner
id: "migr.partner.{ref}"
unique_key: ["ref"]
fields:
  name: { source: "Company Name" }
  email: { source: "Email Address" }      # NO transforms!
  phone: { source: "Phone" }              # NO transforms!
  ref: { source: "Customer Code" }
  category_id/id: { source: "Tags" }      # NO transforms!
```

**Check config/lookups/tags.csv:**

```csv
source_key,external_id
Premium,migr.tags.Premium
VIP,migr.tags.VIP
Wholesale,migr.tags.Wholesale
```

**Check data/raw/res.partner.csv (CLEANED!):**

```csv
Company Name,Email Address,Phone,Tags,Customer Code
Acme Corp,sales@acme.com,+15551234567,VIP;Wholesale,ACME001
Beta Inc,contact@beta.com,+15559876543,Premium,BETA002
Gamma LLC,info@gamma.org,+15552468135,VIP;Premium,GAMMA003
```

☝️ **Notice:** Transforms are ALREADY APPLIED!
- Emails are lowercase and trimmed
- Phones are E.164 format
- Tags are still semicolon-separated (will be handled by odoo-migrate)

### Step 7: Extract to odoo-migrate

```bash
cd /home/ben/Documents/GitHub/odoo-migrate
unzip -o /path/to/dataset_1_odoo_migrate.zip
```

### Step 8: Run odoo-migrate Pipeline

**Step 8.1: Prepare Source Data**

```bash
python -m tools.cli source prepare
```

Expected output:
```
📥 Preparing source data from data/raw
Found 1 CSV file(s)

🔍 Validating CSV structure...
  ✓ res.partner.csv

⚙️  Converting to JSONL format...
  Processing res.partner.csv...
    ✓ 3 rows → res.partner.jsonl

✅ Preparation complete!
  Files processed: 1
  Total rows: 3
```

**Step 8.2: Execute Transformation**

```bash
python -m tools.cli transform execute config/mappings/res.partner.yml
```

Expected output:
```
🔄 Transforming data for model: res.partner
📄 Input: data/staging/res.partner.jsonl
📄 Output: data/payload/res.partner.csv
📂 Lookups: config/lookups

⚙️  Processing records...

✅ Transformation complete!
  Processed: 3
  Errors: 0
  Skipped: 0
```

**Step 8.3: Validate Payload**

```bash
python -m tools.cli validate check
```

Expected output:
```
🔍 Starting validation...

📋 Validating configuration files...
  ✓ project.yml
  ✓ ids.yml
  ✓ res.partner.yml

📦 Validating payload files...
  ✓ res.partner.csv

🔗 Validating cross-references...
  ✓ All references valid

✅ All validation checks passed (5 checks)
```

**Step 8.4: Initialize Run**

```bash
python -m tools.cli load init \
  --order "res.partner" \
  --run-id test-run-001
```

Expected output:
```
🔧 Initializing load run...

✓ Using order from CLI: 1 models
✓ Created manifest: runs/test-run-001/manifest.json
✓ Created order file: runs/test-run-001/order.txt

✅ Run initialized: test-run-001

Load order (1 models):
  1. res.partner
```

**Step 8.5: Dry Run (Test Mode)**

```bash
python -m tools.cli load run test-run-001 \
  --url https://your-odoo-test.com \
  --db test_db \
  --username admin \
  --password your_password \
  --test
```

Expected output:
```
🚀 Starting test load for run: test-run-001
🔌 Target: https://your-odoo-test.com database 'test_db'

Loading res.partner...

✅ Load test completed: completed

Summary:
  Loaded:  3
  Errors:  0
  Skipped: 0

Per-model breakdown:
  ✓ res.partner: 3 loaded
```

**Step 8.6: Actual Load (Production)**

```bash
python -m tools.cli load run test-run-001 \
  --url https://your-odoo.com \
  --db production \
  --username admin \
  --password your_password
```

## Validation Checklist

### ✅ Export Phase (data-migrator)

- [ ] All chosen mappings included in YAML
- [ ] No transforms in YAML (data already clean)
- [ ] External ID pattern uses `ref` field
- [ ] Lookup table generated for tags
- [ ] CSV has cleaned data (emails lowercase, phones E.164)

### ✅ Prepare Phase (odoo-migrate)

- [ ] CSV converted to JSONL without errors
- [ ] Row count matches source CSV

### ✅ Transform Phase (odoo-migrate)

- [ ] Transformation completes without errors
- [ ] External IDs generated correctly
- [ ] Lookup table applied (tags mapped to external IDs)

### ✅ Validate Phase (odoo-migrate)

- [ ] Config validation passes
- [ ] Payload CSV validation passes
- [ ] No cross-reference errors

### ✅ Load Phase (odoo-migrate)

- [ ] Dry run succeeds
- [ ] Actual load creates records in Odoo
- [ ] Can re-run load (idempotent check)
- [ ] Records have correct external IDs

## Common Issues & Solutions

### Issue: Export validation fails

**Error:** `No mappings marked as chosen`

**Solution:** Go to mapping UI and mark at least one mapping as chosen

---

### Issue: Transform application fails

**Error:** Column not found in YAML

**Solution:** Check that source column name in YAML matches CSV header exactly

---

### Issue: Lookup table empty

**Error:** No lookup CSV generated

**Solution:**
1. Check that transform includes both `split` and `map`
2. Verify `map` transform has `table` parameter set
3. Check source data has values in that column

---

### Issue: odoo-migrate validation fails

**Error:** Invalid field in mapping

**Solution:** Check that Odoo model has the field you're mapping to

---

### Issue: External IDs conflict

**Error:** Duplicate external ID

**Solution:**
1. Check unique_key is truly unique in source data
2. Verify ref field has no duplicates
3. Clean duplicates in source CSV and re-export

## Success Criteria

✅ Export generates valid ZIP structure
✅ YAML configs match odoo-migrate format
✅ Exported CSVs have transforms applied (clean data)
✅ YAML mappings have NO transform directives
✅ Lookup tables generated correctly
✅ odoo-migrate validate check passes
✅ Can load data to Odoo without errors
✅ Re-running load is idempotent (no duplicates)

## Next Steps After Success

1. **Version Control:**
   ```bash
   cd /home/ben/Documents/GitHub/odoo-migrate
   git add config/ data/
   git commit -m "Add customer migration config from data-migrator"
   git push
   ```

2. **Production Deployment:**
   - Pull configs from git on production server
   - Run odoo-migrate pipeline against production Odoo
   - Verify data in Odoo UI

3. **Iteration:**
   - If issues found, go back to data-migrator
   - Adjust mappings/transforms
   - Re-export and validate
   - Configs are now version-controlled!

## Reporting Results

Please report test results with:

**✅ SUCCESS:**
- All validation checks passed
- Data loaded to Odoo correctly
- Idempotent re-run works

**❌ FAILURE:**
- Which step failed (export, prepare, transform, validate, load)
- Error message
- Contents of generated files (YAML, CSV)
- Logs from odoo-migrate

This will help us debug and fix any integration issues!
