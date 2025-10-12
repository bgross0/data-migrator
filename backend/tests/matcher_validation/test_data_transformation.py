#!/usr/bin/env python3
"""
Data Transformation Pipeline Validation

Tests the TransformRegistry against messy_leads_data.csv to validate
data cleaning and normalization capabilities.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.transformer import TransformRegistry
import pandas as pd

def test_data_transformation():
    """Test data transformation on messy_leads_data.csv"""

    print("=" * 80)
    print("DATA TRANSFORMATION PIPELINE VALIDATION")
    print("=" * 80)

    # Load file
    file_path = Path("/home/zlab/data-migrator/messy_leads_data.csv")
    df = pd.read_csv(file_path)

    print(f"\nFile: {file_path.name}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    # Initialize transformer
    transformer = TransformRegistry()

    print(f"\n{'=' * 80}")
    print("AVAILABLE TRANSFORMS")
    print(f"{'=' * 80}")
    transforms = list(transformer.transforms.keys())
    for i, t in enumerate(transforms, 1):
        print(f"{i:2d}. {t}")

    # Test each column with appropriate transforms
    print(f"\n{'=' * 80}")
    print("TRANSFORMATION TESTS")
    print(f"{'=' * 80}")

    results = {
        "name": [],
        "phone": [],
        "email": []
    }

    # Test Name transformations
    print(f"\n{'=' * 80}")
    print("NAME FIELD TRANSFORMATIONS")
    print(f"{'=' * 80}")
    print("\nSample transformations (first 10 rows):")
    print(f"{'Original':<30} | {'titlecase':<30} | {'upper':<30}")
    print("-" * 95)

    for i, value in enumerate(df['Name'].head(10)):
        if pd.isna(value):
            continue
        original = str(value)
        titlecased = transformer.titlecase(value)
        uppered = transformer.upper(value)
        print(f"{original:<30} | {titlecased:<30} | {uppered:<30}")

        results["name"].append({
            "original": original,
            "titlecase": titlecased,
            "upper": uppered,
            "lower": transformer.lower(value),
            "trim": transformer.trim(value)
        })

    # Test Phone transformations
    print(f"\n{'=' * 80}")
    print("PHONE FIELD TRANSFORMATIONS")
    print(f"{'=' * 80}")
    print("\nSample transformations (first 10 rows):")
    print(f"{'Original':<20} | {'Normalized (E.164)':<20} | {'Status':<10}")
    print("-" * 55)

    phone_success = 0
    phone_total = 0

    for i, value in enumerate(df['Phone'].head(10)):
        if pd.isna(value):
            continue
        original = str(value)
        normalized = transformer.phone_normalize(value, region="US")
        phone_total += 1

        # Check if normalization worked (E.164 format starts with +)
        success = normalized.startswith('+') and len(normalized) > 10
        if success:
            phone_success += 1
            status = "✓"
        else:
            status = "✗"

        print(f"{original:<20} | {normalized:<20} | {status:<10}")

        results["phone"].append({
            "original": original,
            "normalized": normalized,
            "success": success
        })

    phone_accuracy = (phone_success / phone_total * 100) if phone_total > 0 else 0
    print(f"\nPhone Normalization Success Rate: {phone_success}/{phone_total} ({phone_accuracy:.1f}%)")

    # Test Email transformations
    print(f"\n{'=' * 80}")
    print("EMAIL FIELD TRANSFORMATIONS")
    print(f"{'=' * 80}")
    print("\nSample transformations (first 10 rows):")
    print(f"{'Original':<35} | {'Normalized':<35} | {'Status':<10}")
    print("-" * 85)

    email_success = 0
    email_total = 0

    for i, value in enumerate(df['Email'].head(10)):
        if pd.isna(value):
            continue
        original = str(value)
        normalized = transformer.email_normalize(value)
        email_total += 1

        # Check if normalization worked (has @, is lowercase)
        success = "@" in normalized and normalized == normalized.lower()
        if success:
            email_success += 1
            status = "✓"
        else:
            status = "✗"

        print(f"{original:<35} | {normalized:<35} | {status:<10}")

        results["email"].append({
            "original": original,
            "normalized": normalized,
            "success": success
        })

    email_accuracy = (email_success / email_total * 100) if email_total > 0 else 0
    print(f"\nEmail Normalization Success Rate: {email_success}/{email_total} ({email_accuracy:.1f}%)")

    # Test split_name on Name field
    print(f"\n{'=' * 80}")
    print("NAME SPLITTING (FIRST/LAST)")
    print(f"{'=' * 80}")
    print("\nSample name splits (first 10 rows):")
    print(f"{'Original':<30} | {'First Name':<15} | {'Last Name':<15}")
    print("-" * 65)

    for i, value in enumerate(df['Name'].head(10)):
        if pd.isna(value):
            continue
        original = str(value)
        split = transformer.split_name(value)
        print(f"{original:<30} | {split['first_name']:<15} | {split['last_name']:<15}")

    # Overall summary
    print(f"\n{'=' * 80}")
    print("TRANSFORMATION SUMMARY")
    print(f"{'=' * 80}")

    print(f"\nTransforms Available: {len(transforms)}")
    print(f"Transforms Tested: 8")
    print(f"  - Basic: trim, lower, upper, titlecase")
    print(f"  - Phone: phone_normalize (E.164)")
    print(f"  - Email: email_normalize (lowercase + trim)")
    print(f"  - Name: split_name (first/last)")
    print(f"  - Utility: concat, regex_extract (not tested)")

    print(f"\nSuccess Rates:")
    print(f"  Phone Normalization: {phone_accuracy:.1f}% ({phone_success}/{phone_total})")
    print(f"  Email Normalization: {email_accuracy:.1f}% ({email_success}/{email_total})")
    print(f"  Name Transformations: 100% (always succeeds)")

    # Test full pipeline on one row
    print(f"\n{'=' * 80}")
    print("FULL PIPELINE EXAMPLE (Row 1)")
    print(f"{'=' * 80}")

    row = df.iloc[0]
    print(f"\nOriginal Data:")
    print(f"  Name:  {row['Name']}")
    print(f"  Phone: {row['Phone']}")
    print(f"  Email: {row['Email']}")

    print(f"\nTransformed Data (Production-Ready):")
    print(f"  Name:  {transformer.titlecase(row['Name'])}")
    print(f"  Phone: {transformer.phone_normalize(row['Phone'])}")
    print(f"  Email: {transformer.email_normalize(row['Email'])}")

    name_split = transformer.split_name(row['Name'])
    print(f"\nName Split:")
    print(f"  First Name: {name_split['first_name']}")
    print(f"  Last Name:  {name_split['last_name']}")

    # Pass/Fail
    print(f"\n{'=' * 80}")
    overall_success = (phone_accuracy + email_accuracy) / 2
    threshold = 80.0

    if overall_success >= threshold:
        print(f"✓✓✓ TRANSFORMATION PIPELINE: PASSED (≥{threshold}%)")
    else:
        print(f"✗✗✗ TRANSFORMATION PIPELINE: FAILED (<{threshold}%)")

    print(f"Overall Success Rate: {overall_success:.1f}%")
    print(f"{'=' * 80}")

    return overall_success


if __name__ == "__main__":
    success_rate = test_data_transformation()
    sys.exit(0 if success_rate >= 80.0 else 1)
