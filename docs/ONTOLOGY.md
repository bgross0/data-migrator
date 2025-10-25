# Data Migrator Ontology

**Purpose**: Authoritative semantic map of Odoo entities we ingest, transform, and load.

## Core Entities

### 1. Party (res.partner)

**Definition**: Any legal or natural person with whom we do business. Can be a company (parent) or contact (person, child of company).

**Key Attributes**:
- `is_company` (boolean): Company vs person
- `parent_id` (m2o → res.partner): Company for contacts
- `name` (string, required)
- `vat` (string): Tax ID
- `email`, `phone`, `mobile`
- `street`, `street2`, `city`, `state_id` (m2o → res.country.state), `country_id` (m2o → res.country), `zip`
- `type` (selection): contact, invoice, delivery, other
- `category_id` (m2m → res.partner.category): Tags for partners
- `company_id` (m2o → res.company): Multi-company scope

**Natural Key**: `vat` OR (`name` + `street` + `city` + `state` + `country`)
**Cardinality**: 1 company → N contacts (via parent_id)

---

### 2. Lead/Opportunity (crm.lead)

**Definition**: Sales pipeline entry representing potential business. Progresses through stages until won/lost.

**Key Attributes**:
- `name` (string, required): Lead title
- `partner_id` (m2o → res.partner): Associated company
- `contact_name` (string): Contact name (fallback if no partner)
- `email_from`, `phone`
- `user_id` (m2o → res.users): Salesperson/owner
- `team_id` (m2o → crm.team): Sales team
- `stage_id` (m2o → crm.stage, required): Current pipeline stage
- `tag_ids` (m2m → crm.tag): Categorization tags
- `lost_reason_id` (m2o → crm.lost.reason): Why lost (if applicable)
- `expected_revenue` (float), `probability` (float)
- `utm_source_id`, `utm_medium_id`, `utm_campaign_id` (m2o → utm.*): Attribution
- `company_id` (m2o → res.company)

**Natural Key**: external_id OR (`partner_id` + `name` + `create_date`[±3d])
**Cardinality**: N leads → 1 partner, 1 stage, 1 user; N↔N tags

---

### 3. User/Owner (res.users)

**Definition**: Odoo users who own/manage leads, activities, and records.

**Key Attributes**:
- `name` (string, required)
- `login` (string, required, unique)
- `email`
- `partner_id` (m2o → res.partner): Underlying contact record

**Natural Key**: `login`
**Resolution Policy**: lookup_only (never auto-create users)

---

### 4. Activity (mail.activity)

**Definition**: Structured to-do item linked polymorphically to any record (lead, partner, etc.).

**Key Attributes**:
- `res_model` (string, required): Target model (e.g., "crm.lead")
- `res_id` (integer, required): Target record ID
- `activity_type_id` (m2o → mail.activity.type): Call, Email, Meeting, To-Do
- `user_id` (m2o → res.users): Assignee
- `date_deadline` (date, required)
- `summary` (string), `note` (text)

**Natural Key**: (`res_model` + `res_id` + `activity_type_id` + `date_deadline` + hash(`note`))
**Cardinality**: N activities → 1 parent record (polymorphic)

---

### 5. Interaction Log (mail.message)

**Definition**: Unstructured chatter entry (notes, emails, system messages) on any record.

**Key Attributes**:
- `model` (string), `res_id` (integer): Polymorphic link
- `subject` (string), `body` (html)
- `message_type` (selection): email, comment, notification
- `author_id` (m2o → res.partner)
- `date`

**Natural Key**: external message_id OR (`model` + `res_id` + `date`[±1m] + `author_id` + hash(`subject`+`body`))
**Cardinality**: N messages → 1 parent record (polymorphic)

---

### 6. Marketing Attribution (utm.source / utm.medium / utm.campaign)

**Definition**: Google Analytics–style tracking of lead sources.

**Key Attributes**:
- `name` (string, required)

**Natural Key**: lower(trim(`name`))
**Resolution Policy**: suggest_only (review before creating; flip to lookup_only post-stabilization)

---

### 7. Products/Services (product.template / product.product)

**Definition**: Catalog of sellable items.

**Key Attributes** (template):
- `name` (string, required)
- `type` (selection): consu, service, product
- `list_price` (float)

**Natural Key**: (`default_code`) OR (`name` + `type`)
**Cardinality**: 1 template → N variants (product.product)

---

### 8. Quote/Order (sale.order / sale.order.line)

**Definition**: Sales order with line items.

**Key Attributes** (order):
- `name` (string, sequence): Order reference
- `partner_id` (m2o → res.partner, required)
- `user_id` (m2o → res.users): Salesperson
- `date_order` (datetime)
- `state` (selection): draft, sent, sale, done, cancel
- `order_line` (o2m → sale.order.line)

**Key Attributes** (line):
- `order_id` (m2o → sale.order)
- `product_id` (m2o → product.product)
- `product_uom_qty` (float), `price_unit` (float)

**Natural Key** (order): external_id OR (`partner_id` + `name`)
**Cardinality**: 1 order → N lines

---

### 9. Project/Task (project.project / project.task)

**Definition**: Post-sale operational tracking.

**Key Attributes** (project):
- `name` (string, required)
- `partner_id` (m2o → res.partner)
- `user_id` (m2o → res.users): Manager

**Key Attributes** (task):
- `name` (string, required)
- `project_id` (m2o → project.project)
- `user_ids` (m2m → res.users): Assignees
- `date_deadline` (date)

**Cardinality**: 1 project → N tasks

---

### 10. Taxonomy (crm.stage / crm.lost.reason / crm.tag / res.partner.category)

**Definition**: Controlled vocabularies for categorization and pipeline management.

**crm.stage**:
- `name` (string, required)
- `is_won` (boolean), `fold` (boolean): Won/lost indicators
- `sequence` (integer): Display order

**Resolution Policy**: lookup_only (stages control reporting/funnel math)

**crm.lost.reason**:
- `name` (string, required)

**Resolution Policy**: suggest_only (require approval)

**crm.tag** / **res.partner.category**:
- `name` (string, required)

**Natural Key**: lower(trim(`name`)) within `company_id`
**Resolution Policy**: create_if_missing (low risk, m2m friendly)

---

### 11. Geo (res.country / res.country.state)

**Definition**: Geographic reference data.

**res.country**:
- `name` (string), `code` (char(2)): ISO alpha-2

**res.country.state**:
- `name` (string), `code` (string), `country_id` (m2o → res.country)

**Resolution Policy**: lookup_only (never create countries/states)

---

### 12. Company (res.company)

**Definition**: Multi-company segregation entity.

**Key Attributes**:
- `name` (string, required)
- `partner_id` (m2o → res.partner): Underlying contact

**Resolution Policy**: lookup_only (companies are system config)

---

## Cardinality Summary

| Relationship | Odoo Type | Example |
|--------------|-----------|---------|
| Partner (Company) ↔ Contact (Person) | parent_id (m2o) | 1 company → N contacts |
| Lead → Partner | partner_id (m2o) | N leads → 1 partner |
| Lead → Stage | stage_id (m2o) | N leads → 1 stage |
| Lead → Lost Reason | lost_reason_id (m2o) | N leads → 0/1 reason |
| Lead ↔ Tags | tag_ids (m2m) | N↔N |
| Lead → Activities | mail.activity (o2m) | 1 lead → N activities |
| Lead → Messages | mail.message (o2m) | 1 lead → N messages |
| Order → Lines | order_line (o2m) | 1 order → N lines |
| Project → Tasks | task_ids (o2m) | 1 project → N tasks |

---

## Resolution Policy Matrix (Defaults)

| Model | Policy | Rationale |
|-------|--------|-----------|
| crm.stage | lookup_only | Controls reporting, funnel math |
| crm.lost.reason | suggest_only | Bespoke wording requires approval |
| utm.source / medium / campaign | suggest_only* | Review before creating; flip to lookup_only post-stabilization |
| crm.tag | create_if_missing | Low risk, high variability |
| res.partner.category | create_if_missing | Low risk, m2m friendly |
| res.country / res.country.state | lookup_only | Never create geo data |
| res.users | lookup_only | Security boundary |
| res.company | lookup_only | System config |

\* Can be overridden per tenant/environment to create_if_missing during migration cutover, then locked back to strict.

---

## ETL Validators

### Pre-Load Assertions

- All m2o references resolve to existing Odoo IDs
- No contact without parent company (if ontology requires)
- Lead marked lost → must have valid `lost_reason_id` and lost stage
- Required fields present: `partner_id` on orders, `stage_id` on leads
- UTM values exist or policy allows creation
- Unique constraints satisfied (e.g., `vat` per company, `login` for users)

### Post-Load Reconciliation

- Odoo record counts == canonical table counts (per model)
- Sample-based deep checks: 50 random leads confirm linked partners/stages/tags exist
- No orphaned activities/messages (all polymorphic links valid)
- No duplicate natural keys within company scope

---

**Last Updated**: 2025-10-24
**Owned By**: Data Platform Team
