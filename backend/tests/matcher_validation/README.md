# Matcher Validation Test Harness

This test harness validates the field mapper system by running it against real test cases with known ground truth mappings.

## What It Does

1. **Tests the complex matcher** against real spreadsheet data
2. **Measures accuracy** by comparing predictions to ground truth
3. **Analyzes each strategy individually** to identify which ones help vs hurt
4. **Generates detailed reports** (HTML, JSON, CSV)
5. **Recommends optimal strategy weights** based on performance

## Quick Start

### Prerequisites

Make sure dependencies are installed:
```bash
cd /home/zlab/data-migrator/backend
pip3 install pandas networkx pygtrie openpyxl
```

### Run the Full Test Suite

```bash
cd /home/zlab/data-migrator/backend/tests/matcher_validation
python3 test_harness.py
```

This will:
- Test against customers, products, and sales orders data
- Generate HTML/JSON/CSV reports in `./reports/`
- Exit with error if accuracy is below 70%

### Analyze Individual Strategies

```bash
python3 strategy_analyzer.py
```

This will:
- Test each of the 8 strategies in isolation
- Show which strategies are most accurate
- Test strategy combinations
- Recommend optimal weights

## Understanding the Results

### Test Harness Output

The test harness generates three types of reports:

**1. HTML Report** (`reports/matcher_validation_TIMESTAMP.html`)
- Visual overview with color-coded results
- Per-test accuracy breakdowns
- Detailed column-by-column mapping results
- Open in browser to review

**2. JSON Report** (`reports/matcher_validation_TIMESTAMP.json`)
- Complete structured data
- Suitable for programmatic analysis
- Includes confidence scores and strategy info

**3. CSV Report** (`reports/column_results_TIMESTAMP.csv`)
- Flat file of all column mappings
- Easy to import into Excel/Google Sheets
- Good for manual review

### Strategy Analyzer Output

The strategy analyzer prints:

**Individual Strategy Performance:**
```
ExactNameMatch                 Correct: 8/9 (88.9%)
  Precision: 100.0%
  Recall: 88.9%
```

**Weight Recommendations:**
```
ExactNameMatch                 Weight: 1.0 - STRONG - Keep enabled
FuzzyMatch                     Weight: 0.5 - WEAK - Consider disabling
```

## Test Cases

### Currently Defined

1. **customers** - Contact/partner data (90% threshold)
2. **products** - Product catalog (90% threshold)
3. **sales_orders** - Sales orders (85% threshold)
4. **leads** - CRM leads/opportunities (80% threshold)
5. **invoices** - Accounting invoices (85% threshold)
6. **projects** - Project management (75% threshold)
7. **tasks** - Task tracking (75% threshold)
8. **vehicles** - Fleet management (80% threshold)
9. **sale_order_lines** - Order line items (85% threshold)
10. **financial_analysis** - Analytic accounting (70% threshold)

### Adding New Test Cases

1. Add ground truth to `ground_truth.py`:
```python
GROUND_TRUTH["my_test"] = {
    "Column Name": ("odoo.model", "field_name"),
    ...
}
```

2. Add test data to `test_harness.py` in the `main()` function:
```python
my_df = pd.DataFrame({
    "Column Name": ["value1", "value2"],
    ...
})

gt = harness.load_ground_truth("my_test")
result = harness.run_test_case("my_test", my_df, gt, "SheetName")
all_results.append(result)
```

3. Optionally set accuracy threshold in `ground_truth.py`:
```python
ACCURACY_THRESHOLDS["my_test"] = 0.85  # 85%
```

## Interpreting Strategy Performance

### High-Value Strategies
These should have **high weight (1.0)**:
- **ExactNameMatch**: Perfect matches (e.g., "name" → name)
- **LabelMatch**: Matches Odoo field labels
- **SelectionValueMatch**: Matches based on valid selection values

### Medium-Value Strategies
These may need **reduced weight (0.5-0.7)**:
- **DataTypeCompatibility**: Type-based matching
- **PatternMatch**: Regex patterns (email, phone, etc.)
- **ContextualMatch**: Uses context from other columns

### Potentially Noisy Strategies
These might need **low/zero weight** if accuracy is poor:
- **StatisticalSimilarity**: Statistical properties
- **FuzzyMatch**: String similarity (can cause false positives)

## Tuning the Matcher

Based on test results, you can tune strategy weights in:
`backend/app/field_mapper/config/settings.py`

```python
class FieldMapperSettings(BaseSettings):
    # Adjust these based on strategy analyzer recommendations
    exact_match_weight: float = 1.0       # Keep high
    label_match_weight: float = 0.95      # Keep high
    selection_value_weight: float = 0.90  # Keep high
    data_type_weight: float = 0.70        # Maybe reduce
    pattern_match_weight: float = 0.75    # Adjust as needed
    statistical_weight: float = 0.60      # Maybe reduce or disable
    contextual_weight: float = 0.80       # Adjust as needed
    fuzzy_match_weight: float = 0.65      # Maybe reduce or disable
```

After tuning, re-run the test harness to validate improvements.

## Success Criteria

A good matcher should achieve:
- **≥90% accuracy** on customers and products (critical use cases)
- **≥85% accuracy** on sales orders and invoices (transactional data)
- **≥80% accuracy** on CRM and specialized modules
- **≥70% overall accuracy** across all test cases

If accuracy is below these thresholds, use the strategy analyzer to identify and fix issues.

## Troubleshooting

### "ModuleNotFoundError: No module named 'pandas'"
Install dependencies:
```bash
pip3 install pandas networkx pygtrie openpyxl
```

### "dictionary_path must be set to load from dictionary"
Make sure the odoo-dictionary folder exists:
```bash
ls /home/zlab/data-migrator/odoo-dictionary/
```

Should contain:
- Fields (ir.model.fields).xlsx
- Fields Selection (ir.model.fields.selection).xlsx
- Model Constraint (ir.model.constraint).xlsx
- Models (ir.model) (1).xlsx
- Relation Model (ir.model.relation).xlsx

### Low Accuracy Results
1. Run `strategy_analyzer.py` to identify problematic strategies
2. Disable or reduce weight of low-performing strategies
3. Check ground truth definitions are correct
4. Ensure Odoo dictionary files are complete

## Next Steps

After validating the matcher:

1. **Add Pre-Cleaning** - Normalize phone/email/dates before matching
2. **Add Validation** - Check MVS (Minimal Viable Sets), orphans, type mismatches
3. **Write Integration Tests** - End-to-end tests with pytest
4. **Deploy** - Use the validated matcher in production

## Files

- `test_harness.py` - Main test runner
- `strategy_analyzer.py` - Individual strategy analysis
- `ground_truth.py` - Expected mapping definitions
- `reports/` - Generated test reports
- `test_data/` - (Optional) Sample spreadsheet files
