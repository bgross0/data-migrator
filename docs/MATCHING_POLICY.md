# Matching Policy

**Purpose**: Define deterministic matching rules, similarity thresholds, and human-in-the-loop (HITL) escalation paths for entity resolution and deduplication.

## Matching Strategy (Layered)

### Layer 1: Deterministic Keys (Exact Match)
**Goal**: Fast, certain matches with zero false positives

**Rules**:
- Exact match on normalized natural keys
- Normalization: LOWER(TRIM(value)), remove punctuation, collapse spaces
- **NO** fuzzy matching at this layer

**When to Use**: First pass on all entities

---

### Layer 2: Probabilistic Matching (Similarity Threshold)
**Goal**: Catch near-duplicates that deterministic rules miss

**Rules**:
- Apply similarity scoring (Levenshtein, Jaro-Winkler, or embeddings)
- Require threshold confidence (model-specific)
- Generate match candidates with scores

**When to Use**: Records that passed Layer 1 without match

---

### Layer 3: Human-in-the-Loop (HITL)
**Goal**: Escalate ambiguous cases for manual review

**Rules**:
- Multi-match candidates (2+ records with similar scores)
- Low confidence (below auto-match threshold but above auto-reject)
- High-value records (flagged by data steward)

**When to Use**: Layer 2 produces ambiguous results

---

## Per-Model Matching Rules

### res.partner (Company)

#### Layer 1: Deterministic
```python
def match_company(record):
    # Priority 1: VAT (if present)
    if record.vat:
        return MATCH_BY(normalize(vat))

    # Priority 2: Name + Address
    key = (
        normalize(name),
        normalize(street),
        normalize(city),
        normalize(state_code),
        normalize(country_code)
    )
    return MATCH_BY(key)

    # Priority 3: Name + Phone/Email Domain
    if record.phone or record.email:
        key = (
            normalize(name),
            normalize(phone) or extract_domain(email)
        )
        return MATCH_BY(key)

    # No match
    return NO_MATCH
```

**Normalization**:
- `vat`: Remove spaces, dashes, convert to uppercase
- `name`: LOWER, TRIM, remove punctuation, collapse spaces, remove legal suffixes (LLC, Inc., Ltd., Corp.)
- `street/city`: LOWER, TRIM
- `state_code`: ISO code (e.g., "CA", "NY")
- `country_code`: ISO alpha-2 (e.g., "US", "GB")
- `phone`: E.164 format
- `email`: LOWER, extract domain after @

**Confidence**: 1.0 (exact match)

#### Layer 2: Probabilistic
```python
def fuzzy_match_company(record, candidates):
    scores = []
    for candidate in candidates:
        # Name similarity (Jaro-Winkler)
        name_score = jaro_winkler(normalize(record.name), normalize(candidate.name))

        # Address similarity (Levenshtein)
        addr_score = levenshtein_ratio(
            f"{record.street} {record.city}",
            f"{candidate.street} {candidate.city}"
        )

        # Combined score (weighted)
        combined = 0.7 * name_score + 0.3 * addr_score
        scores.append((candidate, combined))

    # Return candidates above threshold
    return [c for c, score in scores if score >= 0.85]
```

**Threshold**: 0.85 (auto-match), 0.70-0.85 (HITL), <0.70 (auto-reject)

#### Layer 3: HITL
- **Trigger**: ≥2 candidates with score ≥0.70
- **Present**: Side-by-side comparison (name, address, phone, email, vat)
- **Options**: Match to candidate, Create new, Skip

---

### res.partner (Contact/Person)

#### Layer 1: Deterministic
```python
def match_contact(record):
    # Require parent company + name + email
    if record.parent_id and record.email:
        key = (
            record.parent_id,  # Already resolved company
            normalize(full_name),
            normalize(email)
        )
        return MATCH_BY(key)

    # Fallback: parent + name + phone
    if record.parent_id and record.phone:
        key = (
            record.parent_id,
            normalize(full_name),
            normalize(phone)
        )
        return MATCH_BY(key)

    return NO_MATCH
```

**Normalization**:
- `full_name`: LOWER, TRIM, collapse spaces
- `email`: LOWER
- `phone`: E.164

**Confidence**: 1.0

#### Layer 2: Probabilistic
```python
def fuzzy_match_contact(record, candidates):
    scores = []
    for candidate in candidates:
        # Must have same parent company (hard constraint)
        if candidate.parent_id != record.parent_id:
            continue

        # Name similarity
        name_score = jaro_winkler(normalize(record.full_name), normalize(candidate.full_name))

        # Email similarity (high weight)
        email_score = 1.0 if record.email == candidate.email else 0.0

        # Combined
        combined = 0.5 * name_score + 0.5 * email_score
        scores.append((candidate, combined))

    return [c for c, score in scores if score >= 0.80]
```

**Threshold**: 0.80 (auto-match), 0.65-0.80 (HITL), <0.65 (auto-reject)

---

### crm.lead

#### Layer 1: Deterministic
```python
def match_lead(record):
    # Priority 1: External ID (if provided)
    if record.external_id:
        return MATCH_BY(external_id)

    # Priority 2: Partner + Name + Date (±3 days)
    if record.partner_id:
        key = (
            record.partner_id,
            normalize(name),
            date_bucket(create_date, days=3)  # e.g., 2024-10-24 → 2024-10-22 to 2024-10-26
        )
        return MATCH_BY(key)

    # Priority 3: Email + Name + Date
    if record.email_from:
        key = (
            normalize(email_from),
            normalize(name),
            date_bucket(create_date, days=3)
        )
        return MATCH_BY(key)

    return NO_MATCH
```

**Normalization**:
- `name`: LOWER, TRIM, collapse spaces
- `email_from`: LOWER
- `create_date`: Bucket to ±3 day window

**Confidence**: 1.0

#### Layer 2: Probabilistic
```python
def fuzzy_match_lead(record, candidates):
    scores = []
    for candidate in candidates:
        # Name similarity
        name_score = jaro_winkler(normalize(record.name), normalize(candidate.name))

        # Email exact match (binary)
        email_score = 1.0 if record.email_from == candidate.email_from else 0.0

        # Date proximity (within 7 days = 1.0, beyond = decay)
        date_diff = abs((record.create_date - candidate.create_date).days)
        date_score = max(0, 1.0 - (date_diff / 30.0))  # Linear decay over 30 days

        # Combined
        combined = 0.4 * name_score + 0.4 * email_score + 0.2 * date_score
        scores.append((candidate, combined))

    return [c for c, score in scores if score >= 0.75]
```

**Threshold**: 0.75 (auto-match), 0.60-0.75 (HITL), <0.60 (auto-reject)

---

### Vocabulary (crm.tag, utm.source, etc.)

#### Layer 1: Deterministic
```python
def match_vocab(record, model):
    # Exact match on normalized name within scope
    key = (
        normalize(name),
        record.company_id  # For company-scoped vocab (tags, categories)
    )
    return MATCH_BY(key)
```

**Normalization**:
- `name`: LOWER, TRIM, collapse spaces, remove punctuation

**Confidence**: 1.0

#### Layer 2: Probabilistic (Alias Expansion + Fuzzy)
```python
def fuzzy_match_vocab(record, vocab_table, model):
    # Step 1: Check alias table
    alias = lookup_alias(model, record.name, record.company_id)
    if alias:
        return MATCH_BY(alias.canonical_value)  # Confidence: 1.0

    # Step 2: Fuzzy match on canonical names
    candidates = vocab_table.filter_by(company_id=record.company_id)
    scores = []
    for candidate in candidates:
        score = levenshtein_ratio(normalize(record.name), normalize(candidate.name))
        scores.append((candidate, score))

    return [c for c, score in scores if score >= 0.85]
```

**Alias Examples** (pre-seeded):
```csv
model,field,alias,canonical_value,company_id
utm.source,name,G Ads,google,NULL
utm.source,name,Gooogle,google,NULL
utm.source,name,FB,facebook,NULL
res.country,name,US,United States,NULL
res.country,name,USA,United States,NULL
crm.stage,name,Qualified Lead,Qualified,NULL
```

**Threshold**: 0.85 (auto-match), 0.70-0.85 (suggest), <0.70 (create if policy allows)

**Vocab Policy Enforcement**:
- `lookup_only`: If no match ≥0.85 → QUARANTINE (error)
- `create_if_missing`: If no match ≥0.85 → CREATE new
- `suggest_only`: If no match ≥0.85 → HITL (require approval)

---

## Matching Confidence Thresholds (Summary)

| Entity | Deterministic | Auto-Match | HITL | Auto-Reject | Policy |
|--------|---------------|------------|------|-------------|--------|
| res.partner (company) | 1.0 | ≥0.85 | 0.70-0.85 | <0.70 | Never auto-create, always match or HITL |
| res.partner (contact) | 1.0 | ≥0.80 | 0.65-0.80 | <0.65 | Never auto-create, always match or HITL |
| crm.lead | 1.0 | ≥0.75 | 0.60-0.75 | <0.60 | Match or create (idempotent via ledger) |
| crm.stage | 1.0 | ≥0.85 | N/A | <0.85 | lookup_only (never create) |
| crm.tag | 1.0 | ≥0.85 | N/A | <0.85 | create_if_missing |
| utm.* | 1.0 | ≥0.85 | 0.70-0.85 | <0.70 | suggest_only (HITL) |
| res.country | 1.0 | N/A | N/A | N/A | lookup_only (never create, pre-seeded) |

---

## HITL Review Queue

### Quarantine Table
```sql
CREATE TABLE match_review_queue (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR NOT NULL,
    source_table VARCHAR NOT NULL,
    source_pk VARCHAR NOT NULL,
    target_model VARCHAR NOT NULL,
    reason VARCHAR NOT NULL,  -- 'multi_match', 'low_confidence', 'ambiguous_anchor'

    -- Source record
    source_data JSONB NOT NULL,

    -- Match candidates
    candidates JSONB NOT NULL,  -- [{"partner_sk": 123, "score": 0.82, "name": "Acme Corp", ...}, ...]

    -- Resolution
    status VARCHAR DEFAULT 'pending',  -- 'pending', 'resolved', 'skipped'
    resolved_by VARCHAR,
    resolved_at TIMESTAMP,
    resolution JSONB,  -- {"action": "match", "partner_sk": 123} or {"action": "create"}

    created_at TIMESTAMP DEFAULT NOW()
);
```

### HITL UI Flow
1. **Present**: Show source record + candidates side-by-side
2. **Highlight**: Differences (name, address, email, phone) in red/green
3. **Provide Context**: Show scores, matching logic used, natural keys
4. **Options**:
   - **Match to Candidate**: Select candidate → record linked
   - **Create New**: No match → new record created
   - **Skip**: Defer decision → stays in queue
5. **Log Decision**: Store in `decision_log` (audit trail)

### Batch Review
- **Filter by Model**: Show all partners, all leads, etc.
- **Sort by Confidence**: Low confidence first (most ambiguous)
- **Bulk Actions**: Match all to top candidate (if confident)

---

## Collision Handling (Multi-Match)

**Scenario**: Source record matches ≥2 existing records with similar scores.

**Example**:
```
Source: "Acme Corp", "123 Main St", "New York"
Candidates:
  1. "Acme Corporation", "123 Main Street", "New York, NY" (score: 0.87)
  2. "ACME Corp", "123 Main St", "NYC" (score: 0.85)
```

**Action**:
1. **Quarantine** source record
2. **Present** all candidates to data steward
3. **Require** explicit choice:
   - Match to #1 (set as canonical)
   - Match to #2
   - Merge #1 and #2 (advanced: trigger Odoo merge)
   - Create new (if truly distinct)

**Decision Logged**:
```json
{
  "source_pk": "lead_1234",
  "collision_reason": "multi_match",
  "candidates": [
    {"partner_sk": 42, "score": 0.87},
    {"partner_sk": 91, "score": 0.85}
  ],
  "resolution": {
    "action": "match",
    "selected_partner_sk": 42,
    "rationale": "Preferred by data steward - more complete address"
  },
  "resolved_by": "john@example.com",
  "resolved_at": "2024-10-24T15:30:00Z"
}
```

---

## Cross-Source Deduplication

**Goal**: Prevent creating duplicates when importing from multiple sources (HubSpot + Salesforce + CSV).

**Strategy**:
1. **Natural keys span sources**: Match on `vat` or `name+address` regardless of `src_system`
2. **Ledger tracks first source**: `import_ledger.src_system` shows origin
3. **Subsequent sources match**: Layer 1/2 matching finds existing record, updates if changed
4. **Content hash detects changes**: Re-import with same natural key but different content → UPDATE

**Example**:
```
Import 1 (HubSpot):
  - "Acme Corp" → partner_sk=42, odoo_id=100, src_system='hubspot'

Import 2 (Salesforce):
  - "Acme Corporation" (same address, VAT) → MATCHES partner_sk=42
  - Content hash differs → UPDATE partner_sk=42 with new data
  - Ledger: Add entry (src_system='salesforce', src_pk='SF_001', odoo_id=100)

Result: ONE Odoo partner, TWO ledger entries (cross-source linked)
```

---

## Normalization Functions (Reference)

```python
def normalize_string(value):
    """Standard string normalization."""
    return value.lower().strip().replace('  ', ' ') if value else None

def normalize_name_company(name):
    """Normalize company name (remove legal suffixes)."""
    name = normalize_string(name)
    suffixes = ['llc', 'inc', 'corp', 'ltd', 'limited', 'corporation', 'company', 'co']
    for suffix in suffixes:
        name = re.sub(rf'\b{suffix}\b\.?$', '', name).strip()
    return name

def normalize_vat(vat):
    """Normalize VAT (remove spaces, dashes, uppercase)."""
    return re.sub(r'[\s\-]', '', vat).upper() if vat else None

def normalize_phone(phone):
    """Normalize to E.164 using TypeRegistry."""
    return TypeRegistry.parse_phone(phone, default_region='US')

def normalize_email(email):
    """Normalize email (lowercase, trim)."""
    return TypeRegistry.parse_email(email)

def extract_domain(email):
    """Extract domain from email."""
    return email.split('@')[1] if email and '@' in email else None

def date_bucket(date, days=3):
    """Bucket date to ±N day window."""
    # Return Monday of the week containing date (as example)
    return date - timedelta(days=date.weekday())
```

---

**Last Updated**: 2025-10-24
**Owned By**: Data Platform Team
