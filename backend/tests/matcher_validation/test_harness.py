#!/usr/bin/env python3
"""
Matcher Validation Test Harness

This script validates the complex field mapper by:
1. Running it against real test spreadsheets with known ground truth
2. Measuring each strategy's contribution to correct matches
3. Identifying false positives and missed mappings
4. Generating detailed performance reports

Usage:
    python test_harness.py [--verbose] [--report-dir ./reports]
"""
import sys
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import argparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from app.field_mapper.main import DeterministicFieldMapper
    from app.field_mapper.core.data_structures import FieldMapping
    from app.field_mapper.matching.matching_pipeline import MatchingPipeline
except ImportError as e:
    print(f"ERROR: Could not import field_mapper: {e}")
    print("Make sure you're running from the backend directory")
    sys.exit(1)


class MatcherTestHarness:
    """Test harness for validating the field mapper."""

    def __init__(self, dictionary_path: Path, verbose: bool = False):
        """
        Initialize the test harness.

        Args:
            dictionary_path: Path to odoo-dictionary folder
            verbose: Enable verbose output
        """
        self.dictionary_path = dictionary_path
        self.verbose = verbose
        self.mapper = None
        self.results = []

    def initialize_mapper(self) -> bool:
        """Initialize the field mapper with Odoo dictionary."""
        try:
            print(f"Initializing mapper with dictionary at: {self.dictionary_path}")
            self.mapper = DeterministicFieldMapper(dictionary_path=self.dictionary_path)
            stats = self.mapper.get_statistics()
            print(f"✓ Mapper initialized successfully")
            print(f"  - Models: {stats['knowledge_base']['total_models']}")
            print(f"  - Fields: {stats['knowledge_base']['total_fields']}")
            print(f"  - Selections: {stats['knowledge_base']['total_selections']}")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize mapper: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_ground_truth(self, test_case_name: str) -> Dict[str, Tuple[str, str]]:
        """
        Load ground truth mappings for a test case.

        Args:
            test_case_name: Name of the test case

        Returns:
            Dict mapping column names to (model, field) tuples
        """
        from ground_truth import GROUND_TRUTH

        if test_case_name not in GROUND_TRUTH:
            print(f"WARNING: No ground truth defined for '{test_case_name}'")
            return {}

        return GROUND_TRUTH[test_case_name]

    def run_test_case(
        self,
        test_name: str,
        df: pd.DataFrame,
        ground_truth: Dict[str, Tuple[str, str]],
        sheet_name: str = "Sheet1"
    ) -> Dict:
        """
        Run the mapper on a test case and compare against ground truth.

        Args:
            test_name: Name of the test
            df: DataFrame to map
            ground_truth: Expected mappings {column: (model, field)}
            sheet_name: Sheet name

        Returns:
            Dict with test results
        """
        print(f"\n{'='*80}")
        print(f"TEST: {test_name}")
        print(f"{'='*80}")
        print(f"Columns: {len(df.columns)}")
        print(f"Ground truth mappings: {len(ground_truth)}")

        # Run the mapper
        try:
            mappings = self.mapper.map_dataframe(df, sheet_name=sheet_name)
        except Exception as e:
            print(f"✗ Mapping failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "test_name": test_name,
                "status": "ERROR",
                "error": str(e)
            }

        # Analyze results
        results = {
            "test_name": test_name,
            "status": "COMPLETED",
            "timestamp": datetime.now().isoformat(),
            "total_columns": len(df.columns),
            "columns_mapped": sum(1 for m in mappings.values() if m),
            "columns_unmapped": sum(1 for m in mappings.values() if not m),
            "correct_mappings": 0,
            "incorrect_mappings": 0,
            "missing_mappings": 0,
            "false_positives": 0,
            "strategy_performance": defaultdict(lambda: {"correct": 0, "incorrect": 0, "total": 0}),
            "column_results": [],
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0, "none": 0},
        }

        # Evaluate each column
        for column_name in df.columns:
            field_mappings = mappings.get(column_name, [])
            expected = ground_truth.get(column_name)

            column_result = {
                "column": column_name,
                "expected": expected,
                "predicted": None,
                "confidence": 0.0,
                "status": "UNKNOWN",
                "strategies_used": [],
                "alternatives": []
            }

            if field_mappings:
                top_mapping = field_mappings[0]
                predicted = (top_mapping.target_model, top_mapping.target_field)
                confidence = top_mapping.confidence
                strategy = top_mapping.matching_strategy

                column_result["predicted"] = predicted
                column_result["confidence"] = confidence
                column_result["strategies_used"] = [strategy]
                column_result["alternatives"] = [
                    (m.target_model, m.target_field, m.confidence)
                    for m in field_mappings[1:6]  # Top 5 alternatives
                ]

                # Classify confidence
                if confidence >= 0.8:
                    results["confidence_distribution"]["high"] += 1
                elif confidence >= 0.6:
                    results["confidence_distribution"]["medium"] += 1
                elif confidence > 0:
                    results["confidence_distribution"]["low"] += 1
                else:
                    results["confidence_distribution"]["none"] += 1

                # Check correctness
                if expected:
                    if predicted == expected:
                        results["correct_mappings"] += 1
                        column_result["status"] = "CORRECT"
                        # Credit the strategy
                        results["strategy_performance"][strategy]["correct"] += 1
                    else:
                        results["incorrect_mappings"] += 1
                        column_result["status"] = "INCORRECT"
                        results["strategy_performance"][strategy]["incorrect"] += 1

                    results["strategy_performance"][strategy]["total"] += 1
                else:
                    # No ground truth - we can't validate
                    column_result["status"] = "NO_GROUND_TRUTH"
                    if predicted:
                        results["false_positives"] += 1
            else:
                # No mapping found
                if expected:
                    results["missing_mappings"] += 1
                    column_result["status"] = "MISSING"
                    results["confidence_distribution"]["none"] += 1

            results["column_results"].append(column_result)

        # Calculate accuracy metrics
        if ground_truth:
            total_gt = len(ground_truth)
            results["accuracy"] = results["correct_mappings"] / total_gt if total_gt > 0 else 0.0
            results["recall"] = results["correct_mappings"] / total_gt if total_gt > 0 else 0.0

            total_predicted = results["columns_mapped"]
            results["precision"] = (
                results["correct_mappings"] / total_predicted
                if total_predicted > 0 else 0.0
            )

        # Print summary
        self._print_test_summary(results)

        return results

    def _print_test_summary(self, results: Dict):
        """Print test result summary."""
        print(f"\n{'-'*80}")
        print("RESULTS SUMMARY")
        print(f"{'-'*80}")
        print(f"Total Columns:      {results['total_columns']}")
        print(f"  Mapped:           {results['columns_mapped']}")
        print(f"  Unmapped:         {results['columns_unmapped']}")
        print(f"\nAccuracy Metrics:")
        print(f"  Correct:          {results['correct_mappings']}")
        print(f"  Incorrect:        {results['incorrect_mappings']}")
        print(f"  Missing:          {results['missing_mappings']}")

        if "accuracy" in results:
            print(f"\n  Accuracy:         {results['accuracy']*100:.1f}%")
            print(f"  Precision:        {results['precision']*100:.1f}%")
            print(f"  Recall:           {results['recall']*100:.1f}%")

        print(f"\nConfidence Distribution:")
        print(f"  High (≥0.8):      {results['confidence_distribution']['high']}")
        print(f"  Medium (0.6-0.8): {results['confidence_distribution']['medium']}")
        print(f"  Low (<0.6):       {results['confidence_distribution']['low']}")
        print(f"  None (0):         {results['confidence_distribution']['none']}")

        print(f"\nStrategy Performance:")
        for strategy, perf in sorted(
            results['strategy_performance'].items(),
            key=lambda x: x[1]['correct'],
            reverse=True
        ):
            total = perf['total']
            correct = perf['correct']
            incorrect = perf['incorrect']
            accuracy = correct / total if total > 0 else 0.0
            print(f"  {strategy:30} {correct:3}/{total:3} ({accuracy*100:5.1f}%)")

    def generate_report(self, all_results: List[Dict], output_dir: Path):
        """
        Generate detailed HTML and JSON reports.

        Args:
            all_results: List of test results
            output_dir: Directory to save reports
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON report
        json_path = output_dir / f"matcher_validation_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n✓ JSON report saved to: {json_path}")

        # Generate HTML report
        html_path = output_dir / f"matcher_validation_{timestamp}.html"
        html_content = self._generate_html_report(all_results)
        with open(html_path, 'w') as f:
            f.write(html_content)
        print(f"✓ HTML report saved to: {html_path}")

        # Generate CSV of all column results
        csv_path = output_dir / f"column_results_{timestamp}.csv"
        self._generate_csv_report(all_results, csv_path)
        print(f"✓ CSV report saved to: {csv_path}")

    def _generate_html_report(self, all_results: List[Dict]) -> str:
        """Generate HTML report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Matcher Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .correct {{ background-color: #d4edda; }}
        .incorrect {{ background-color: #f8d7da; }}
        .missing {{ background-color: #fff3cd; }}
        .metric {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
        .summary {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Field Mapper Validation Report</h1>
    <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
"""

        # Overall summary
        total_tests = len(all_results)
        total_correct = sum(r.get("correct_mappings", 0) for r in all_results)
        total_incorrect = sum(r.get("incorrect_mappings", 0) for r in all_results)
        total_missing = sum(r.get("missing_mappings", 0) for r in all_results)
        total_columns = sum(r.get("total_columns", 0) for r in all_results)

        overall_accuracy = (
            total_correct / (total_correct + total_incorrect + total_missing)
            if (total_correct + total_incorrect + total_missing) > 0 else 0.0
        )

        html += f"""
    <div class="summary">
        <h2>Overall Summary</h2>
        <p>Tests Run: {total_tests}</p>
        <p>Total Columns: {total_columns}</p>
        <p class="metric">Overall Accuracy: {overall_accuracy*100:.1f}%</p>
        <p>Correct: {total_correct} | Incorrect: {total_incorrect} | Missing: {total_missing}</p>
    </div>
"""

        # Per-test results
        for result in all_results:
            test_name = result.get("test_name", "Unknown")
            accuracy = result.get("accuracy", 0.0)

            html += f"""
    <h2>Test: {test_name}</h2>
    <p>Accuracy: <span class="metric">{accuracy*100:.1f}%</span></p>

    <h3>Column Mappings</h3>
    <table>
        <tr>
            <th>Column</th>
            <th>Expected</th>
            <th>Predicted</th>
            <th>Confidence</th>
            <th>Status</th>
            <th>Strategy</th>
        </tr>
"""

            for col_result in result.get("column_results", []):
                column = col_result["column"]
                expected = col_result.get("expected", "N/A")
                predicted = col_result.get("predicted", "N/A")
                confidence = col_result.get("confidence", 0.0)
                status = col_result.get("status", "UNKNOWN")
                strategies = ", ".join(col_result.get("strategies_used", []))

                expected_str = f"{expected[0]}.{expected[1]}" if expected and expected != "N/A" else "N/A"
                predicted_str = f"{predicted[0]}.{predicted[1]}" if predicted and predicted != "N/A" else "N/A"

                status_class = status.lower()

                html += f"""
        <tr class="{status_class}">
            <td>{column}</td>
            <td>{expected_str}</td>
            <td>{predicted_str}</td>
            <td>{confidence:.2f}</td>
            <td>{status}</td>
            <td>{strategies}</td>
        </tr>
"""

            html += """
    </table>
"""

        html += """
</body>
</html>
"""
        return html

    def _generate_csv_report(self, all_results: List[Dict], csv_path: Path):
        """Generate CSV report of all column results."""
        rows = []
        for result in all_results:
            test_name = result.get("test_name", "Unknown")
            for col_result in result.get("column_results", []):
                expected = col_result.get("expected")
                predicted = col_result.get("predicted")

                rows.append({
                    "test_name": test_name,
                    "column": col_result["column"],
                    "expected_model": expected[0] if expected else "",
                    "expected_field": expected[1] if expected else "",
                    "predicted_model": predicted[0] if predicted else "",
                    "predicted_field": predicted[1] if predicted else "",
                    "confidence": col_result.get("confidence", 0.0),
                    "status": col_result.get("status", ""),
                    "strategy": ", ".join(col_result.get("strategies_used", [])),
                })

        df = pd.DataFrame(rows)
        df.to_csv(csv_path, index=False)


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Validate the field mapper")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--dictionary",
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / "odoo-dictionary",
        help="Path to odoo-dictionary folder"
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path(__file__).parent / "reports",
        help="Directory for reports"
    )
    args = parser.parse_args()

    # Initialize harness
    harness = MatcherTestHarness(
        dictionary_path=args.dictionary,
        verbose=args.verbose
    )

    if not harness.initialize_mapper():
        print("Failed to initialize mapper. Exiting.")
        sys.exit(1)

    # Run test cases
    all_results = []

    # Test 1: Customers
    print("\n" + "="*80)
    print("RUNNING TEST SUITE")
    print("="*80)

    customers_df = pd.DataFrame({
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

    customers_gt = harness.load_ground_truth("customers")
    result = harness.run_test_case("customers", customers_df, customers_gt, "Customers")
    all_results.append(result)

    # Test 2: Products
    products_df = pd.DataFrame({
        "Product Name": ["Widget A", "Gadget B"],
        "SKU": ["WID-001", "GAD-002"],
        "Sale Price": [29.99, 49.99],
        "Cost Price": [15.00, 25.00],
        "Category": ["Electronics", "Hardware"],
        "Barcode": ["1234567890123", "9876543210987"],
        "Active": [True, True],
    })

    products_gt = harness.load_ground_truth("products")
    result = harness.run_test_case("products", products_df, products_gt, "Products")
    all_results.append(result)

    # Test 3: Sales Orders
    orders_df = pd.DataFrame({
        "Order Number": ["SO-001", "SO-002"],
        "Customer": ["Acme Corp", "TechStart Inc"],
        "Order Date": ["2024-01-15", "2024-01-16"],
        "Total": [1500.00, 2500.00],
        "Status": ["confirmed", "draft"],
        "Salesperson": ["John Doe", "Jane Smith"],
    })

    orders_gt = harness.load_ground_truth("sales_orders")
    result = harness.run_test_case("sales_orders", orders_df, orders_gt, "Orders")
    all_results.append(result)

    # Generate reports
    harness.generate_report(all_results, args.report_dir)

    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)

    # Exit with error code if accuracy is too low
    overall_accuracy = sum(r.get("correct_mappings", 0) for r in all_results) / \
                      max(sum(r.get("total_columns", 0) for r in all_results), 1)

    if overall_accuracy < 0.7:
        print(f"\n⚠ WARNING: Overall accuracy {overall_accuracy*100:.1f}% is below 70% threshold")
        sys.exit(1)
    else:
        print(f"\n✓ SUCCESS: Overall accuracy {overall_accuracy*100:.1f}% meets threshold")
        sys.exit(0)


if __name__ == "__main__":
    main()
