#!/usr/bin/env python3
"""
Comprehensive Test Suite with Pre-Cleaning

Runs the full comprehensive test suite (10 tests, 75 fields) with pre-cleaning enabled.
Compares results against the baseline (89.3% without pre-cleaning).

Goal: Achieve 95%+ accuracy with pre-cleaning.
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.hybrid_matcher import HybridMatcher
from app.cleaners.config import CleaningConfig
from app.cleaners.rules.column_name import ColumnNameCleaningRule
from ground_truth import GROUND_TRUTH, ACCURACY_THRESHOLDS, get_threshold, is_critical
import pandas as pd


class ComprehensiveCleaningResults:
    """Stores comprehensive test results with pre-cleaning comparison."""

    def __init__(self):
        self.test_cases = []
        self.start_time = datetime.now()
        self.end_time = None

    def add_test_case(self, raw_result: Dict, cleaned_result: Dict):
        """Add a test case result."""
        self.test_cases.append({
            "test_name": raw_result["test_name"],
            "test_key": raw_result["test_key"],
            "raw": raw_result,
            "cleaned": cleaned_result,
            "improvement": cleaned_result["accuracy"] - raw_result["accuracy"],
        })

    def finalize(self):
        """Finalize results."""
        self.end_time = datetime.now()

    def get_summary(self) -> Dict:
        """Get overall summary statistics."""
        total_fields = sum(r["raw"]["total_fields"] for r in self.test_cases)
        raw_correct = sum(r["raw"]["correct"] for r in self.test_cases)
        cleaned_correct = sum(r["cleaned"]["correct"] for r in self.test_cases)

        raw_passed = sum(1 for r in self.test_cases if r["raw"]["passed"])
        cleaned_passed = sum(1 for r in self.test_cases if r["cleaned"]["passed"])

        return {
            "total_test_cases": len(self.test_cases),
            "total_fields": total_fields,
            "raw_correct": raw_correct,
            "cleaned_correct": cleaned_correct,
            "raw_accuracy": raw_correct / total_fields if total_fields > 0 else 0.0,
            "cleaned_accuracy": cleaned_correct / total_fields if total_fields > 0 else 0.0,
            "improvement": (cleaned_correct - raw_correct) / total_fields if total_fields > 0 else 0.0,
            "raw_passed": raw_passed,
            "cleaned_passed": cleaned_passed,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            "timestamp": self.start_time.isoformat(),
        }


def clean_column_names(column_names: List[str]) -> Tuple[List[str], Dict[str, str]]:
    """
    Clean column names using the pre-cleaning rules.

    Args:
        column_names: Original column names

    Returns:
        Tuple of (cleaned_names, mappings)
    """
    config = CleaningConfig.default()
    rule = ColumnNameCleaningRule(config)

    # Create a dummy DataFrame with the columns
    dummy_df = pd.DataFrame(columns=column_names)

    # Apply cleaning
    result = rule.clean(dummy_df)

    # Extract cleaned names and mappings
    cleaned_names = result.df.columns.tolist()
    mappings = {}

    for original, cleaned in zip(column_names, cleaned_names):
        mappings[original] = cleaned

    return cleaned_names, mappings


def test_matcher_with_cleaning(
    matcher: HybridMatcher,
    df: pd.DataFrame,
    ground_truth: Dict[str, Tuple[str, str]],
    test_name: str,
    test_key: str
) -> Tuple[Dict, Dict, Dict[str, str]]:
    """
    Test matcher with both raw and cleaned column names.

    Returns:
        Tuple of (raw_result, cleaned_result, column_mappings)
    """
    original_columns = df.columns.tolist()

    # Clean the column names
    cleaned_columns, column_mappings = clean_column_names(original_columns)

    # Count how many columns actually changed
    changes = sum(1 for orig, cleaned in column_mappings.items() if orig != cleaned)

    print(f"\n{'='*80}")
    print(f"Testing: {test_name}")
    print(f"{'='*80}")
    print(f"Columns: {len(original_columns)}")
    print(f"Columns changed by pre-cleaning: {changes}")

    if changes > 0:
        print(f"\nColumn Mappings:")
        for orig, cleaned in column_mappings.items():
            if orig != cleaned:
                print(f"  '{orig}' → '{cleaned}'")

    # Test with RAW column names
    print(f"\n{'-'*80}")
    print(f"RAW Results:")
    print(f"{'-'*80}")
    raw_result = test_matcher(matcher, original_columns, ground_truth, test_name, test_key, "RAW")

    # Test with CLEANED column names
    print(f"\n{'-'*80}")
    print(f"CLEANED Results:")
    print(f"{'-'*80}")

    # Need to update ground truth keys to use cleaned column names
    cleaned_ground_truth = {}
    for original_col, cleaned_col in column_mappings.items():
        if original_col in ground_truth:
            cleaned_ground_truth[cleaned_col] = ground_truth[original_col]

    cleaned_result = test_matcher(matcher, cleaned_columns, cleaned_ground_truth, test_name, test_key, "CLEANED")

    # Print comparison
    print(f"\n{'-'*80}")
    print(f"COMPARISON:")
    print(f"{'-'*80}")
    print(f"RAW:     {raw_result['correct']}/{raw_result['total_fields']} ({raw_result['accuracy']*100:.1f}%) - {'✓ PASS' if raw_result['passed'] else '✗ FAIL'}")
    print(f"CLEANED: {cleaned_result['correct']}/{cleaned_result['total_fields']} ({cleaned_result['accuracy']*100:.1f}%) - {'✓ PASS' if cleaned_result['passed'] else '✗ FAIL'}")
    improvement = cleaned_result['accuracy'] - raw_result['accuracy']
    if improvement > 0:
        print(f"IMPROVEMENT: +{improvement*100:.1f} percentage points ⭐")
    elif improvement < 0:
        print(f"DEGRADATION: {improvement*100:.1f} percentage points ⚠️")
    else:
        print(f"NO CHANGE")

    return raw_result, cleaned_result, column_mappings


def test_matcher(
    matcher: HybridMatcher,
    column_names: List[str],
    ground_truth: Dict[str, Tuple[str, str]],
    test_name: str,
    test_key: str,
    label: str
) -> Dict:
    """Test matcher against column names with ground truth."""
    correct = 0
    incorrect = 0
    missing = 0
    column_results = []

    for column in column_names:
        expected = ground_truth.get(column)

        # Get match from hybrid matcher
        candidates = matcher.match(
            header=column,
            sheet_name=test_name,
            column_names=column_names
        )

        if candidates:
            predicted = (candidates[0]["model"], candidates[0]["field"])
            confidence = candidates[0]["confidence"]
            method = candidates[0]["method"]

            if expected:
                if predicted == expected:
                    status = "✓"
                    correct += 1
                elif predicted[1] is None:
                    status = "✗ MISS"
                    missing += 1
                else:
                    status = "✗ WRONG"
                    incorrect += 1

                print(f"{status:8} | {column[:35]:35} → {predicted[0]:20}.{predicted[1] or 'None':20}")
                if status == "✗ WRONG":
                    print(f"         | Expected: {expected[0]:20}.{expected[1]:20}")

                column_results.append({
                    "column": column,
                    "expected_model": expected[0],
                    "expected_field": expected[1],
                    "predicted_model": predicted[0],
                    "predicted_field": predicted[1],
                    "confidence": confidence,
                    "method": method,
                    "status": status,
                })
        else:
            if expected:
                status = "✗ MISS"
                missing += 1
                print(f"{status:8} | {column[:35]:35} → NO MATCH")
                column_results.append({
                    "column": column,
                    "expected_model": expected[0],
                    "expected_field": expected[1],
                    "predicted_model": None,
                    "predicted_field": None,
                    "confidence": 0.0,
                    "method": "none",
                    "status": "MISSING",
                })

    # Calculate metrics
    total = len(ground_truth)
    accuracy = correct / total if total > 0 else 0.0
    threshold = get_threshold(test_key)
    passed = accuracy >= threshold

    return {
        "label": label,
        "test_name": test_name,
        "test_key": test_key,
        "total_fields": total,
        "correct": correct,
        "incorrect": incorrect,
        "missing": missing,
        "accuracy": accuracy,
        "threshold": threshold,
        "passed": passed,
        "critical": is_critical(test_key),
        "column_results": column_results,
    }


def run_comprehensive_with_cleaning():
    """Run comprehensive test suite with pre-cleaning."""
    print("="*80)
    print("COMPREHENSIVE TEST SUITE WITH PRE-CLEANING")
    print("="*80)
    print(f"Testing: 10 test cases, 75 total fields")
    print(f"Baseline: 89.3% accuracy (67/75 correct) WITHOUT pre-cleaning")
    print(f"Target: 95%+ accuracy WITH pre-cleaning")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize HybridMatcher
    dictionary_path = Path(__file__).parent.parent.parent.parent / "odoo-dictionary"
    print(f"\nInitializing HybridMatcher with dictionary: {dictionary_path}")
    matcher = HybridMatcher(dictionary_path=dictionary_path)

    # Initialize results collector
    results = ComprehensiveCleaningResults()

    # Test 1: Customers
    print("\n" + "="*80)
    print("TEST 1/10: CUSTOMERS (res.partner)")
    print("="*80)

    customer_df = pd.DataFrame({
        "Customer Name": ["Acme Corp", "TechStart Inc"],
        "Contact Email": ["sales@acme.com", "hello@techstart.com"],
        "Phone": ["+1-555-0100", "+1-555-0200"],
        "Street Address": ["123 Main St", "456 Tech Blvd"],
        "City": ["New York", "San Francisco"],
        "State": ["NY", "CA"],
        "Zip Code": ["10001", "94102"],
        "Annual Revenue": [1000000, 500000],
        "Customer ID": ["CUST001", "CUST002"],
    })

    raw, cleaned, _ = test_matcher_with_cleaning(matcher, customer_df, GROUND_TRUTH["customers"], "Customers", "customers")
    results.add_test_case(raw, cleaned)

    # Test 2: Products
    print("\n" + "="*80)
    print("TEST 2/10: PRODUCTS (product.product)")
    print("="*80)

    products_df = pd.DataFrame({
        "Product Name": ["Widget A", "Gadget B"],
        "SKU": ["WID-001", "GAD-002"],
        "Sale Price": [29.99, 49.99],
        "Cost Price": [15.00, 25.00],
        "Category": ["Electronics", "Hardware"],
        "Barcode": ["1234567890123", "9876543210987"],
        "Active": [True, True],
    })

    raw, cleaned, _ = test_matcher_with_cleaning(matcher, products_df, GROUND_TRUTH["products"], "Products", "products")
    results.add_test_case(raw, cleaned)

    # Test 3: Sales Orders
    print("\n" + "="*80)
    print("TEST 3/10: SALES ORDERS (sale.order)")
    print("="*80)

    orders_df = pd.DataFrame({
        "Order Number": ["SO-001", "SO-002"],
        "Customer": ["Acme Corp", "TechStart Inc"],
        "Order Date": ["2024-01-15", "2024-01-16"],
        "Total": [1500.00, 2500.00],
        "Status": ["confirmed", "draft"],
        "Salesperson": ["John Doe", "Jane Smith"],
    })

    raw, cleaned, _ = test_matcher_with_cleaning(matcher, orders_df, GROUND_TRUTH["sales_orders"], "Sales Orders", "sales_orders")
    results.add_test_case(raw, cleaned)

    # Test 4: Invoices
    print("\n" + "="*80)
    print("TEST 4/10: INVOICES (account.move)")
    print("="*80)

    invoices_df = pd.DataFrame({
        "Invoice Number": ["INV-001", "INV-002"],
        "Customer": ["Acme Corp", "TechStart Inc"],
        "Invoice Date": ["2024-01-15", "2024-01-16"],
        "Due Date": ["2024-02-15", "2024-02-16"],
        "Subtotal": [1000.00, 2000.00],
        "Tax": [100.00, 200.00],
        "Total": [1100.00, 2200.00],
        "Status": ["posted", "draft"],
    })

    raw, cleaned, _ = test_matcher_with_cleaning(matcher, invoices_df, GROUND_TRUTH["invoices"], "Invoices", "invoices")
    results.add_test_case(raw, cleaned)

    # Test 5: Leads
    print("\n" + "="*80)
    print("TEST 5/10: LEADS (crm.lead)")
    print("="*80)

    leads_df = pd.DataFrame({
        "Opportunity Title": ["Website Redesign", "ERP Implementation"],
        "Email": ["contact@prospect.com", "info@bigcorp.com"],
        "Phone": ["+1-555-0300", "+1-555-0400"],
        "Street Address (Contact)": ["789 Business Ave", "321 Commerce St"],
        "City (Contact)": ["Boston", "Chicago"],
        "Zip (Contact)": ["02101", "60601"],
        "Lead Status": ["Qualified", "New"],
        "Salesperson": ["Alice Johnson", "Bob Williams"],
        "Source": ["Website", "Referral"],
        "Expected Revenue": [50000, 100000],
    })

    raw, cleaned, _ = test_matcher_with_cleaning(matcher, leads_df, GROUND_TRUTH["leads"], "Leads", "leads")
    results.add_test_case(raw, cleaned)

    # Test 6: Projects
    print("\n" + "="*80)
    print("TEST 6/10: PROJECTS (project.project)")
    print("="*80)

    projects_df = pd.DataFrame({
        "Project Name": ["Website Development", "Mobile App"],
        "Customer": ["Acme Corp", "TechStart Inc"],
        "Project Manager": ["Alice Johnson", "Bob Williams"],
        "Start Date": ["2024-01-01", "2024-02-01"],
        "Deadline": ["2024-06-30", "2024-08-31"],
        "Active": [True, True],
    })

    raw, cleaned, _ = test_matcher_with_cleaning(matcher, projects_df, GROUND_TRUTH["projects"], "Projects", "projects")
    results.add_test_case(raw, cleaned)

    # Test 7: Tasks
    print("\n" + "="*80)
    print("TEST 7/10: TASKS (project.task)")
    print("="*80)

    tasks_df = pd.DataFrame({
        "Task Title": ["Design Homepage", "Implement Backend"],
        "Project": ["Website Development", "Mobile App"],
        "Assigned To": ["Designer 1", "Developer 1"],
        "Due Date": ["2024-02-15", "2024-03-31"],
        "Priority": ["High", "Medium"],
        "Status": ["In Progress", "Ready"],
    })

    raw, cleaned, _ = test_matcher_with_cleaning(matcher, tasks_df, GROUND_TRUTH["tasks"], "Tasks", "tasks")
    results.add_test_case(raw, cleaned)

    # Test 8: Vehicles
    print("\n" + "="*80)
    print("TEST 8/10: VEHICLES (fleet.vehicle)")
    print("="*80)

    vehicles_df = pd.DataFrame({
        "VIN": ["1HGBH41JXMN109186", "2HGFG12857H554897"],
        "License Plate": ["ABC-1234", "XYZ-9876"],
        "Vehicle Model": ["Toyota Camry", "Honda Accord"],
        "Driver": ["John Doe", "Jane Smith"],
        "Acquisition Date": ["2020-01-15", "2021-03-20"],
        "Odometer": [45000, 32000],
        "Active": [True, True],
    })

    raw, cleaned, _ = test_matcher_with_cleaning(matcher, vehicles_df, GROUND_TRUTH["vehicles"], "Vehicles", "vehicles")
    results.add_test_case(raw, cleaned)

    # Test 9: Sale Order Lines
    print("\n" + "="*80)
    print("TEST 9/10: SALE ORDER LINES (sale.order.line)")
    print("="*80)

    sale_lines_df = pd.DataFrame({
        "Order Number": ["SO-001", "SO-001"],
        "Product": ["Widget A", "Gadget B"],
        "Description": ["High-quality widget", "Premium gadget"],
        "Quantity": [10, 5],
        "Unit Price": [29.99, 49.99],
        "Discount": [10.0, 5.0],
        "Subtotal": [269.91, 237.45],
    })

    raw, cleaned, _ = test_matcher_with_cleaning(matcher, sale_lines_df, GROUND_TRUTH["sale_order_lines"], "Sale Order Lines", "sale_order_lines")
    results.add_test_case(raw, cleaned)

    # Test 10: Financial Analysis
    print("\n" + "="*80)
    print("TEST 10/10: FINANCIAL ANALYSIS (account.analytic.line)")
    print("="*80)

    financial_df = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "Product": ["Widget A", "Gadget B"],
        "Segment": ["Enterprise", "SMB"],
        "Country": ["USA", "Canada"],
        "Units Sold": [100, 50],
        "Revenue": [2999.00, 2499.50],
        "COGS": [1500.00, 1250.00],
        "Profit": [1499.00, 1249.50],
        "Discount Band": ["None", "5%"],
    })

    raw, cleaned, _ = test_matcher_with_cleaning(matcher, financial_df, GROUND_TRUTH["financial_analysis"], "Financial Analysis", "financial_analysis")
    results.add_test_case(raw, cleaned)

    # Finalize and print summary
    results.finalize()
    print_comprehensive_summary(results)

    return results


def print_comprehensive_summary(results: ComprehensiveCleaningResults):
    """Print comprehensive summary of all tests."""
    summary = results.get_summary()

    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUITE SUMMARY")
    print("="*80)

    print(f"\nOverall Results:")
    print(f"  Test Cases:    {summary['total_test_cases']}")
    print(f"  Total Fields:  {summary['total_fields']}")

    print(f"\nRAW (No Pre-Cleaning):")
    print(f"  Correct:       {summary['raw_correct']}/{summary['total_fields']} ({summary['raw_accuracy']*100:.1f}%)")
    print(f"  Tests Passed:  {summary['raw_passed']}/{summary['total_test_cases']}")

    print(f"\nCLEANED (With Pre-Cleaning):")
    print(f"  Correct:       {summary['cleaned_correct']}/{summary['total_fields']} ({summary['cleaned_accuracy']*100:.1f}%)")
    print(f"  Tests Passed:  {summary['cleaned_passed']}/{summary['total_test_cases']}")

    print(f"\nIMPROVEMENT:")
    print(f"  Accuracy:      {summary['improvement']*100:+.1f} percentage points")
    print(f"  Fields Fixed:  +{summary['cleaned_correct'] - summary['raw_correct']}")
    print(f"  Tests Fixed:   +{summary['cleaned_passed'] - summary['raw_passed']}")

    print(f"\n{'='*80}")
    print("PER-TEST CASE RESULTS")
    print(f"{'='*80}")
    print(f"{'Test Case':<30} {'RAW':<15} {'CLEANED':<15} {'Improvement'}")
    print("-"*80)

    for test in results.test_cases:
        raw_acc = test["raw"]["accuracy"] * 100
        cleaned_acc = test["cleaned"]["accuracy"] * 100
        improvement = test["improvement"] * 100

        raw_status = "✓" if test["raw"]["passed"] else "✗"
        cleaned_status = "✓" if test["cleaned"]["passed"] else "✗"

        improvement_str = f"{improvement:+6.1f}%" if improvement != 0 else "  0.0%"
        star = " ⭐" if improvement > 5 else ""

        print(f"{test['test_name']:<30} {raw_status} {raw_acc:>5.1f}%        {cleaned_status} {cleaned_acc:>5.1f}%        {improvement_str}{star}")

    print("-"*80)

    # Overall verdict
    print(f"\n{'='*80}")
    if summary['cleaned_accuracy'] >= 0.95:
        print("✓✓✓ EXCELLENT: Cleaned accuracy ≥95% - TARGET ACHIEVED!")
    elif summary['cleaned_accuracy'] >= 0.90:
        print("✓✓ GOOD: Cleaned accuracy ≥90% - Close to target")
    elif summary['cleaned_accuracy'] >= 0.85:
        print("✓ ACCEPTABLE: Cleaned accuracy ≥85% - Improvements needed")
    else:
        print("✗ NEEDS WORK: Cleaned accuracy <85%")

    if summary['improvement'] > 0.05:
        print(f"✓✓✓ SIGNIFICANT IMPROVEMENT: Pre-cleaning improves accuracy by {summary['improvement']*100:.1f}%")
    elif summary['improvement'] > 0.01:
        print(f"✓✓ MODERATE IMPROVEMENT: Pre-cleaning improves accuracy by {summary['improvement']*100:.1f}%")
    elif summary['improvement'] > 0:
        print(f"✓ MINOR IMPROVEMENT: Pre-cleaning improves accuracy by {summary['improvement']*100:.1f}%")
    else:
        print(f"⚠ NO IMPROVEMENT from pre-cleaning")

    print(f"{'='*80}")
    print(f"\nDuration: {summary['duration_seconds']:.1f} seconds")

    # Show which tests improved
    print(f"\n{'='*80}")
    print("TESTS WITH IMPROVEMENTS:")
    print(f"{'='*80}")
    improved_tests = [t for t in results.test_cases if t["improvement"] > 0]
    if improved_tests:
        for test in improved_tests:
            print(f"  • {test['test_name']}: {test['improvement']*100:+.1f}% ({test['raw']['correct']} → {test['cleaned']['correct']} correct)")
    else:
        print("  None - all tests already at maximum accuracy")


def save_results_json(results: ComprehensiveCleaningResults, output_path: Path):
    """Save results to JSON file."""
    data = {
        "summary": results.get_summary(),
        "test_cases": results.test_cases,
    }

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\n✓ Results saved to: {output_path}")


if __name__ == "__main__":
    results = run_comprehensive_with_cleaning()

    # Save JSON results
    output_dir = Path(__file__).parent / "reports"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"comprehensive_with_cleaning_{timestamp}.json"
    save_results_json(results, json_path)

    # Exit with appropriate code
    summary = results.get_summary()
    if summary['cleaned_accuracy'] >= 0.95:
        print("\n✓✓✓ SUCCESS: Target accuracy of 95% achieved!")
        sys.exit(0)
    elif summary['cleaned_accuracy'] >= 0.90:
        print(f"\n✓ CLOSE: Achieved {summary['cleaned_accuracy']*100:.1f}%, target was 95%")
        sys.exit(0)
    else:
        print(f"\n⚠ Target not reached: {summary['cleaned_accuracy']*100:.1f}% < 95%")
        sys.exit(1)
