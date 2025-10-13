"""
REAL end-to-end test of sheet splitting with actual multi-model data.

This test:
1. Uploads test CSV with mixed data
2. Creates REAL mappings for 3 different models
3. Executes split
4. Verifies new sheets exist
5. Verifies data files were created
6. Checks data integrity
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models import Dataset, Sheet, Mapping, ColumnProfile, SourceFile
from app.services.sheet_splitter import SheetSplitterService
from app.models.mapping import MappingStatus
from datetime import datetime


def create_test_data():
    """Create test CSV with multi-model data."""
    data = {
        # res.partner fields
        "Customer Name": ["Acme Corp", "TechStart Inc", "Global Services"],
        "Customer Email": ["contact@acme.com", "info@techstart.io", "hello@global.com"],
        "Customer Phone": ["555-1234", "555-5678", "555-9012"],

        # fleet.vehicle fields
        "Vehicle VIN": ["1HGCM82633A123456", "2T1BU4EE8DC123789", "5FNRL6H79KB123456"],
        "Vehicle License": ["ABC-123", "XYZ-789", "DEF-456"],
        "Vehicle Model": ["Honda Accord", "Toyota Camry", "Honda CR-V"],

        # sale.order fields
        "Order Number": ["SO-001", "SO-002", "SO-003"],
        "Order Date": ["2024-01-15", "2024-01-16", "2024-01-17"],
        "Order Total": [1500.00, 2300.00, 1800.00],
    }

    df = pd.DataFrame(data)
    test_file = Path("/tmp/test_multi_model.csv")
    df.to_csv(test_file, index=False)
    return test_file


def test_real_split():
    """Test actual split with real multi-model mappings."""
    print("=" * 80)
    print("REAL MULTI-MODEL SPLIT TEST")
    print("=" * 80)

    db = SessionLocal()

    try:
        # Step 1: Create test data
        print("\n[1] Creating test data with 3 models...")
        test_file = create_test_data()
        print(f"✓ Created: {test_file}")

        # Step 2: Create SourceFile and Dataset
        print("\n[2] Creating dataset...")
        source_file = SourceFile(
            path=str(test_file),
            mime_type="text/csv",
            original_filename="test_multi_model.csv",
            uploaded_at=datetime.utcnow()
        )
        db.add(source_file)
        db.flush()

        dataset = Dataset(
            name="Multi-Model Test Dataset",
            source_file_id=source_file.id,
            created_at=datetime.utcnow(),
            selected_modules=["contacts_partners", "fleet", "sales_crm"]
        )
        db.add(dataset)
        db.flush()
        print(f"✓ Dataset created: ID={dataset.id}")

        # Step 3: Create Sheet
        print("\n[3] Creating sheet...")
        df = pd.read_csv(test_file)
        sheet = Sheet(
            dataset_id=dataset.id,
            name="Sheet1",
            n_rows=len(df),
            n_cols=len(df.columns)
        )
        db.add(sheet)
        db.flush()
        print(f"✓ Sheet created: ID={sheet.id}, Rows={sheet.n_rows}, Cols={sheet.n_cols}")

        # Step 4: Create ColumnProfiles
        print("\n[4] Creating column profiles...")
        for col in df.columns:
            profile = ColumnProfile(
                sheet_id=sheet.id,
                name=col,
                dtype_guess="string",
                sample_values=df[col].head(3).tolist(),
                null_pct=0.0,
                distinct_pct=100.0,
                patterns={}
            )
            db.add(profile)
        db.commit()
        print(f"✓ Created {len(df.columns)} column profiles")

        # Step 5: Create REAL mappings for 3 models
        print("\n[5] Creating multi-model mappings...")

        # res.partner mappings
        partner_mappings = [
            ("Customer Name", "name"),
            ("Customer Email", "email"),
            ("Customer Phone", "phone"),
        ]

        for header, field in partner_mappings:
            mapping = Mapping(
                dataset_id=dataset.id,
                sheet_id=sheet.id,
                header_name=header,
                target_model="res.partner",
                target_field=field,
                confidence=0.95,
                status=MappingStatus.CONFIRMED,
                chosen=True
            )
            db.add(mapping)

        # fleet.vehicle mappings
        fleet_mappings = [
            ("Vehicle VIN", "vin"),
            ("Vehicle License", "license_plate"),
            ("Vehicle Model", "model_id"),
        ]

        for header, field in fleet_mappings:
            mapping = Mapping(
                dataset_id=dataset.id,
                sheet_id=sheet.id,
                header_name=header,
                target_model="fleet.vehicle",
                target_field=field,
                confidence=0.92,
                status=MappingStatus.CONFIRMED,
                chosen=True
            )
            db.add(mapping)

        # sale.order mappings
        order_mappings = [
            ("Order Number", "name"),
            ("Order Date", "date_order"),
            ("Order Total", "amount_total"),
        ]

        for header, field in order_mappings:
            mapping = Mapping(
                dataset_id=dataset.id,
                sheet_id=sheet.id,
                header_name=header,
                target_model="sale.order",
                target_field=field,
                confidence=0.93,
                status=MappingStatus.CONFIRMED,
                chosen=True
            )
            db.add(mapping)

        db.commit()

        # Verify mappings
        all_mappings = db.query(Mapping).filter(Mapping.sheet_id == sheet.id).all()
        models_detected = {}
        for m in all_mappings:
            if m.target_model not in models_detected:
                models_detected[m.target_model] = []
            models_detected[m.target_model].append(m.header_name)

        print(f"✓ Created {len(all_mappings)} mappings for {len(models_detected)} models:")
        for model, columns in models_detected.items():
            print(f"  - {model}: {columns}")

        # Step 6: Preview split
        print("\n[6] Testing split preview...")
        splitter = SheetSplitterService(db)
        preview = splitter.preview_split(sheet.id)

        if not preview.get("can_split"):
            print(f"✗ FAIL: Cannot split - {preview.get('error')}")
            return False

        print(f"✓ Can split into {len(preview['models'])} sheets:")
        for model_info in preview['models']:
            print(f"  - {model_info['display_name']} ({model_info['model']}): {model_info['column_count']} cols")

        # Step 7: Execute split
        print("\n[7] Executing split...")
        result = splitter.split_sheet(sheet.id, delete_original=False)

        if not result.get("success"):
            print(f"✗ FAIL: Split failed - {result.get('error')}")
            if result.get('errors'):
                for error in result['errors']:
                    print(f"  - {error}")
            return False

        print(f"✓ Split successful! Created {len(result['created_sheets'])} sheets:")
        for new_sheet in result['created_sheets']:
            print(f"  - {new_sheet['name']} (ID: {new_sheet['id']})")
            print(f"    Model: {new_sheet['model']}")
            print(f"    Rows: {new_sheet['rows']}, Columns: {new_sheet['columns']}")
            print(f"    File: {new_sheet['file_path']}")

        # Step 8: Verify new sheets in database
        print("\n[8] Verifying database state...")
        all_sheets = db.query(Sheet).filter(Sheet.dataset_id == dataset.id).all()
        print(f"✓ Total sheets in database: {len(all_sheets)}")

        split_sheets = [s for s in all_sheets if s.target_model]
        print(f"✓ Split sheets with target_model: {len(split_sheets)}")

        for s in split_sheets:
            print(f"  - {s.name} (ID: {s.id})")
            print(f"    target_model: {s.target_model}")
            print(f"    Rows: {s.n_rows}, Cols: {s.n_cols}")

            # Check ColumnProfiles
            profiles = db.query(ColumnProfile).filter(ColumnProfile.sheet_id == s.id).all()
            print(f"    ColumnProfiles: {len(profiles)}")

            # Check Mappings
            mappings = db.query(Mapping).filter(Mapping.sheet_id == s.id).all()
            print(f"    Mappings: {len(mappings)}")

        # Step 9: Verify data files
        print("\n[9] Verifying split data files...")
        for created_sheet in result['created_sheets']:
            file_path = Path(created_sheet['file_path'])
            if not file_path.exists():
                print(f"✗ FAIL: File not found: {file_path}")
                return False

            # Read and verify data
            split_df = pd.read_csv(file_path)
            print(f"\n  ✓ {file_path.name}")
            print(f"    Rows: {len(split_df)}, Cols: {len(split_df.columns)}")
            print(f"    Columns: {list(split_df.columns)}")
            print(f"    Sample data:")
            print(split_df.head(2).to_string(index=False))

        # Step 10: Verify data integrity
        print("\n[10] Verifying data integrity...")

        # Check res.partner sheet
        partner_file = [f for f in result['created_sheets'] if f['model'] == 'res.partner'][0]['file_path']
        partner_df = pd.read_csv(partner_file)
        assert len(partner_df) == 3, f"Expected 3 rows, got {len(partner_df)}"
        assert len(partner_df.columns) == 3, f"Expected 3 columns, got {len(partner_df.columns)}"
        # MappingExecutor renamed to Odoo field names!
        assert "name" in partner_df.columns
        assert "email" in partner_df.columns
        assert "phone" in partner_df.columns
        print("✓ res.partner data integrity verified (columns mapped to Odoo field names)")

        # Check fleet.vehicle sheet
        fleet_file = [f for f in result['created_sheets'] if f['model'] == 'fleet.vehicle'][0]['file_path']
        fleet_df = pd.read_csv(fleet_file)
        assert len(fleet_df) == 3, f"Expected 3 rows, got {len(fleet_df)}"
        assert len(fleet_df.columns) == 3, f"Expected 3 columns, got {len(fleet_df.columns)}"
        assert "vin" in fleet_df.columns
        assert "license_plate" in fleet_df.columns
        assert "model_id" in fleet_df.columns
        print("✓ fleet.vehicle data integrity verified (columns mapped to Odoo field names)")

        # Check sale.order sheet
        order_file = [f for f in result['created_sheets'] if f['model'] == 'sale.order'][0]['file_path']
        order_df = pd.read_csv(order_file)
        assert len(order_df) == 3, f"Expected 3 rows, got {len(order_df)}"
        assert len(order_df.columns) == 3, f"Expected 3 columns, got {len(order_df.columns)}"
        assert "name" in order_df.columns  # order_number → name
        assert "date_order" in order_df.columns
        assert "amount_total" in order_df.columns
        print("✓ sale.order data integrity verified (columns mapped to Odoo field names)")

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - SHEET SPLITTING WORKS END-TO-END!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_real_split()
    sys.exit(0 if success else 1)
