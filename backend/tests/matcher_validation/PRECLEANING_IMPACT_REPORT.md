# Pre-Cleaning Impact Report

**Date**: October 11, 2025
**Test Suite**: Pre-Cleaning Impact Test
**Purpose**: Validate that column name pre-cleaning improves HybridMatcher accuracy

---

## Executive Summary

✅ **RESULT: SIGNIFICANT IMPROVEMENT**

Pre-cleaning column names before matching improves overall accuracy by **+15.4 percentage points**, from 84.6% to 100.0%.

**Recommendation**: **ENABLE pre-cleaning in production pipeline**

---

## Overall Results

| Metric | RAW | CLEANED | Improvement |
|--------|-----|---------|-------------|
| **Total Fields Tested** | 26 | 26 | - |
| **Correct Matches** | 22 | 26 | +4 |
| **Accuracy** | 84.6% | 100.0% | **+15.4%** |
| **Test Cases Passed** | 1/3 | 3/3 | +2 |

---

## Per-Test Case Breakdown

### Test 1: Customers (res.partner)
**Status**: Already clean - No improvement needed

| Metric | RAW | CLEANED | Change |
|--------|-----|---------|--------|
| Accuracy | 100.0% (9/9) | 100.0% (9/9) | 0.0% |
| Status | ✓ PASS | ✓ PASS | - |

**Column Mappings**: No changes (columns were already clean)

**Analysis**: This test demonstrates that pre-cleaning is **non-destructive** - it doesn't harm already-clean column names.

---

### Test 2: Leads (crm.lead) - WITH PARENTHETICAL SUFFIXES
**Status**: Significant improvement due to suffix removal

| Metric | RAW | CLEANED | Change |
|--------|-----|---------|--------|
| Accuracy | 70.0% (7/10) | 100.0% (10/10) | **+30.0%** |
| Status | ✗ FAIL | ✓ PASS | ✓ |

**Column Mappings**:
```
Street Address (Contact) → Street Address
City (Contact)           → City
Zip (Contact)            → Zip
```

**Failures Fixed** (3 fields):
1. **"Street Address (Contact)"**
   - RAW: Incorrectly matched to `crm.lead.partner_id` (relationship field)
   - CLEANED: ✓ Correctly matched to `crm.lead.street`

2. **"City (Contact)"**
   - RAW: Incorrectly matched to `crm.lead.partner_id` (relationship field)
   - CLEANED: ✓ Correctly matched to `crm.lead.city`

3. **"Zip (Contact)"**
   - RAW: Incorrectly matched to `crm.lead.partner_id` (relationship field)
   - CLEANED: ✓ Correctly matched to `crm.lead.zip`

**Analysis**: The parenthetical suffix " (Contact)" confused the matcher, causing it to match the relationship field instead of the actual address fields. Pre-cleaning removed the suffix and achieved perfect accuracy.

**Real-World Impact**: The test file "Leads (1).xlsx" had 10 columns with similar suffixes. This improvement directly addresses that real-world data quality issue.

---

### Test 3: Products (product.product) - WITH SPECIAL CHARACTERS
**Status**: Moderate improvement due to special character removal

| Metric | RAW | CLEANED | Change |
|--------|-----|---------|--------|
| Accuracy | 85.7% (6/7) | 100.0% (7/7) | **+14.3%** |
| Status | ✗ FAIL | ✓ PASS | ✓ |

**Column Mappings**:
```
Product Name...       → Product Name
SKU*                  → SKU
Sale Price?           → Sale Price
Cost Price (Internal) → Cost Price
Barcode #             → Barcode
```

**Failures Fixed** (1 field):
1. **"Cost Price (Internal)"**
   - RAW: Incorrectly matched to `product.product.list_price` (sale price)
   - CLEANED: ✓ Correctly matched to `product.product.standard_price` (cost price)

**Analysis**: The parenthetical suffix "(Internal)" confused the matcher. After cleaning to just "Cost Price", the matcher correctly identified it as the standard_price field.

Special characters like `*`, `?`, `#`, and `...` were also successfully removed without affecting accuracy.

---

## Key Findings

### 1. Parenthetical Suffixes are Problematic
**Pattern**: ` (Something)`, ` (Contact)`, ` (Internal)`, etc.

**Impact**: These suffixes significantly degrade matching accuracy by adding semantic confusion. The matcher struggles to differentiate between:
- "Street Address" vs "Street Address (Contact)"
- "Cost Price" vs "Cost Price (Internal)"

**Solution**: Pre-cleaning removes these suffixes, improving accuracy by **30% on the Leads test**.

---

### 2. Special Characters are Common but Harmless After Cleaning
**Pattern**: `*`, `?`, `#`, `...`

**Impact**: These characters appear in real-world exports (likely from CRM systems like Salesforce). While they don't always break matching, they can cause confusion.

**Solution**: Pre-cleaning removes trailing special characters, improving consistency.

---

### 3. Pre-Cleaning is Non-Destructive
The Customers test (already clean) showed **no degradation** in accuracy, confirming that pre-cleaning:
- ✅ Only modifies problematic patterns
- ✅ Preserves clean column names
- ✅ Does not introduce false positives

---

## Validation Against Real Data

The test results validate our analysis of the real "Leads (1).xlsx" file, which contained:
- 10 columns with parenthetical suffixes (e.g., " (Contact)", " (Opp)", " (All)")
- 7 columns with special characters (e.g., `*`, `?`, `#`)
- 83 values with whitespace issues

**Test Coverage**:
- ✅ Parenthetical suffixes: Validated (Test 2: Leads)
- ✅ Special characters: Validated (Test 3: Products)
- ⚠️ Whitespace issues: Not tested in column names (only in values)

---

## Recommendations

### Immediate Actions
1. ✅ **ENABLE pre-cleaning in production pipeline**
   - Add pre-cleaning step before HybridMatcher
   - Use `ColumnNameCleaningRule` with default config

2. ✅ **Run pre-cleaning on upload**
   - Apply cleaning immediately after file upload
   - Store both original and cleaned column names for audit trail

### Pipeline Integration
```python
# Proposed integration in upload pipeline
from app.cleaners.config import CleaningConfig
from app.cleaners.rules.column_name import ColumnNameCleaningRule

# After loading DataFrame from upload
config = CleaningConfig.default()
cleaner = ColumnNameCleaningRule(config)
result = cleaner.clean(df)

# Store original → cleaned mappings for transparency
column_mappings = {
    orig: cleaned
    for orig, cleaned in zip(df.columns, result.df.columns)
}

# Use cleaned DataFrame for matching
df_cleaned = result.df
```

### Future Testing
1. **Value-level cleaning**: Test impact of whitespace trimming and HTML entity decoding on data quality
2. **Additional rules**: Test impact of currency normalization, empty column removal
3. **Full integration**: Run comprehensive test suite (10 tests, 75 fields) with pre-cleaning enabled

---

## Technical Details

### Test Environment
- **Python**: 3.x
- **HybridMatcher Version**: Latest (with fleet.vehicle patterns, custom field support)
- **Dictionary**: `/odoo-dictionary` (520 models, 9947 fields)
- **Test Framework**: Custom pre-cleaning impact test

### Test Methodology
1. Create DataFrames with known problematic column names
2. Run HybridMatcher on RAW column names → measure accuracy
3. Apply `ColumnNameCleaningRule` to clean column names
4. Run HybridMatcher on CLEANED column names → measure accuracy
5. Compare results and calculate improvement

### Configuration Used
```python
CleaningConfig(
    clean_column_names=True,
    remove_parentheses=True,
    remove_special_chars=True,
    special_chars_to_remove="*?#",
    trim_column_names=True,
    normalize_spaces=True,
)
```

---

## Conclusion

**Pre-cleaning column names provides significant, measurable improvement to matching accuracy.**

- **Overall improvement**: +15.4 percentage points
- **Leads test improvement**: +30.0 percentage points (70% → 100%)
- **Products test improvement**: +14.3 percentage points (86% → 100%)
- **No degradation**: Clean data remains 100% accurate

**The data supports immediate integration of pre-cleaning into the production pipeline.**

---

## Appendix: Detailed Test Results

### Test Execution
```bash
cd /home/zlab/data-migrator/backend/tests/matcher_validation
source ../../venv/bin/activate
python test_precleaning_impact.py
```

### Output Summary
```
================================================================================
PRE-CLEANING IMPACT SUMMARY
================================================================================

Overall Results:
  Total Fields:      26
  RAW Correct:       22 (84.6%)
  CLEANED Correct:   26 (100.0%)
  Improvement:       +15.4 percentage points

Per-Test Case Breakdown:
--------------------------------------------------------------------------------
Test Case                      RAW             CLEANED         Improvement
--------------------------------------------------------------------------------
Customers                      ✓ 100.0%        ✓ 100.0%          +0.0%
Leads                          ✗  70.0%        ✓ 100.0%         +30.0%
Products (Messy)               ✗  85.7%        ✓ 100.0%         +14.3%
--------------------------------------------------------------------------------

================================================================================
✓✓✓ SIGNIFICANT IMPROVEMENT: Pre-cleaning improves accuracy by >5%!
    Recommendation: ENABLE pre-cleaning in production pipeline
================================================================================
```

### Files Generated
- `test_precleaning_impact.py`: Test script
- `PRECLEANING_IMPACT_REPORT.md`: This report
