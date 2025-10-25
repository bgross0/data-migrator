# Validator Checklist

**Purpose**: Pre-load and post-load assertions to ensure data quality and referential integrity.

## Pre-Load Validators (Run Before Each Batch)

### Batch 1: System Config
**Goal**: Ensure base system entities exist

- [ ] `res.company` records have unique names
- [ ] `res.users` records have unique `login` values
- [ ] `res.country` and `res.country.state` are pre-seeded (Odoo default)
- [ ] All `res.users` have valid email addresses

**Action on Failure**: ABORT (system config must be clean)

---

### Batch 2: Taxonomies & Catalogs
**Goal**: Ensure controlled vocabularies are clean and unique

- [ ] `crm.stage` names unique per team (or global if no team)
- [ ] `crm.lost.reason` names unique globally
- [ ] `crm.tag` names unique per company (after normalization: lower + trim)
- [ ] `res.partner.category` names unique globally
- [ ] `utm.source` / `utm.medium` / `utm.campaign` names unique (after normalization)
- [ ] `product.template` has unique `default_code` (SKU) if provided
- [ ] `product.product` has unique `default_code` (SKU) if provided
- [ ] All `product.product` records have valid `product_tmpl_id`

**Action on Failure**: QUARANTINE conflicting records, continue with valid ones

---

### Batch 3: Partners
**Goal**: Ensure all foreign key references resolve

**Companies (`is_company=True`):**
- [ ] All `country_id` references exist in `res.country`
- [ ] All `state_id` references exist in `res.country.state` AND match `country_id`
- [ ] All `category_id` (m2m) references exist in `res.partner.category`
- [ ] All `company_id` references exist in `res.company`
- [ ] `vat` is unique per company (if provided)
- [ ] Email addresses pass validation (TypeRegistry.parse_email)
- [ ] Phone numbers pass validation (TypeRegistry.parse_phone)

**Contacts (`is_company=False`):**
- [ ] All `parent_id` references resolve to existing companies (`is_company=True`)
- [ ] All `country_id` / `state_id` / `category_id` / `company_id` resolve (same as companies)
- [ ] No circular `parent_id` references
- [ ] Each contact has at least ONE of: email, phone, mobile

**Natural Key Uniqueness:**
- [ ] No duplicate `vat` values (within company scope)
- [ ] No duplicate (`name` + `street` + `city` + `state` + `country`) combos for companies
- [ ] No duplicate (`parent_id` + `name` + `email`) combos for contacts

**Action on Failure**: QUARANTINE record with missing FK or duplicate natural key

---

### Batch 4: CRM Leads
**Goal**: Ensure all lead relationships resolve

- [ ] All `partner_id` references exist in `res.partner`
- [ ] All `user_id` references exist in `res.users`
- [ ] All `team_id` references exist in `crm.team` (if provided)
- [ ] All `stage_id` references exist in `crm.stage` (REQUIRED)
- [ ] All `lost_reason_id` references exist in `crm.lost.reason` (if provided)
- [ ] All `tag_ids` (m2m) references exist in `crm.tag`
- [ ] All `utm_source_id` / `utm_medium_id` / `utm_campaign_id` references exist OR policy allows creation
- [ ] All `company_id` references exist in `res.company`

**Business Rules:**
- [ ] If `lost_reason_id` is set, then `stage_id` must point to a lost stage (`fold=True` or custom lost indicator)
- [ ] `probability` is between 0-100
- [ ] `expected_revenue` ≥ 0
- [ ] Each lead has at least ONE of: `partner_id`, `contact_name`, `email_from`

**Natural Key Uniqueness:**
- [ ] No duplicate external IDs (if provided)
- [ ] No duplicate (`partner_id` + `name` + `create_date`[±3d]) combos

**Action on Failure**: QUARANTINE record with missing FK or invalid business rule

---

### Batch 5: Polymorphic Children (Activities & Messages)
**Goal**: Ensure polymorphic links resolve

**mail.activity:**
- [ ] All `user_id` references exist in `res.users`
- [ ] All `activity_type_id` references exist in `mail.activity.type`
- [ ] All (`res_model`, `res_id`) pairs resolve:
  - If `res_model='crm.lead'`, `res_id` exists in `crm.lead`
  - If `res_model='res.partner'`, `res_id` exists in `res.partner`
- [ ] `date_deadline` is a valid date (not in past beyond threshold, e.g., >90 days old)

**mail.message:**
- [ ] All `author_id` references exist in `res.partner` (if provided)
- [ ] All (`model`, `res_id`) pairs resolve (same logic as activities)
- [ ] `date` is a valid datetime

**Anchor Confidence:**
- [ ] If <90% of rows successfully resolved anchors → WARN and require user confirmation
- [ ] If ≥10% of rows have ambiguous anchors (could be lead OR partner) → REQUIRE explicit rule

**Action on Failure**: QUARANTINE record with unresolvable polymorphic link

---

### Batch 6: Sales Orders
**Goal**: Ensure all order relationships resolve

**sale.order:**
- [ ] All `partner_id` references exist in `res.partner` (REQUIRED)
- [ ] All `user_id` references exist in `res.users`
- [ ] All `company_id` references exist in `res.company`
- [ ] `date_order` is a valid datetime
- [ ] Each order has at least ONE `order_line`

**sale.order.line:**
- [ ] All `product_id` references exist in `product.product` (REQUIRED)
- [ ] `product_uom_qty` > 0
- [ ] `price_unit` ≥ 0

**Natural Key Uniqueness:**
- [ ] No duplicate (`partner_id` + `name`) if `name` is provided by source

**Action on Failure**: QUARANTINE order with missing FK or invalid lines

---

### Batch 7: Projects & Tasks
**Goal**: Ensure all project relationships resolve

**project.project:**
- [ ] All `partner_id` references exist in `res.partner` (if provided)
- [ ] All `user_id` references exist in `res.users` (if provided)
- [ ] All `company_id` references exist in `res.company`

**project.task:**
- [ ] All `project_id` references exist in `project.project` (REQUIRED)
- [ ] All `user_ids` (m2m) references exist in `res.users`
- [ ] `date_deadline` is a valid date (if provided)

**Action on Failure**: QUARANTINE task with missing project

---

## Post-Load Validators (Run After Each Batch)

### Record Count Reconciliation
**Goal**: Ensure no records were silently dropped

For each model in batch:
- [ ] Odoo record count == Canonical table count (from staging)
- [ ] Created + Matched + Quarantined == Total source rows

**Example:**
```
crm.lead:
  Source rows: 1,250
  Created in Odoo: 1,100
  Matched (duplicates): 120
  Quarantined: 30
  Total accounted: 1,250 ✓
```

**Action on Failure**: HALT and investigate missing records

---

### Sample Integrity Checks (50 Random Records)

**Batch 3: Partners**
- [ ] 50 random partners with `state_id` → all have valid `country_id` that matches state's country
- [ ] 50 random contacts with `parent_id` → all parents exist and are companies
- [ ] 50 random partners with email → all emails pass validation
- [ ] 50 random partners with phone → all phones in E.164 format

**Batch 4: Leads**
- [ ] 50 random leads with `partner_id` → all partners exist
- [ ] 50 random leads with `stage_id` → all stages exist
- [ ] 50 random leads with `user_id` → all users exist
- [ ] 50 random lost leads → all have valid `lost_reason_id` AND lost stage
- [ ] 50 random leads with tags → all tags exist (m2m resolved)

**Batch 5: Activities & Messages**
- [ ] 50 random activities → all (`res_model`, `res_id`) pairs resolve to actual records
- [ ] 50 random messages → all (`model`, `res_id`) pairs resolve to actual records
- [ ] 50 random activities → all `user_id` and `activity_type_id` exist

**Batch 6: Sales Orders**
- [ ] 50 random orders → all have `partner_id` that exists
- [ ] 50 random orders → all have ≥1 `order_line`
- [ ] 50 random order lines → all have `product_id` that exists

**Batch 7: Projects & Tasks**
- [ ] 50 random tasks → all have `project_id` that exists
- [ ] 50 random tasks with assignees → all `user_ids` exist

**Action on Failure**: WARN (log specific failures) and flag for manual review

---

### Orphan Detection
**Goal**: Ensure no dangling foreign keys

- [ ] No `mail.activity` records with (`res_model`, `res_id`) pointing to non-existent records
- [ ] No `mail.message` records with (`model`, `res_id`) pointing to non-existent records
- [ ] No `sale.order.line` records with `order_id` pointing to non-existent orders
- [ ] No `project.task` records with `project_id` pointing to non-existent projects
- [ ] No `res.partner` (contacts) with `parent_id` pointing to non-existent companies

**Query Template:**
```sql
-- Example: Check for orphaned activities
SELECT COUNT(*) FROM mail_activity a
LEFT JOIN crm_lead l ON (a.res_model = 'crm.lead' AND a.res_id = l.id)
LEFT JOIN res_partner p ON (a.res_model = 'res.partner' AND a.res_id = p.id)
WHERE l.id IS NULL AND p.id IS NULL;
-- Expected: 0
```

**Action on Failure**: CRITICAL ERROR - data corruption detected, rollback batch

---

### Uniqueness Constraints (Per Batch)

**Batch 2: Taxonomies**
- [ ] No duplicate `crm.stage.name` per team
- [ ] No duplicate `crm.tag.name` per company (normalized)
- [ ] No duplicate `utm.source.name` (normalized)

**Batch 3: Partners**
- [ ] No duplicate `vat` per company
- [ ] No duplicate natural keys (company: name+address, contact: parent+name+email)

**Batch 4: Leads**
- [ ] No duplicate external IDs
- [ ] No duplicate natural keys (partner+name+date)

**Action on Failure**: WARN (duplicates detected, idempotency ledger should prevent this)

---

## Failure Action Matrix

| Severity | Action | When to Use |
|----------|--------|-------------|
| ABORT | Stop entire import, rollback all | System config invalid (Batch 1) |
| CRITICAL | Rollback current batch, halt | Data corruption (orphans detected) |
| QUARANTINE | Move record to review queue, continue | Missing FK, invalid business rule |
| WARN | Log and continue | Soft issues (sample checks, duplicates caught by ledger) |

---

## Quarantine Table Schema

```sql
CREATE TABLE quarantine_records (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR NOT NULL,
    source_table VARCHAR NOT NULL,
    source_pk VARCHAR NOT NULL,
    target_model VARCHAR NOT NULL,
    reason VARCHAR NOT NULL,  -- "missing_fk:partner_id", "duplicate_natural_key", etc.
    source_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolution VARCHAR  -- "fixed_and_loaded", "discarded", "pending"
);
```

**Review Process:**
1. Export quarantine records to CSV
2. Data steward fixes source data OR manually creates missing FKs
3. Re-run import with `--resume-from-quarantine` flag
4. System retries quarantined records

---

## Validator Implementation Checklist

- [ ] Create `Validator` base class with `validate()` method
- [ ] Implement `PreLoadValidator` subclass for each batch
- [ ] Implement `PostLoadValidator` subclass for each batch
- [ ] Create `QuarantineService` to manage quarantine table
- [ ] Add `--strict` flag to fail on first QUARANTINE (vs continue)
- [ ] Add `--skip-post-load-checks` flag for fast testing (NOT for production)
- [ ] Integrate validators into `DependencyAwareLoader`
- [ ] Add validator results to import summary dashboard

---

**Last Updated**: 2025-10-24
**Owned By**: Data Platform Team
