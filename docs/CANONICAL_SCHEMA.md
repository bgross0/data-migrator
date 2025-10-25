# Canonical Schema Sketch

**Purpose**: Factorized data model (dim/fact/bridge) that sits between staging and Odoo load. Enables deduplication, natural key resolution, and dependency management.

## Design Principles

1. **Minimal Redundancy**: Dimensions stored once, facts reference via surrogate keys
2. **1:1 with Odoo**: Each canonical table maps directly to one Odoo model
3. **Clear Load Order**: Dimensions → Facts → Bridges (matches Odoo dependencies)
4. **Lineage Preserved**: Every row tracks `src_system`, `src_table`, `src_pk`, `src_hash`
5. **Idempotency Ready**: Natural keys + content hashes enable safe replays

---

## Staging Layer (Raw → Typed)

### Purpose
- Accept raw source data with minimal transformation
- Light typing (string → date, currency → decimal)
- Preserve source identity for lineage

### Tables

```sql
-- One staging table per source entity type
CREATE TABLE stg_leads (
    id SERIAL PRIMARY KEY,
    src_system VARCHAR NOT NULL,     -- 'hubspot', 'salesforce', 'csv_import_2024'
    src_table VARCHAR NOT NULL,       -- 'leads', 'opportunities'
    src_pk VARCHAR NOT NULL,          -- Original source ID
    src_hash VARCHAR NOT NULL,        -- MD5 of raw row

    -- Raw columns (as found in source)
    raw_data JSONB NOT NULL,          -- Full raw row for audit

    -- Lightly typed columns (extracted from raw_data)
    name VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    company_name VARCHAR,
    contact_name VARCHAR,
    stage VARCHAR,
    owner_email VARCHAR,
    utm_source VARCHAR,
    utm_medium VARCHAR,
    utm_campaign VARCHAR,
    expected_revenue DECIMAL(15,2),
    created_date DATE,

    -- Metadata
    loaded_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL,

    UNIQUE(src_system, src_table, src_pk)
);

-- Similar tables for:
-- stg_contacts, stg_companies, stg_activities, stg_messages
```

**Key Rules**:
- NO foreign keys yet (just natural keys as strings)
- Keep source identity columns: `src_system`, `src_table`, `src_pk`, `src_hash`
- Store full `raw_data` JSONB for forensics

---

## Canonical Layer (Factorized)

### Dimension Tables (Catalogs & Reference Data)

#### dim_partner
```sql
CREATE TABLE dim_partner (
    partner_sk SERIAL PRIMARY KEY,        -- Surrogate key

    -- Source lineage
    src_system VARCHAR NOT NULL,
    src_table VARCHAR NOT NULL,
    src_pk VARCHAR NOT NULL,
    src_hash VARCHAR NOT NULL,

    -- Natural keys (for deduplication)
    natural_key_hash VARCHAR NOT NULL UNIQUE,  -- Hash of (vat OR name+address)

    -- Odoo mapping
    odoo_id INTEGER,                      -- NULL until loaded to Odoo
    external_id VARCHAR UNIQUE,           -- Odoo external_id (for XMLID lookups)

    -- Business attributes (normalized)
    is_company BOOLEAN NOT NULL,
    parent_sk INTEGER REFERENCES dim_partner(partner_sk),  -- For contacts
    name VARCHAR NOT NULL,
    vat VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    mobile VARCHAR,
    street VARCHAR,
    street2 VARCHAR,
    city VARCHAR,
    state_code VARCHAR,                   -- Normalized to res.country.state.code
    country_code VARCHAR(2),              -- Normalized to ISO alpha-2
    zip VARCHAR,
    type VARCHAR,                         -- 'contact', 'invoice', 'delivery'
    company_sk INTEGER NOT NULL,          -- References dim_company

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL,

    CHECK (is_company = TRUE OR parent_sk IS NOT NULL)  -- Contacts must have parent
);

CREATE INDEX idx_dim_partner_natural_key ON dim_partner(natural_key_hash);
CREATE INDEX idx_dim_partner_odoo_id ON dim_partner(odoo_id);
CREATE INDEX idx_dim_partner_external_id ON dim_partner(external_id);
```

#### dim_user
```sql
CREATE TABLE dim_user (
    user_sk SERIAL PRIMARY KEY,

    -- Source lineage
    src_system VARCHAR NOT NULL,
    src_pk VARCHAR NOT NULL,

    -- Natural key
    login VARCHAR NOT NULL UNIQUE,        -- Primary natural key

    -- Odoo mapping
    odoo_id INTEGER UNIQUE,

    -- Attributes
    name VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    partner_sk INTEGER REFERENCES dim_partner(partner_sk),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL
);
```

#### dim_stage
```sql
CREATE TABLE dim_stage (
    stage_sk SERIAL PRIMARY KEY,

    -- Natural key
    name VARCHAR NOT NULL,
    team_name VARCHAR,                    -- NULL = global
    natural_key_hash VARCHAR NOT NULL UNIQUE,

    -- Odoo mapping
    odoo_id INTEGER UNIQUE,

    -- Attributes
    sequence INTEGER NOT NULL,
    is_won BOOLEAN DEFAULT FALSE,
    fold BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL
);
```

#### dim_lost_reason, dim_tag, dim_utm_source, dim_utm_medium, dim_utm_campaign
```sql
-- Similar structure:
-- - {entity}_sk (PK)
-- - natural_key_hash (unique, based on normalized name)
-- - odoo_id (unique)
-- - name (normalized)
-- - company_sk (if scoped per company)
-- - created_at, batch_id
```

#### dim_product
```sql
CREATE TABLE dim_product (
    product_sk SERIAL PRIMARY KEY,

    -- Source lineage
    src_system VARCHAR NOT NULL,
    src_pk VARCHAR NOT NULL,

    -- Natural key
    default_code VARCHAR,                 -- SKU
    natural_key_hash VARCHAR NOT NULL UNIQUE,

    -- Odoo mapping
    odoo_template_id INTEGER,             -- product.template
    odoo_product_id INTEGER,              -- product.product

    -- Attributes
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,                -- 'consu', 'service', 'product'
    list_price DECIMAL(15,2),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL
);
```

#### dim_company
```sql
CREATE TABLE dim_company (
    company_sk SERIAL PRIMARY KEY,

    -- Odoo mapping
    odoo_id INTEGER UNIQUE NOT NULL,

    -- Attributes
    name VARCHAR NOT NULL,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### Fact Tables (Business Events)

#### fact_lead
```sql
CREATE TABLE fact_lead (
    lead_sk SERIAL PRIMARY KEY,

    -- Source lineage
    src_system VARCHAR NOT NULL,
    src_table VARCHAR NOT NULL,
    src_pk VARCHAR NOT NULL,
    src_hash VARCHAR NOT NULL,

    -- Natural keys
    natural_key_hash VARCHAR NOT NULL UNIQUE,
    content_hash VARCHAR NOT NULL,        -- For change detection

    -- Odoo mapping
    odoo_id INTEGER,
    external_id VARCHAR UNIQUE,

    -- Foreign keys (surrogate keys to dimensions)
    partner_sk INTEGER REFERENCES dim_partner(partner_sk),
    user_sk INTEGER NOT NULL REFERENCES dim_user(user_sk),
    stage_sk INTEGER NOT NULL REFERENCES dim_stage(stage_sk),
    lost_reason_sk INTEGER REFERENCES dim_lost_reason(lost_reason_sk),
    utm_source_sk INTEGER REFERENCES dim_utm_source(utm_source_sk),
    utm_medium_sk INTEGER REFERENCES dim_utm_medium(utm_medium_sk),
    utm_campaign_sk INTEGER REFERENCES dim_utm_campaign(utm_campaign_sk),
    company_sk INTEGER NOT NULL REFERENCES dim_company(company_sk),

    -- Business attributes
    name VARCHAR NOT NULL,
    contact_name VARCHAR,
    email_from VARCHAR,
    phone VARCHAR,
    expected_revenue DECIMAL(15,2),
    probability DECIMAL(5,2),
    date_open TIMESTAMP,
    date_closed TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL
);

CREATE INDEX idx_fact_lead_natural_key ON fact_lead(natural_key_hash);
CREATE INDEX idx_fact_lead_content_hash ON fact_lead(content_hash);
CREATE INDEX idx_fact_lead_odoo_id ON fact_lead(odoo_id);
CREATE INDEX idx_fact_lead_partner_sk ON fact_lead(partner_sk);
```

#### fact_activity
```sql
CREATE TABLE fact_activity (
    activity_sk SERIAL PRIMARY KEY,

    -- Source lineage
    src_system VARCHAR NOT NULL,
    src_table VARCHAR NOT NULL,
    src_pk VARCHAR NOT NULL,
    src_hash VARCHAR NOT NULL,

    -- Natural key
    natural_key_hash VARCHAR NOT NULL UNIQUE,

    -- Odoo mapping
    odoo_id INTEGER,

    -- Polymorphic link (anchor)
    anchor_model VARCHAR NOT NULL,        -- 'fact_lead' or 'dim_partner'
    anchor_sk INTEGER NOT NULL,           -- FK to either fact_lead or dim_partner

    -- Foreign keys
    user_sk INTEGER NOT NULL REFERENCES dim_user(user_sk),
    activity_type_sk INTEGER NOT NULL REFERENCES dim_activity_type(activity_type_sk),

    -- Attributes
    date_deadline DATE NOT NULL,
    summary VARCHAR,
    note TEXT,
    sequence INTEGER,                     -- For ordering (from pivot)

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL,

    CHECK (anchor_model IN ('fact_lead', 'dim_partner'))
);

CREATE INDEX idx_fact_activity_anchor ON fact_activity(anchor_model, anchor_sk);
```

#### fact_message
```sql
CREATE TABLE fact_message (
    message_sk SERIAL PRIMARY KEY,

    -- Source lineage
    src_system VARCHAR NOT NULL,
    src_pk VARCHAR NOT NULL,

    -- Natural key
    natural_key_hash VARCHAR NOT NULL UNIQUE,

    -- Odoo mapping
    odoo_id INTEGER,

    -- Polymorphic link
    anchor_model VARCHAR NOT NULL,
    anchor_sk INTEGER NOT NULL,

    -- Foreign keys
    author_sk INTEGER REFERENCES dim_partner(partner_sk),

    -- Attributes
    subject VARCHAR,
    body TEXT,
    message_type VARCHAR NOT NULL,        -- 'email', 'comment', 'notification'
    date TIMESTAMP NOT NULL,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL,

    CHECK (anchor_model IN ('fact_lead', 'dim_partner'))
);
```

#### fact_order
```sql
CREATE TABLE fact_order (
    order_sk SERIAL PRIMARY KEY,

    -- Source lineage
    src_system VARCHAR NOT NULL,
    src_pk VARCHAR NOT NULL,
    src_hash VARCHAR NOT NULL,

    -- Natural key
    natural_key_hash VARCHAR NOT NULL UNIQUE,
    content_hash VARCHAR NOT NULL,

    -- Odoo mapping
    odoo_id INTEGER,
    external_id VARCHAR UNIQUE,

    -- Foreign keys
    partner_sk INTEGER NOT NULL REFERENCES dim_partner(partner_sk),
    user_sk INTEGER NOT NULL REFERENCES dim_user(user_sk),
    company_sk INTEGER NOT NULL REFERENCES dim_company(company_sk),

    -- Attributes
    name VARCHAR NOT NULL,
    date_order TIMESTAMP NOT NULL,
    state VARCHAR NOT NULL,
    amount_total DECIMAL(15,2),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL
);
```

#### fact_order_line
```sql
CREATE TABLE fact_order_line (
    line_sk SERIAL PRIMARY KEY,

    -- Source lineage
    src_system VARCHAR NOT NULL,
    src_pk VARCHAR NOT NULL,

    -- Foreign keys
    order_sk INTEGER NOT NULL REFERENCES fact_order(order_sk),
    product_sk INTEGER NOT NULL REFERENCES dim_product(product_sk),

    -- Attributes
    product_uom_qty DECIMAL(15,3) NOT NULL,
    price_unit DECIMAL(15,2) NOT NULL,
    discount DECIMAL(5,2) DEFAULT 0,
    sequence INTEGER,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL
);
```

---

### Bridge Tables (Many-to-Many Relationships)

#### bridge_partner_contact
```sql
-- For explicit company ↔ contact relationships
CREATE TABLE bridge_partner_contact (
    company_sk INTEGER NOT NULL REFERENCES dim_partner(partner_sk),
    person_sk INTEGER NOT NULL REFERENCES dim_partner(partner_sk),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL,

    PRIMARY KEY (company_sk, person_sk),
    CHECK (company_sk != person_sk)
);
```

#### bridge_tags_partner
```sql
CREATE TABLE bridge_tags_partner (
    partner_sk INTEGER NOT NULL REFERENCES dim_partner(partner_sk),
    tag_sk INTEGER NOT NULL REFERENCES dim_partner_category(category_sk),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL,

    PRIMARY KEY (partner_sk, tag_sk)
);
```

#### bridge_tags_lead
```sql
CREATE TABLE bridge_tags_lead (
    lead_sk INTEGER NOT NULL REFERENCES fact_lead(lead_sk),
    tag_sk INTEGER NOT NULL REFERENCES dim_tag(tag_sk),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    batch_id VARCHAR NOT NULL,

    PRIMARY KEY (lead_sk, tag_sk)
);
```

---

## Load Flow

### 1. Staging Ingest
```
Source CSV/API → stg_leads, stg_contacts, stg_companies, stg_activities
```
- Parse and lightly type
- Store full `raw_data` JSONB
- Generate `src_hash`

### 2. Canonical Factorization
```
stg_* → dim_* + fact_* + bridge_*
```
- **Deduplicate** using natural keys
- **Resolve** foreign keys to surrogate keys (e.g., stage name → stage_sk)
- **Normalize** values (trim, casefold, E.164 phones, ISO countries)
- **Generate** natural_key_hash and content_hash

### 3. Odoo Load
```
dim_* → Odoo (create/match) → populate odoo_id
fact_* → Odoo (create/match) → populate odoo_id
bridge_* → Odoo m2m commands
```
- Load in **dependency order** (dims → facts → bridges)
- Use **external_id** or **natural keys** for matching
- **Update** canonical tables with `odoo_id` after create

### 4. Idempotency Ledger Update
```
canonical.odoo_id → import_ledger
```
- Record `(src_system, src_pk) → odoo_id` mapping
- Store `natural_key_hash`, `content_hash`, `fk_map_version`
- Persist `decision_log` (matched vs created)

---

## Example: Lead Load Workflow

```sql
-- 1. Stage → Canonical (Factorization)
INSERT INTO fact_lead (src_system, src_pk, src_hash, natural_key_hash, content_hash,
                       partner_sk, user_sk, stage_sk, name, email_from, ...)
SELECT
    s.src_system,
    s.src_pk,
    s.src_hash,
    MD5(CONCAT(p.partner_sk, s.name, s.created_date)) AS natural_key_hash,
    MD5(CONCAT(s.name, s.email, s.phone, ...)) AS content_hash,
    p.partner_sk,                           -- Resolved from dim_partner
    u.user_sk,                               -- Resolved from dim_user
    st.stage_sk,                             -- Resolved from dim_stage
    s.name,
    s.email,
    ...
FROM stg_leads s
LEFT JOIN dim_partner p ON p.natural_key_hash = MD5(s.company_name + s.company_email)
LEFT JOIN dim_user u ON u.login = s.owner_email
LEFT JOIN dim_stage st ON st.natural_key_hash = MD5(LOWER(TRIM(s.stage)))
WHERE s.batch_id = 'batch_2024_10_24'
ON CONFLICT (natural_key_hash) DO UPDATE
    SET content_hash = EXCLUDED.content_hash,
        updated_at = NOW();

-- 2. Canonical → Odoo (Python/API)
for lead in fact_lead WHERE odoo_id IS NULL:
    odoo_vals = {
        'name': lead.name,
        'partner_id': dim_partner[lead.partner_sk].odoo_id,
        'user_id': dim_user[lead.user_sk].odoo_id,
        'stage_id': dim_stage[lead.stage_sk].odoo_id,
        ...
    }
    odoo_id = odoo.create('crm.lead', odoo_vals)
    UPDATE fact_lead SET odoo_id = odoo_id WHERE lead_sk = lead.lead_sk

-- 3. Bridge → Odoo m2m
for bridge in bridge_tags_lead WHERE lead_sk IN (SELECT lead_sk FROM fact_lead WHERE odoo_id IS NOT NULL):
    lead_odoo_id = fact_lead[bridge.lead_sk].odoo_id
    tag_odoo_id = dim_tag[bridge.tag_sk].odoo_id
    odoo.write('crm.lead', lead_odoo_id, {
        'tag_ids': [(4, tag_odoo_id)]  # Link tag
    })
```

---

## Benefits of This Design

1. **Deduplication**: Natural keys prevent cross-source duplicates BEFORE Odoo load
2. **Dependency Management**: Clear dim → fact → bridge order matches Odoo constraints
3. **Idempotency**: Content hashes detect changes; natural keys prevent re-creates
4. **Lineage**: Every row traces back to source via `src_system`, `src_pk`, `src_hash`
5. **Replay Safety**: Re-running ETL updates existing canonical rows (no new duplicates)
6. **Audit Trail**: `raw_data` JSONB preserved in staging for forensics
7. **Performance**: Surrogate keys (_sk) keep joins fast; Odoo IDs added after load

---

**Last Updated**: 2025-10-24
**Owned By**: Data Platform Team
