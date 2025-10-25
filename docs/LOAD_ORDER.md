# Load Order + Dependency Matrix

**Purpose**: Define safe topological load order for Odoo entities to prevent foreign key constraint violations.

## Load Order (Sequential Batches)

### Batch 1: System Config (no dependencies)
1. `res.company` - Multi-company entities
2. `res.users` - System users (creates res.partner automatically)
3. `res.country` - Geographic reference (pre-seeded by Odoo)
4. `res.country.state` - Geographic reference (pre-seeded by Odoo)

**Why first**: All other entities reference these. Must exist before loading business data.

---

### Batch 2: Taxonomies & Catalogs (minimal dependencies)
5. `crm.stage` - Pipeline stages
6. `crm.lost.reason` - Lost reasons
7. `crm.tag` - CRM tags
8. `res.partner.category` - Partner categories
9. `utm.source` - Marketing source
10. `utm.medium` - Marketing medium
11. `utm.campaign` - Marketing campaigns
12. `mail.activity.type` - Activity types (Call, Email, Meeting, To-Do)
13. `product.template` - Product catalog (templates)
14. `product.product` - Product catalog (variants)

**Why second**: Pure catalogs with no business data dependencies. Can load in parallel within this batch.

---

### Batch 3: Partners (depends on Batch 1-2)
15. `res.partner` (companies, `is_company=True`) - Companies first
16. `res.partner` (contacts, `is_company=False`, with `parent_id`) - Contacts second

**Why third**: Contacts depend on companies via `parent_id`. All later entities reference partners.

**Dependency**:
- `parent_id` → res.partner (company)
- `state_id` → res.country.state
- `country_id` → res.country
- `category_id` → res.partner.category (m2m)
- `company_id` → res.company

---

### Batch 4: CRM Leads (depends on Batch 1-3)
17. `crm.lead`

**Why fourth**: Leads reference partners, stages, users, UTM values.

**Dependency**:
- `partner_id` → res.partner
- `user_id` → res.users
- `stage_id` → crm.stage
- `lost_reason_id` → crm.lost.reason
- `tag_ids` → crm.tag (m2m)
- `utm_source_id` → utm.source
- `utm_medium_id` → utm.medium
- `utm_campaign_id` → utm.campaign
- `company_id` → res.company

---

### Batch 5: Polymorphic Children (depends on Batch 4)
18. `mail.activity` - Structured to-dos
19. `mail.message` - Chatter logs

**Why fifth**: These link polymorphically to leads/partners (created in previous batches).

**Dependency (polymorphic)**:
- `res_model` + `res_id` → crm.lead OR res.partner
- `user_id` → res.users
- `activity_type_id` → mail.activity.type
- `author_id` → res.partner

---

### Batch 6: Sales (depends on Batch 3-4)
20. `sale.order`
21. `sale.order.line` (nested o2m, created with order)

**Why sixth**: Orders reference partners and products.

**Dependency**:
- `partner_id` → res.partner
- `user_id` → res.users
- `company_id` → res.company
- `order_line.product_id` → product.product

---

### Batch 7: Projects (depends on Batch 3)
22. `project.project`
23. `project.task`

**Why seventh**: Projects reference partners; tasks reference projects.

**Dependency**:
- `partner_id` → res.partner
- `user_id` / `user_ids` → res.users
- `company_id` → res.company
- `task.project_id` → project.project

---

## Dependency Matrix (Quick Reference)

| Model | Depends On | Batch |
|-------|------------|-------|
| res.company | (none) | 1 |
| res.users | (auto-creates res.partner) | 1 |
| res.country | (pre-seeded) | 1 |
| res.country.state | res.country | 1 |
| crm.stage | (none) | 2 |
| crm.lost.reason | (none) | 2 |
| crm.tag | (none) | 2 |
| res.partner.category | (none, tree via parent_id) | 2 |
| utm.source | (none) | 2 |
| utm.medium | (none) | 2 |
| utm.campaign | (none) | 2 |
| mail.activity.type | (none, pre-seeded) | 2 |
| product.template | (none) | 2 |
| product.product | product.template | 2 |
| res.partner (company) | res.country, res.country.state, res.partner.category | 3 |
| res.partner (contact) | res.partner (company via parent_id) | 3 |
| crm.lead | res.partner, res.users, crm.stage, crm.lost.reason, crm.tag, utm.* | 4 |
| mail.activity | res.users, mail.activity.type, polymorphic(crm.lead, res.partner) | 5 |
| mail.message | res.partner (author), polymorphic(crm.lead, res.partner) | 5 |
| sale.order | res.partner, res.users | 6 |
| sale.order.line | sale.order, product.product | 6 |
| project.project | res.partner, res.users | 7 |
| project.task | project.project, res.users | 7 |

---

## Load Strategy

### Sequential Batches
Load batches in strict order (1 → 2 → 3 → ... → 7). Never proceed to next batch until current batch is 100% complete.

### Parallel Within Batch
Entities within the same batch can be loaded in parallel since they have no inter-dependencies **within that batch**.

**Example**: All taxonomies (Batch 2) can load concurrently.

### Retry Logic
- **Transient failures**: Retry up to 3 times with exponential backoff
- **Constraint violations**: Quarantine record and continue (log as error)
- **Missing foreign keys**: Quarantine record (pre-load validation should catch this)

### Rollback Strategy
- Rollback **per batch** on critical failure
- Never cross-contaminate: dims (Batch 1-2) vs facts (Batch 3+)
- Keep ledger intact even on rollback for audit trail

---

## Validators (Pre-Load)

Before starting each batch, assert:

1. **Batch 1**: No validation needed (system config)
2. **Batch 2**: All taxonomy names unique within scope (e.g., crm.stage.name unique per team)
3. **Batch 3**:
   - All `parent_id` references resolve to existing companies
   - All `state_id` / `country_id` resolve
   - All `category_id` values exist (m2m)
4. **Batch 4**:
   - All `partner_id` references resolve
   - All `stage_id` references resolve
   - All `user_id` references resolve
   - All UTM references resolve (or policy allows creation)
   - Lost leads have valid `lost_reason_id`
5. **Batch 5**:
   - All polymorphic `(res_model, res_id)` pairs resolve
   - All `user_id` / `author_id` references resolve
6. **Batch 6**:
   - All `partner_id` references resolve
   - All `order_line.product_id` references resolve
7. **Batch 7**:
   - All `project.partner_id` references resolve
   - All `task.project_id` references resolve

---

## Validators (Post-Load)

After completing each batch:

1. **Record count reconciliation**: Odoo count == canonical table count
2. **Sample integrity checks**:
   - Batch 3: 50 random partners have valid state/country
   - Batch 4: 50 random leads have valid partner/stage/user
   - Batch 5: 50 random activities have valid polymorphic links
   - Batch 6: 50 random orders have valid partner and ≥1 line
   - Batch 7: 50 random tasks have valid project
3. **Orphan detection**: No dangling foreign keys (e.g., `mail.activity.res_id` points to non-existent lead)

---

## Critical Path (MVP)

If time-constrained, ship in this order:

1. **Week 1**: Batch 1-3 (System + Taxonomies + Partners)
2. **Week 2**: Batch 4-5 (Leads + Activities/Messages)
3. **Week 3-4**: Batch 6-7 (Sales + Projects) - Optional for CRM-only migration

**Rationale**: Core CRM pipeline (leads + partners + activities) is non-negotiable. Sales/Projects can iterate post-MVP.

---

**Last Updated**: 2025-10-24
**Owned By**: Data Platform Team
