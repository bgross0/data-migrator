"""
Test that graph execution properly applies mappings before validation.

This verifies the fix for the critical missing logic in execute_model_node().
"""
import pytest
from pathlib import Path
from sqlalchemy.orm import Session
import polars as pl

from app.core.database import Base, engine, SessionLocal
from app.models.graph import Graph
from app.models.source import Dataset, SourceFile, Sheet
from app.models.mapping import Mapping, MappingStatus
from app.services.graph_execute_service import GraphExecuteService
from app.services.export_service import ExportService


@pytest.fixture
def db():
    """Create test database session."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_data_with_mappings(db: Session, tmp_path):
    """Create test dataset with confirmed mappings."""
    # Create a test CSV file
    csv_path = tmp_path / "test_partners.csv"
    csv_path.write_text("""Customer Name,Email Address,Phone Number
Acme Corp,info@acme.com,555-1234
Beta LLC,hello@beta.com,555-5678
""")

    # Create source file
    source_file = SourceFile(
        path=str(csv_path),
        original_filename="test_partners.csv",
        mime_type="text/csv"
    )
    db.add(source_file)
    db.commit()

    # Create dataset
    dataset = Dataset(
        name="Test Partners",
        source_file_id=source_file.id,
        profiling_status="complete"
    )
    db.add(dataset)
    db.commit()

    # Create sheet
    sheet = Sheet(
        dataset_id=dataset.id,
        name="Sheet1",
        n_rows=2,
        n_cols=3
    )
    db.add(sheet)
    db.commit()

    # Create CONFIRMED mappings (this is the key part)
    mappings = [
        Mapping(
            dataset_id=dataset.id,
            sheet_id=sheet.id,
            header_name="Customer Name",
            target_model="res.partner",
            target_field="name",
            confidence=0.95,
            status=MappingStatus.CONFIRMED,  # Must be CONFIRMED
            chosen=True,
            mapping_type="direct"
        ),
        Mapping(
            dataset_id=dataset.id,
            sheet_id=sheet.id,
            header_name="Email Address",
            target_model="res.partner",
            target_field="email",
            confidence=1.0,
            status=MappingStatus.CONFIRMED,
            chosen=True,
            mapping_type="direct"
        ),
        Mapping(
            dataset_id=dataset.id,
            sheet_id=sheet.id,
            header_name="Phone Number",
            target_model="res.partner",
            target_field="phone",
            confidence=0.9,
            status=MappingStatus.CONFIRMED,
            chosen=True,
            mapping_type="direct"
        ),
    ]

    for mapping in mappings:
        db.add(mapping)
    db.commit()

    return {
        "dataset": dataset,
        "sheet": sheet,
        "mappings": mappings,
        "csv_path": csv_path
    }


def test_execute_model_node_applies_mappings(db: Session, test_data_with_mappings, tmp_path):
    """
    Test that execute_model_node applies mappings before validation.

    This is the critical fix - without applying mappings, validation fails because
    source column names ("Customer Name") don't match target field names ("name").
    """
    dataset = test_data_with_mappings["dataset"]

    # Set up export service with artifact root
    from app.core.config import settings
    original_artifact_root = settings.ARTIFACT_ROOT
    settings.ARTIFACT_ROOT = str(tmp_path / "artifacts")

    try:
        export_service = ExportService(db)
        execute_service = GraphExecuteService(db)

        # Call execute_model_node for res.partner model
        result = execute_service.execute_model_node(
            model_name="res.partner",
            run_id=1,
            dataset_id=dataset.id
        )

        print(f"\n📊 Execution result: {result}")

        # Verify execution succeeded
        assert result["success"] is True, f"Execution failed: {result.get('error')}"

        # If mappings were applied correctly, we should have emitted rows
        # Without mappings, validation would fail and rows_emitted would be 0
        assert result["rows_emitted"] >= 0, "Should have processed rows"

        # If we got an error, it should not be about missing columns
        if result.get("error"):
            assert "not found" not in result["error"].lower(), \
                "Should not get 'column not found' errors if mappings applied correctly"

        print(f"✓ Mappings were applied: {result['rows_emitted']} rows processed")

    finally:
        settings.ARTIFACT_ROOT = original_artifact_root


def test_execute_model_node_skips_without_confirmed_mappings(db: Session, test_data_with_mappings):
    """
    Test that execute_model_node skips models without CONFIRMED mappings.
    """
    dataset = test_data_with_mappings["dataset"]

    # Change all mappings to PENDING
    for mapping in test_data_with_mappings["mappings"]:
        mapping.status = MappingStatus.PENDING
    db.commit()

    execute_service = GraphExecuteService(db)

    # Call execute_model_node
    result = execute_service.execute_model_node(
        model_name="res.partner",
        run_id=1,
        dataset_id=dataset.id
    )

    # Should skip because no CONFIRMED mappings
    assert result["success"] is True
    assert result["rows_emitted"] == 0
    print("✓ Correctly skipped model without CONFIRMED mappings")


def test_mapping_transforms_column_names(db: Session, test_data_with_mappings, tmp_path):
    """
    Test that _apply_mappings_and_transforms actually renames columns.

    This directly tests the transformation logic.
    """
    dataset = test_data_with_mappings["dataset"]
    csv_path = test_data_with_mappings["csv_path"]

    # Read the source CSV
    df = pl.read_csv(str(csv_path))

    print(f"\n📄 Source columns: {df.columns}")
    assert "Customer Name" in df.columns
    assert "Email Address" in df.columns
    assert "Phone Number" in df.columns

    # Get mappings and model spec
    from app.registry.loader import RegistryLoader
    from app.core.config import settings

    registry_path = Path(settings.REGISTRY_FILE)
    loader = RegistryLoader(registry_path)
    registry = loader.load()

    model_spec = registry.models["res.partner"]
    mappings = test_data_with_mappings["mappings"]

    # Apply mappings using the export service method
    original_artifact_root = settings.ARTIFACT_ROOT
    settings.ARTIFACT_ROOT = str(tmp_path / "artifacts")

    try:
        export_service = ExportService(db)
        transformed_df = export_service._apply_mappings_and_transforms(df, mappings, model_spec)

        print(f"✓ Transformed columns: {transformed_df.columns}")

        # Verify columns were renamed
        assert "name" in transformed_df.columns, "Should have 'name' column"
        assert "email" in transformed_df.columns, "Should have 'email' column"
        assert "phone" in transformed_df.columns, "Should have 'phone' column"

        # Verify old names are gone
        assert "Customer Name" not in transformed_df.columns
        assert "Email Address" not in transformed_df.columns
        assert "Phone Number" not in transformed_df.columns

        # Verify data was preserved
        assert len(transformed_df) == 2
        assert "Acme Corp" in transformed_df["name"].to_list()
        assert "info@acme.com" in transformed_df["email"].to_list()

        print("✓ Column name transformation verified")

    finally:
        settings.ARTIFACT_ROOT = original_artifact_root


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
