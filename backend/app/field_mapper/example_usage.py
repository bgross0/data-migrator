"""
Example usage of the Deterministic Field Mapper.

This script demonstrates how to use the field mapper to map spreadsheet columns
to Odoo fields.
"""
from pathlib import Path
from app.field_mapper.main import DeterministicFieldMapper
from app.field_mapper.validation import ConstraintValidator
from app.field_mapper.executor import MappingExecutor


def example_basic_mapping():
    """Example 1: Basic file mapping."""
    print("=" * 80)
    print("Example 1: Basic File Mapping")
    print("=" * 80)

    # Initialize mapper
    mapper = DeterministicFieldMapper(
        dictionary_path="/home/ben/Documents/GitHub/data-migrator/odoo-dictionary"
    )

    # Map a file (replace with your file path)
    # result = mapper.map_file("path/to/your/spreadsheet.xlsx")

    # For demonstration, let's map a DataFrame
    import pandas as pd

    # Sample customer data
    df = pd.DataFrame({
        "customer_name": ["John Doe", "Jane Smith", "Bob Johnson"],
        "email": ["john@example.com", "jane@example.com", "bob@example.com"],
        "phone": ["+1234567890", "+0987654321", "+1122334455"],
        "company": ["Acme Corp", "Tech Inc", "Global Ltd"],
        "is_company": [False, False, True],
    })

    # Map the DataFrame
    mappings = mapper.map_dataframe(df, sheet_name="Customers")

    # Print results
    print("\nMapping Results:")
    print("-" * 80)
    for column_name, field_mappings in mappings.items():
        if not field_mappings:
            print(f"\n❌ {column_name}: No mapping found")
            continue

        best_mapping = field_mappings[0]
        print(f"\n✓ {column_name}:")
        print(f"  → {best_mapping.target_model}.{best_mapping.target_field}")
        print(f"  Confidence: {best_mapping.confidence:.2f}")
        print(f"  Strategy: {best_mapping.matching_strategy}")
        print(f"  Rationale: {best_mapping.rationale[:100]}...")

        # Show alternatives if available
        if best_mapping.alternatives:
            print(f"  Alternatives:")
            for alt in best_mapping.alternatives[:2]:
                print(f"    - {alt.target_model}.{alt.target_field} (confidence: {alt.confidence:.2f})")

    return mapper, df, mappings


def example_validation(mapper, df, mappings):
    """Example 2: Validate mappings."""
    print("\n" + "=" * 80)
    print("Example 2: Validation")
    print("=" * 80)

    # Create validator
    validator = ConstraintValidator(mapper.knowledge_base)

    # Validate mappings for res.partner model
    result = validator.validate_mappings(
        mappings,
        target_model="res.partner",
        df=df
    )

    print(f"\nValidation Result: {'✓ VALID' if result.is_valid else '❌ INVALID'}")

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  ❌ {error}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  ⚠ {warning}")

    if result.missing_required_fields:
        print("\nMissing Required Fields:")
        for field in result.missing_required_fields:
            print(f"  - {field}")

    if result.suggestions:
        print("\nSuggestions:")
        for suggestion in result.suggestions:
            print(f"  💡 {suggestion.description}")

    return result


def example_data_transformation(mapper, df, mappings):
    """Example 3: Transform data using mappings."""
    print("\n" + "=" * 80)
    print("Example 3: Data Transformation")
    print("=" * 80)

    # Create executor
    executor = MappingExecutor(mapper.knowledge_base)

    # Execute mappings (transform data)
    try:
        # Group by model
        by_model = executor.execute_by_model(df, mappings)

        print("\nTransformed Data by Model:")
        print("-" * 80)
        for model_name, model_df in by_model.items():
            print(f"\nModel: {model_name}")
            print(f"Columns: {list(model_df.columns)}")
            print(f"Rows: {len(model_df)}")
            print("\nSample data:")
            print(model_df.head())

        # Generate Odoo import file
        if "res.partner" in by_model:
            output_file = "/tmp/partner_import.csv"
            executor.generate_odoo_import_csv(
                by_model["res.partner"],
                "res.partner",
                output_file
            )
            print(f"\n✓ Generated Odoo import file: {output_file}")

    except Exception as e:
        print(f"\n❌ Error during transformation: {e}")


def example_get_field_suggestions(mapper):
    """Example 4: Get field suggestions for a single column."""
    print("\n" + "=" * 80)
    print("Example 4: Field Suggestions")
    print("=" * 80)

    # Get suggestions for a column
    suggestions = mapper.get_field_suggestions(
        column_name="customer_email",
        sample_values=["john@example.com", "jane@example.com", "bob@example.com"],
        data_type="string",
        max_suggestions=5
    )

    print("\nField Suggestions for 'customer_email':")
    print("-" * 80)
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. {suggestion.target_model}.{suggestion.target_field}")
        print(f"   Confidence: {suggestion.confidence:.2f}")
        print(f"   Strategy: {suggestion.matching_strategy}")
        print(f"   Rationale: {suggestion.rationale[:100]}...")


def example_statistics(mapper):
    """Example 5: Get system statistics."""
    print("\n" + "=" * 80)
    print("Example 5: System Statistics")
    print("=" * 80)

    stats = mapper.get_statistics()

    print("\nKnowledge Base:")
    print(f"  Models: {stats['knowledge_base']['total_models']}")
    print(f"  Fields: {stats['knowledge_base']['total_fields']}")
    print(f"  Selections: {stats['knowledge_base']['total_selections']}")

    print("\nPipeline:")
    print(f"  Total Strategies: {stats['pipeline']['total_strategies']}")
    print(f"  Enabled Strategies: {stats['pipeline']['enabled_strategies']}")

    print("\nSettings:")
    print(f"  Confidence Threshold: {stats['settings']['confidence_threshold']}")
    print(f"  Sample Size: {stats['settings']['sample_size']}")


def example_performance_monitoring():
    """Example 6: Performance monitoring."""
    print("\n" + "=" * 80)
    print("Example 6: Performance Monitoring")
    print("=" * 80)

    from app.field_mapper.performance import get_monitor

    monitor = get_monitor()

    # Measure an operation
    with monitor.measure("example_operation"):
        import time
        time.sleep(0.1)  # Simulate work

    # Get summary
    summary = monitor.get_summary()

    print("\nPerformance Summary:")
    print(f"  Total Operations: {summary['total_operations']}")
    print(f"  Total Duration: {summary['total_duration_ms']:.2f}ms")
    print(f"  Current Memory: {summary['current_memory_mb']:.2f}MB")

    if summary.get("by_operation"):
        print("\nBy Operation:")
        for op_name, op_stats in summary["by_operation"].items():
            print(f"  {op_name}:")
            print(f"    Count: {op_stats['count']}")
            print(f"    Avg Duration: {op_stats['avg_duration_ms']:.2f}ms")


def example_caching():
    """Example 7: Caching demonstration."""
    print("\n" + "=" * 80)
    print("Example 7: Caching")
    print("=" * 80)

    from app.field_mapper.cache import get_cache

    cache = get_cache()

    # Set a value
    cache.set("test_key", {"data": "test_value"})

    # Get the value
    value = cache.get("test_key")
    print(f"\nCached value: {value}")

    # Get statistics
    stats = cache.get_stats()
    print(f"\nCache Statistics:")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit Rate: {stats['hit_rate']}")
    print(f"  LRU Size: {stats['lru_size']}")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "DETERMINISTIC FIELD MAPPER" + " " * 32 + "║")
    print("║" + " " * 26 + "USAGE EXAMPLES" + " " * 38 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        # Run examples
        mapper, df, mappings = example_basic_mapping()
        example_validation(mapper, df, mappings)
        example_data_transformation(mapper, df, mappings)
        example_get_field_suggestions(mapper)
        example_statistics(mapper)
        example_performance_monitoring()
        example_caching()

        print("\n" + "=" * 80)
        print("✓ All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
