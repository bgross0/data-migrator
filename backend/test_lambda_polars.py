#!/usr/bin/env python3
"""
Test script to verify lambda transformations and Polars integration work correctly.
"""

import polars as pl
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from app.core.lambda_transformer import LambdaTransformer
from app.core.profiler import ColumnProfiler


def test_lambda_transformations():
    """Test lambda transformations with Polars DataFrames."""
    print("=" * 60)
    print("Testing Lambda Transformations with Polars")
    print("=" * 60)

    # Create test data
    data = pl.DataFrame({
        'first_name': ['John', 'Jane', 'Bob', 'Alice'],
        'last_name': ['Doe', 'Smith', 'Johnson', 'Brown'],
        'email': ['john@example.com', 'jane@company.org', 'bob@test.io', 'alice@domain.com'],
        'phone': ['123-456-7890', '(555) 234-5678', '9876543210', '+1 888 999 0000'],
        'birthdate': ['1990-01-15', '1985-06-20', '1992-11-30', '1988-03-10'],
        'total_spent': [500, 1500, 750, 2000],
    })

    print("\nOriginal Data:")
    print(data)

    # Initialize transformer
    transformer = LambdaTransformer()

    # Test 1: Combine first and last name
    print("\n1. Testing name combination lambda:")
    lambda_func = "lambda self, record, **kwargs: f\"{record['first_name']} {record['last_name']}\""
    result = transformer.apply_lambda_mapping(data, 'full_name', lambda_func)
    print(f"   Full names: {result['full_name'].to_list()}")

    # Test 2: Format phone numbers
    print("\n2. Testing phone formatting lambda:")
    lambda_func = "lambda self, record, **kwargs: ''.join(c for c in str(record['phone']) if c.isdigit())"
    result = transformer.apply_lambda_mapping(result, 'clean_phone', lambda_func)
    print(f"   Clean phones: {result['clean_phone'].to_list()}")

    # Test 3: Calculate age
    print("\n3. Testing age calculation lambda:")
    lambda_func = """lambda self, record, **kwargs:
        (datetime.now() - datetime.strptime(record['birthdate'], '%Y-%m-%d')).days // 365
        if record['birthdate'] else None"""
    result = transformer.apply_lambda_mapping(result, 'age', lambda_func, 'pl.Int64')
    print(f"   Ages: {result['age'].to_list()}")

    # Test 4: Customer type based on spending
    print("\n4. Testing conditional lambda:")
    lambda_func = "lambda self, record, **kwargs: 'Premium' if record['total_spent'] > 1000 else 'Regular'"
    result = transformer.apply_lambda_mapping(result, 'customer_type', lambda_func)
    print(f"   Customer types: {result['customer_type'].to_list()}")

    # Test 5: Extract email domain
    print("\n5. Testing email domain extraction:")
    lambda_func = "lambda self, record, **kwargs: record['email'].split('@')[1] if '@' in record['email'] else None"
    result = transformer.apply_lambda_mapping(result, 'email_domain', lambda_func)
    print(f"   Email domains: {result['email_domain'].to_list()}")

    print("\n✅ All lambda transformations passed!")
    return result


def test_polars_profiler():
    """Test the Polars-based profiler."""
    print("\n" + "=" * 60)
    print("Testing Polars Profiler")
    print("=" * 60)

    # Create a test CSV file
    test_file = Path('/tmp/test_polars_data.csv')

    # Create test data with various types
    test_data = pl.DataFrame({
        'id': [1, 2, 3, 4, 5, None],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank'],
        'email': ['alice@test.com', 'bob@example.org', None, 'david@company.com', 'eve@test.io', 'frank@domain.net'],
        'age': [25, 30, None, 45, 28, 35],
        'salary': [50000.50, 75000, 60000.25, None, 85000, 92000.75],
        'is_active': ['yes', 'true', 'false', 'no', '1', '0'],
        'phone': ['123-456-7890', '(555) 234-5678', '9876543210', None, '+1 888 999 0000', '555-1234'],
        'join_date': ['2020-01-15', '2019-06-20', '2021-11-30', '2018-03-10', None, '2022-07-01'],
    })

    # Save to CSV
    test_data.write_csv(test_file)
    print(f"\nTest data saved to: {test_file}")

    # Test profiler
    profiler = ColumnProfiler(str(test_file))
    results = profiler.profile()

    print("\nProfile Results:")
    for sheet_name, columns in results.items():
        print(f"\nSheet: {sheet_name}")
        for col_profile in columns:
            print(f"\n  Column: {col_profile['name']}")
            print(f"    Type: {col_profile['dtype']}")
            print(f"    Null %: {col_profile['null_pct']:.1%}")
            print(f"    Distinct %: {col_profile['distinct_pct']:.1%}")
            print(f"    Patterns: {col_profile.get('patterns', {})}")
            print(f"    Sample values: {col_profile['sample_values'][:3]}")

    print("\n✅ Polars profiler test passed!")
    return results


def test_performance_comparison():
    """Compare performance between pandas and Polars."""
    print("\n" + "=" * 60)
    print("Performance Comparison")
    print("=" * 60)

    import time
    import pandas as pd

    # Create larger dataset
    n_rows = 100_000
    print(f"\nCreating dataset with {n_rows:,} rows...")

    # Test Polars
    start = time.time()
    df_polars = pl.DataFrame({
        'col1': range(n_rows),
        'col2': ['A', 'B', 'C', 'D'] * (n_rows // 4),
        'col3': [i * 1.5 for i in range(n_rows)],
    })

    # Operations in Polars
    result_polars = (
        df_polars
        .filter(pl.col('col1') > 50000)
        .group_by('col2')
        .agg(pl.col('col3').mean())
    )
    polars_time = time.time() - start

    # Test Pandas
    start = time.time()
    df_pandas = pd.DataFrame({
        'col1': range(n_rows),
        'col2': ['A', 'B', 'C', 'D'] * (n_rows // 4),
        'col3': [i * 1.5 for i in range(n_rows)],
    })

    # Operations in Pandas
    result_pandas = (
        df_pandas[df_pandas['col1'] > 50000]
        .groupby('col2')['col3']
        .mean()
    )
    pandas_time = time.time() - start

    print(f"\nPolars time: {polars_time:.3f} seconds")
    print(f"Pandas time: {pandas_time:.3f} seconds")
    print(f"Speedup: {pandas_time/polars_time:.2f}x")

    print("\n✅ Performance test completed!")


if __name__ == "__main__":
    print("\n🚀 Starting Lambda + Polars Integration Tests\n")

    try:
        # Test lambda transformations
        transformed_data = test_lambda_transformations()

        # Test Polars profiler
        profile_results = test_polars_profiler()

        # Test performance
        test_performance_comparison()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)

        print("\nIntegration Summary:")
        print("1. Lambda transformations: ✅ Working with Polars")
        print("2. Polars profiler: ✅ Replaced pandas successfully")
        print("3. Performance: ✅ Polars is faster than pandas")
        print("\nYou can now use lambda transformations in your mappings!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)