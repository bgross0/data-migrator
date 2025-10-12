# Comprehensive Testing Plan for HybridMatcher

## Current Coverage (Limited)
- **3 test cases**: Customers, Products, Sales Orders
- **22 total fields**: All standard, clean column names
- **1 data format**: Standard English naming conventions
- **0 edge cases**: No special characters, abbreviations, or messy data

## Proposed Comprehensive Test Suite

### Category 1: Additional Odoo Models (High Priority)
Expand coverage to more business entities:

**Accounting & Finance**:
- Invoices (account.move) - 12+ fields
- Invoice Lines (account.move.line) - 10+ fields
- Payments (account.payment) - 8+ fields
- Journal Entries (account.move) - 8+ fields

**CRM & Marketing**:
- Leads/Opportunities (crm.lead) - 15+ fields
- Activities (mail.activity) - 8+ fields

**Project Management**:
- Projects (project.project) - 10+ fields
- Tasks (project.task) - 12+ fields
- Timesheets (account.analytic.line) - 8+ fields

**Inventory & Manufacturing**:
- Stock Moves (stock.move) - 10+ fields
- Inventory Adjustments (stock.quant) - 8+ fields
- Bills of Materials (mrp.bom) - 8+ fields

**HR & Employees**:
- Employees (hr.employee) - 15+ fields
- Contracts (hr.contract) - 10+ fields
- Attendance (hr.attendance) - 6+ fields

**Purchasing**:
- Purchase Orders (purchase.order) - 10+ fields
- Purchase Order Lines (purchase.order.line) - 8+ fields
- Vendors (res.partner with supplier=True) - 10+ fields

**Target**: 150+ additional fields across 15+ models

---

### Category 2: Data Format Variations (High Priority)
Test different naming conventions and formats:

**Column Name Variations**:
- Abbreviations: "Cust Name", "Prod #", "Qty", "Amt", "PO#"
- Snake_case: "customer_name", "order_date", "total_amount"
- camelCase: "customerName", "orderDate", "totalAmount"
- UPPERCASE: "CUSTOMER NAME", "PRODUCT SKU", "ORDER TOTAL"
- With prefixes: "Customer - Name", "Product: SKU", "[Order] Date"
- With suffixes: "Name (Customer)", "Total $", "Date (MM/DD/YYYY)"
- Foreign language: "Nombre del Cliente", "客户名称", "Nom du Client"

**Date Formats**:
- US: "01/15/2024", "1/15/24"
- ISO: "2024-01-15"
- European: "15/01/2024", "15-Jan-2024"
- Text: "January 15, 2024", "15th Jan 2024"
- Timestamp: "2024-01-15 14:30:00"

**Phone Number Formats**:
- US: "+1-555-0100", "(555) 555-0100", "555.555.0100"
- International: "+44 20 7946 0958", "+33 1 42 86 82 00"
- Without formatting: "5555550100"

**Currency/Price Formats**:
- With symbols: "$1,234.56", "€1.234,56", "£1,234.56"
- Without symbols: "1234.56", "1,234.56"
- Text: "One thousand dollars"

**Boolean Variations**:
- True/False, Yes/No, Y/N, 1/0, Active/Inactive, Enabled/Disabled

**Target**: 50+ fields testing format variations

---

### Category 3: Edge Cases & Messy Data (High Priority)
Test real-world data quality issues:

**Special Characters**:
- Unicode: "Café René", "北京公司", "Société Générale"
- Symbols: "Customer #1", "Product (v2)", "Order @ 2024"
- Emojis: "Product 🎯", "Customer ⭐"

**Ambiguous Mappings**:
- "Name" - Could be res.partner.name, product.product.name, sale.order.name, etc.
- "Status" - Many models have state/status fields
- "Date" - Which date? Order date, invoice date, delivery date?
- "Amount" - Total, subtotal, tax, discount?

**Data Quality Issues**:
- Extra whitespace: "  Customer Name  ", "Product\tSKU"
- Inconsistent case: "customer NAME", "Product name"
- Typos: "Cutomer Name", "Produt SKU", "Oder Date"
- Missing data: Empty columns, NULL values
- Mixed types: "123" vs 123, "True" vs True

**Composite Fields**:
- "First Name" + "Last Name" → res.partner.name
- "Street" + "City" + "State" + "Zip" → address fields
- "SKU-Name" → Split into default_code + name
- "Price (USD)" → Extract currency and amount

**Target**: 40+ edge case fields

---

### Category 4: Multi-Sheet Scenarios (Medium Priority)
Test datasets with multiple related sheets:

**Parent-Child Relationships**:
- Sheet 1: Customers (res.partner)
- Sheet 2: Orders (sale.order) - References customers
- Sheet 3: Order Lines (sale.order.line) - References orders

**Master Data + Transactions**:
- Sheet 1: Products (product.product)
- Sheet 2: Inventory (stock.quant)
- Sheet 3: Stock Moves (stock.move)

**Different Models in Same File**:
- Sheet 1: Customers
- Sheet 2: Vendors (also res.partner but different context)
- Sheet 3: Employees (hr.employee)

**Target**: 5+ multi-sheet scenarios with 60+ total fields

---

### Category 5: Adversarial Cases (Low Priority)
Intentionally difficult test cases:

**Minimal Context**:
- Single column sheets: Just "Name" or just "Total"
- No sheet name context
- Generic column names only

**Conflicting Signals**:
- Sheet name says "Customers" but columns match products
- Column names match multiple models equally well

**Custom Fields**:
- x_custom_field_1, x_studio_field_2
- Custom labels not in KB
- Industry-specific terminology

**Unusual Models**:
- Less common Odoo models (ir.cron, ir.sequence, etc.)
- Third-party module models
- Multi-company scenarios

**Target**: 20+ adversarial fields

---

## Testing Strategy

### Phase 1: Expand Core Models (Week 1)
- Add 5 new model types (invoices, leads, projects, tasks, purchase orders)
- ~80 new fields
- Target: Maintain ≥90% accuracy

### Phase 2: Format Variations (Week 1-2)
- Test abbreviations, case variations, different date/phone/currency formats
- ~50 new fields
- Target: ≥85% accuracy (some format variations are inherently harder)

### Phase 3: Edge Cases (Week 2)
- Special characters, ambiguous mappings, messy data
- ~40 new fields
- Target: ≥80% accuracy (edge cases expected to be harder)

### Phase 4: Multi-Sheet (Week 3)
- 3-5 multi-sheet scenarios
- ~60 new fields
- Target: Correct model detection across sheets, ≥85% accuracy

### Phase 5: Adversarial (Week 3-4)
- Intentionally difficult cases
- ~20 new fields
- Target: Graceful degradation, ≥70% accuracy

---

## Implementation Approach

### Option A: Expand ground_truth.py Incrementally
Add test cases one category at a time to `ground_truth.py`:

```python
GROUND_TRUTH = {
    # Existing
    "customers": {...},
    "products": {...},
    "sales_orders": {...},

    # Phase 1: New models
    "invoices": {...},
    "leads": {...},
    "projects": {...},
    "tasks": {...},
    "purchase_orders": {...},

    # Phase 2: Format variations
    "customers_abbreviated": {...},
    "products_snake_case": {...},
    "orders_uppercase": {...},

    # Phase 3: Edge cases
    "customers_messy": {...},
    "products_unicode": {...},
    "orders_ambiguous": {...},

    # etc.
}
```

### Option B: Separate Test Suites by Category
Create separate test files for each category:
- `test_hybrid_core_models.py` - Phase 1
- `test_hybrid_formats.py` - Phase 2
- `test_hybrid_edge_cases.py` - Phase 3
- `test_hybrid_multi_sheet.py` - Phase 4
- `test_hybrid_adversarial.py` - Phase 5

### Option C: Real-World Dataset Testing
Obtain actual anonymized customer data exports:
- Excel files from real companies
- CSV exports from legacy systems
- Migration scenarios from other ERPs

---

## Success Metrics

### Coverage Goals
- **Models**: 15+ Odoo models (currently 3)
- **Fields**: 250+ total fields (currently 22)
- **Formats**: 5+ naming conventions (currently 1)
- **Edge cases**: 40+ messy/ambiguous cases (currently 0)

### Accuracy Targets by Phase
- **Phase 1 (Core Models)**: ≥90% accuracy
- **Phase 2 (Formats)**: ≥85% accuracy
- **Phase 3 (Edge Cases)**: ≥80% accuracy
- **Phase 4 (Multi-Sheet)**: ≥85% accuracy
- **Phase 5 (Adversarial)**: ≥70% accuracy

### Overall Target
- **Final Comprehensive Suite**: ≥85% overall accuracy across all 250+ fields

---

## Immediate Next Steps

**Quick wins** you can implement today:

1. **Phase 1A: Add Invoices** (30 min)
   - Add account.move test case with 12 fields
   - Run test, measure accuracy

2. **Phase 1B: Add Leads** (30 min)
   - Add crm.lead test case with 15 fields
   - Run test, measure accuracy

3. **Phase 2A: Add Abbreviated Columns** (20 min)
   - Create "customers_abbreviated" with "Cust Name", "Ph #", "Addr"
   - Test if HybridMatcher handles abbreviations

4. **Phase 3A: Add Unicode/Special Chars** (20 min)
   - Create "customers_unicode" with "Café René", "北京公司"
   - Test special character handling

Would you like me to start with any of these phases? I'd recommend:
- **Start with Phase 1A (Invoices)** to expand model coverage
- **Then Phase 2A (Abbreviations)** to test format handling
- This will give us quick insight into HybridMatcher's robustness
