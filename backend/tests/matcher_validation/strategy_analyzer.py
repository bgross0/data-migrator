#!/usr/bin/env python3
"""
Strategy Analyzer - Measures individual strategy contribution

This script analyzes each of the 8 matching strategies to determine:
1. Which strategies are most accurate
2. Which strategies add false positives
3. Optimal weight configurations
4. Which strategies can be disabled

Usage:
    python strategy_analyzer.py --test-case customers
"""
import sys
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import argparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from app.field_mapper.main import DeterministicFieldMapper
    from app.field_mapper.matching.matching_pipeline import MatchingPipeline
    from app.field_mapper.core.knowledge_base import OdooKnowledgeBase
    from app.field_mapper.profiling.column_profiler import ColumnProfiler
    from app.field_mapper.config.settings import FieldMapperSettings
except ImportError as e:
    print(f"ERROR: Could not import field_mapper: {e}")
    sys.exit(1)


class StrategyAnalyzer:
    """Analyze individual strategy performance."""

    def __init__(self, dictionary_path: Path):
        """Initialize analyzer."""
        self.dictionary_path = dictionary_path
        self.knowledge_base = None
        self.settings = FieldMapperSettings()
        self.pipeline = None

        # Strategy names
        self.strategies = [
            "ExactNameMatch",
            "LabelMatch",
            "SelectionValueMatch",
            "DataTypeCompatibility",
            "PatternMatch",
            "StatisticalSimilarity",
            "ContextualMatch",
            "FuzzyMatch",
        ]

    def initialize(self) -> bool:
        """Initialize knowledge base and pipeline."""
        try:
            print("Initializing knowledge base...")
            self.knowledge_base = OdooKnowledgeBase(dictionary_path=self.dictionary_path)
            self.knowledge_base.load_from_dictionary()

            print("Initializing pipeline...")
            self.pipeline = MatchingPipeline(
                knowledge_base=self.knowledge_base,
                settings=self.settings
            )

            print("✓ Analyzer initialized")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_individual_strategies(
        self,
        df: pd.DataFrame,
        ground_truth: Dict[str, Tuple[str, str]],
        sheet_name: str = "Sheet1"
    ) -> Dict:
        """
        Test each strategy individually to measure its contribution.

        Args:
            df: DataFrame to analyze
            ground_truth: Expected mappings
            sheet_name: Sheet name

        Returns:
            Dict with per-strategy results
        """
        print(f"\n{'='*80}")
        print(f"INDIVIDUAL STRATEGY ANALYSIS")
        print(f"{'='*80}")

        # Profile columns
        profiler = ColumnProfiler()
        column_profiles = profiler.profile_dataframe(df, sheet_name=sheet_name)

        results = {}

        for strategy_name in self.strategies:
            print(f"\nTesting strategy: {strategy_name}")

            # Enable only this strategy
            for s in self.pipeline.strategies:
                if strategy_name in s.__class__.__name__:
                    s.weight = 1.0
                else:
                    s.weight = 0.0

            # Run matching
            mappings = self.pipeline.match_sheet(column_profiles, sheet_name=sheet_name)

            # Evaluate
            correct = 0
            incorrect = 0
            missing = 0
            false_positives = 0

            for column_name in df.columns:
                field_mappings = mappings.get(column_name, [])
                expected = ground_truth.get(column_name)

                if field_mappings:
                    predicted = (field_mappings[0].target_model, field_mappings[0].target_field)
                    if expected:
                        if predicted == expected:
                            correct += 1
                        else:
                            incorrect += 1
                    else:
                        false_positives += 1
                else:
                    if expected:
                        missing += 1

            total = len(ground_truth)
            accuracy = correct / total if total > 0 else 0.0
            precision = correct / (correct + incorrect) if (correct + incorrect) > 0 else 0.0
            recall = correct / total if total > 0 else 0.0

            results[strategy_name] = {
                "correct": correct,
                "incorrect": incorrect,
                "missing": missing,
                "false_positives": false_positives,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
            }

            print(f"  Correct: {correct}/{total} ({accuracy*100:.1f}%)")
            print(f"  Precision: {precision*100:.1f}%")
            print(f"  Recall: {recall*100:.1f}%")

        # Restore original weights
        self.pipeline = MatchingPipeline(
            knowledge_base=self.knowledge_base,
            settings=self.settings
        )

        return results

    def test_strategy_combinations(
        self,
        df: pd.DataFrame,
        ground_truth: Dict[str, Tuple[str, str]],
        sheet_name: str = "Sheet1"
    ) -> Dict:
        """
        Test combinations of strategies to find optimal set.

        Args:
            df: DataFrame to analyze
            ground_truth: Expected mappings
            sheet_name: Sheet name

        Returns:
            Dict with combination results
        """
        print(f"\n{'='*80}")
        print(f"STRATEGY COMBINATION ANALYSIS")
        print(f"{'='*80}")

        # Profile columns
        profiler = ColumnProfiler()
        column_profiles = profiler.profile_dataframe(df, sheet_name=sheet_name)

        results = {}

        # Test: All strategies enabled (baseline)
        print("\nBaseline: All strategies enabled")
        for s in self.pipeline.strategies:
            s.weight = 1.0

        accuracy_all = self._evaluate_pipeline(
            column_profiles, ground_truth, sheet_name
        )
        results["all_strategies"] = accuracy_all
        print(f"  Accuracy: {accuracy_all*100:.1f}%")

        # Test: Only high-precision strategies
        print("\nHigh-Precision Only (Exact + Label + Selection)")
        for s in self.pipeline.strategies:
            if any(name in s.__class__.__name__ for name in ["ExactName", "Label", "SelectionValue"]):
                s.weight = 1.0
            else:
                s.weight = 0.0

        accuracy_high_precision = self._evaluate_pipeline(
            column_profiles, ground_truth, sheet_name
        )
        results["high_precision_only"] = accuracy_high_precision
        print(f"  Accuracy: {accuracy_high_precision*100:.1f}%")

        # Test: Without fuzzy matching
        print("\nWithout Fuzzy Matching")
        for s in self.pipeline.strategies:
            if "Fuzzy" in s.__class__.__name__:
                s.weight = 0.0
            else:
                s.weight = 1.0

        accuracy_no_fuzzy = self._evaluate_pipeline(
            column_profiles, ground_truth, sheet_name
        )
        results["no_fuzzy"] = accuracy_no_fuzzy
        print(f"  Accuracy: {accuracy_no_fuzzy*100:.1f}%")

        # Test: Without statistical similarity
        print("\nWithout Statistical Similarity")
        for s in self.pipeline.strategies:
            if "Statistical" in s.__class__.__name__:
                s.weight = 0.0
            else:
                s.weight = 1.0

        accuracy_no_stats = self._evaluate_pipeline(
            column_profiles, ground_truth, sheet_name
        )
        results["no_statistical"] = accuracy_no_stats
        print(f"  Accuracy: {accuracy_no_stats*100:.1f}%")

        # Restore original weights
        self.pipeline = MatchingPipeline(
            knowledge_base=self.knowledge_base,
            settings=self.settings
        )

        return results

    def _evaluate_pipeline(
        self,
        column_profiles: List,
        ground_truth: Dict[str, Tuple[str, str]],
        sheet_name: str
    ) -> float:
        """Evaluate current pipeline configuration."""
        mappings = self.pipeline.match_sheet(column_profiles, sheet_name=sheet_name)

        correct = 0
        for column_profile in column_profiles:
            column_name = column_profile.column_name
            field_mappings = mappings.get(column_name, [])
            expected = ground_truth.get(column_name)

            if field_mappings and expected:
                predicted = (field_mappings[0].target_model, field_mappings[0].target_field)
                if predicted == expected:
                    correct += 1

        total = len(ground_truth)
        return correct / total if total > 0 else 0.0

    def recommend_weights(
        self,
        individual_results: Dict
    ) -> Dict[str, float]:
        """
        Recommend optimal strategy weights based on performance.

        Args:
            individual_results: Results from test_individual_strategies

        Returns:
            Dict mapping strategy names to recommended weights
        """
        print(f"\n{'='*80}")
        print(f"WEIGHT RECOMMENDATIONS")
        print(f"{'='*80}")

        recommendations = {}

        for strategy_name, metrics in sorted(
            individual_results.items(),
            key=lambda x: x[1]["accuracy"],
            reverse=True
        ):
            accuracy = metrics["accuracy"]
            precision = metrics["precision"]

            # Assign weights based on performance
            if accuracy >= 0.80 and precision >= 0.90:
                weight = 1.0
                recommendation = "STRONG - Keep enabled with full weight"
            elif accuracy >= 0.60 and precision >= 0.70:
                weight = 0.7
                recommendation = "MODERATE - Reduce weight"
            elif accuracy >= 0.40:
                weight = 0.5
                recommendation = "WEAK - Consider disabling"
            else:
                weight = 0.0
                recommendation = "POOR - Disable"

            recommendations[strategy_name] = weight

            print(f"{strategy_name:30} Weight: {weight:.1f} - {recommendation}")
            print(f"  Accuracy: {accuracy*100:.1f}%, Precision: {precision*100:.1f}%")

        return recommendations


def main():
    """Main runner."""
    parser = argparse.ArgumentParser(description="Analyze matcher strategies")
    parser.add_argument(
        "--dictionary",
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / "odoo-dictionary",
        help="Path to odoo-dictionary"
    )
    args = parser.parse_args()

    analyzer = StrategyAnalyzer(dictionary_path=args.dictionary)

    if not analyzer.initialize():
        print("Failed to initialize. Exiting.")
        sys.exit(1)

    # Test with customers data
    from ground_truth import GROUND_TRUTH

    df = pd.DataFrame({
        "Customer Name": ["Acme Corp", "TechStart Inc"],
        "Contact Email": ["sales@acme.com", "hello@techstart.com"],
        "Phone": ["+1-555-0100", "+1-555-0200"],
        "Street Address": ["123 Main St", "456 Tech Blvd"],
        "City": ["New York", "San Francisco"],
        "State": ["NY", "CA"],
        "Zip Code": ["10001", "94102"],
        "Customer ID": ["CUST001", "CUST002"],
    })

    ground_truth = GROUND_TRUTH["customers"]

    # Test individual strategies
    individual_results = analyzer.test_individual_strategies(df, ground_truth, "Customers")

    # Test combinations
    combination_results = analyzer.test_strategy_combinations(df, ground_truth, "Customers")

    # Recommend weights
    recommended_weights = analyzer.recommend_weights(individual_results)

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
