#!/usr/bin/env python3
"""
Comprehensive Test Suite for HybridMatcher

Tests the HybridMatcher against 10 test cases covering major Odoo business entities:
1. Customers (res.partner)
2. Products (product.product)
3. Sales Orders (sale.order)
4. Invoices (account.move)
5. Leads (crm.lead)
6. Projects (project.project)
7. Tasks (project.task)
8. Vehicles (fleet.vehicle)
9. Sale Order Lines (sale.order.line)
10. Financial Analysis (account.analytic.line)

Total: 75 fields across 10 test cases
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.hybrid_matcher import HybridMatcher
from ground_truth import GROUND_TRUTH, ACCURACY_THRESHOLDS, get_threshold, is_critical
import pandas as pd


class ComprehensiveTestResults:
    """Stores comprehensive test results."""

    def __init__(self):
        self.test_cases = []
        self.start_time = datetime.now()
        self.end_time = None

    def add_test_case(self, result: Dict):
        """Add a test case result."""
        self.test_cases.append(result)

    def finalize(self):
        """Finalize results."""
        self.end_time = datetime.now()

    def get_summary(self) -> Dict:
        """Get overall summary statistics."""
        total_fields = sum(r["total_fields"] for r in self.test_cases)
        total_correct = sum(r["correct"] for r in self.test_cases)
        total_incorrect = sum(r["incorrect"] for r in self.test_cases)
        total_missing = sum(r["missing"] for r in self.test_cases)

        passed = sum(1 for r in self.test_cases if r["passed"])
        failed = sum(1 for r in self.test_cases if not r["passed"])

        return {
            "total_test_cases": len(self.test_cases),
            "passed": passed,
            "failed": failed,
            "total_fields": total_fields,
            "correct": total_correct,
            "incorrect": total_incorrect,
            "missing": total_missing,
            "overall_accuracy": total_correct / total_fields if total_fields > 0 else 0.0,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            "timestamp": self.start_time.isoformat(),
        }


def test_hybrid_matcher_comprehensive():
    """Run comprehensive test suite for HybridMatcher."""
    print("="*80)
    print("COMPREHENSIVE HYBRIDMATCHER TEST SUITE")
    print("="*80)
    print(f"Testing: 10 test cases, 75 total fields")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize HybridMatcher
    dictionary_path = Path(__file__).parent.parent.parent.parent / "odoo-dictionary"

    print(f"\nInitializing HybridMatcher with dictionary: {dictionary_path}")
    matcher = HybridMatcher(dictionary_path=dictionary_path)

    # Initialize results collector
    results = ComprehensiveTestResults()

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

    result = test_matcher(matcher, customer_df, GROUND_TRUTH["customers"], "Customers", "customers")
    results.add_test_case(result)

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

    result = test_matcher(matcher, products_df, GROUND_TRUTH["products"], "Products", "products")
    results.add_test_case(result)

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

    result = test_matcher(matcher, orders_df, GROUND_TRUTH["sales_orders"], "Sales Orders", "sales_orders")
    results.add_test_case(result)

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

    result = test_matcher(matcher, invoices_df, GROUND_TRUTH["invoices"], "Invoices", "invoices")
    results.add_test_case(result)

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

    result = test_matcher(matcher, leads_df, GROUND_TRUTH["leads"], "Leads", "leads")
    results.add_test_case(result)

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

    result = test_matcher(matcher, projects_df, GROUND_TRUTH["projects"], "Projects", "projects")
    results.add_test_case(result)

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

    result = test_matcher(matcher, tasks_df, GROUND_TRUTH["tasks"], "Tasks", "tasks")
    results.add_test_case(result)

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

    result = test_matcher(matcher, vehicles_df, GROUND_TRUTH["vehicles"], "Vehicles", "vehicles")
    results.add_test_case(result)

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

    result = test_matcher(matcher, sale_lines_df, GROUND_TRUTH["sale_order_lines"], "Sale Order Lines", "sale_order_lines")
    results.add_test_case(result)

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

    result = test_matcher(matcher, financial_df, GROUND_TRUTH["financial_analysis"], "Financial Analysis", "financial_analysis")
    results.add_test_case(result)

    # Finalize and print summary
    results.finalize()
    print_comprehensive_summary(results)

    return results


def test_matcher(
    matcher: HybridMatcher,
    df: pd.DataFrame,
    ground_truth: Dict[str, Tuple[str, str]],
    test_name: str,
    test_key: str
) -> Dict:
    """Test matcher against a dataframe with ground truth."""
    column_names = df.columns.tolist()

    correct = 0
    incorrect = 0
    missing = 0
    column_results = []

    print(f"\nColumns: {len(column_names)}")
    print(f"Ground truth entries: {len(ground_truth)}")
    print(f"Accuracy threshold: {get_threshold(test_key)*100:.0f}%")
    print("\nResults:")
    print("-" * 80)

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
            rationale = candidates[0].get("rationale", "")

            if expected:
                if predicted == expected:
                    status = "✓ CORRECT"
                    correct += 1
                elif predicted[1] is None:
                    status = "✗ MISSING "
                    missing += 1
                else:
                    status = "✗ WRONG  "
                    incorrect += 1

                print(f"{status} | {column:25} → {predicted[0]:25}.{predicted[1] or 'None':25} (conf: {confidence:.2f}, method: {method})")
                if status == "✗ WRONG  ":
                    print(f"         | Expected: {expected[0]:25}.{expected[1]:25}")

                column_results.append({
                    "column": column,
                    "expected_model": expected[0],
                    "expected_field": expected[1],
                    "predicted_model": predicted[0],
                    "predicted_field": predicted[1],
                    "confidence": confidence,
                    "method": method,
                    "status": status.split()[1],
                    "rationale": rationale,
                })
            else:
                print(f"  NO GT  | {column:25} → {predicted[0]:25}.{predicted[1] or 'None':25} (conf: {confidence:.2f})")
        else:
            if expected:
                status = "✗ MISSING "
                missing += 1
                print(f"{status} | {column:25} → NO MATCH")
                column_results.append({
                    "column": column,
                    "expected_model": expected[0],
                    "expected_field": expected[1],
                    "predicted_model": None,
                    "predicted_field": None,
                    "confidence": 0.0,
                    "method": "none",
                    "status": "MISSING",
                    "rationale": "No match found",
                })
            else:
                print(f"  NO GT  | {column:25} → NO MATCH")

    # Calculate metrics
    total = len(ground_truth)
    accuracy = correct / total if total > 0 else 0.0
    threshold = get_threshold(test_key)
    passed = accuracy >= threshold

    print("\n" + "-" * 80)
    print(f"SUMMARY:")
    print(f"  Correct:   {correct}/{total} ({accuracy*100:.1f}%)")
    print(f"  Incorrect: {incorrect}/{total}")
    print(f"  Missing:   {missing}/{total}")
    print(f"  Accuracy:  {accuracy*100:.1f}%")
    print(f"  Threshold: {threshold*100:.0f}%")
    print(f"  Status:    {'✓ PASS' if passed else '✗ FAIL'}")
    if is_critical(test_key):
        print(f"  Critical:  YES")

    return {
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


def print_comprehensive_summary(results: ComprehensiveTestResults):
    """Print comprehensive summary of all tests."""
    summary = results.get_summary()

    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUITE SUMMARY")
    print("="*80)

    print(f"\nOverall Results:")
    print(f"  Test Cases: {summary['total_test_cases']}")
    print(f"  Passed:     {summary['passed']}")
    print(f"  Failed:     {summary['failed']}")
    print(f"  Pass Rate:  {summary['passed']/summary['total_test_cases']*100:.1f}%")

    print(f"\nField-Level Results:")
    print(f"  Total Fields: {summary['total_fields']}")
    print(f"  Correct:      {summary['correct']} ({summary['correct']/summary['total_fields']*100:.1f}%)")
    print(f"  Incorrect:    {summary['incorrect']} ({summary['incorrect']/summary['total_fields']*100:.1f}%)")
    print(f"  Missing:      {summary['missing']} ({summary['missing']/summary['total_fields']*100:.1f}%)")

    print(f"\nOverall Accuracy: {summary['overall_accuracy']*100:.1f}%")
    print(f"Duration: {summary['duration_seconds']:.1f} seconds")

    print(f"\n{'='*80}")
    print("PER-TEST CASE RESULTS")
    print(f"{'='*80}")
    print(f"{'Test Case':<30} {'Accuracy':<12} {'Threshold':<12} {'Status':<8} {'Critical'}")
    print("-"*80)

    for test in results.test_cases:
        status = "✓ PASS" if test["passed"] else "✗ FAIL"
        critical = "YES" if test["critical"] else "NO"
        print(f"{test['test_name']:<30} {test['accuracy']*100:>6.1f}% ({test['correct']:>2}/{test['total_fields']:<2})  {test['threshold']*100:>6.0f}%       {status:<8} {critical}")

    print("-"*80)

    # Overall status
    print(f"\n{'='*80}")
    if summary['overall_accuracy'] >= 0.85:
        print("✓✓✓ EXCELLENT: Overall accuracy ≥85% - Production ready!")
    elif summary['overall_accuracy'] >= 0.80:
        print("✓✓ GOOD: Overall accuracy ≥80% - Minor improvements recommended")
    elif summary['overall_accuracy'] >= 0.75:
        print("✓ ACCEPTABLE: Overall accuracy ≥75% - Improvements needed")
    else:
        print("✗ POOR: Overall accuracy <75% - Significant improvements required")
    print(f"{'='*80}")


def save_results_json(results: ComprehensiveTestResults, output_path: Path):
    """Save results to JSON file."""
    data = {
        "summary": results.get_summary(),
        "test_cases": results.test_cases,
    }

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\n✓ Results saved to: {output_path}")


if __name__ == "__main__":
    results = test_hybrid_matcher_comprehensive()

    # Save JSON results
    output_dir = Path(__file__).parent / "reports"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"comprehensive_results_{timestamp}.json"
    save_results_json(results, json_path)

    # Exit with appropriate code
    summary = results.get_summary()
    if summary['overall_accuracy'] >= 0.80:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Needs improvement
