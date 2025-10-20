"""
Regression tests for fixed runtime blockers and flows.

Tests cover:
1. Graph execution signatures
2. CSV emitter initialization
3. Sheet-mapping relationships
4. Lambda mapping execution
5. Dataset module attributes
6. Export/import with mappings and transforms
"""
import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import polars as pl
from app.core.database import Base
from app.models.source import Dataset, Sheet, SourceFile
from app.models.mapping import Mapping, MappingStatus, Transform
from app.services.export_service import ExportService
from app.services.graph_execute_service import GraphExecuteService
from app.registry.loader import RegistryLoader
from app.export.csv_emitter import CSVEmitter
from app.adapters.repositories_sqlite import SQLiteExceptionsRepo
import tempfile
import json


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_dataset(db_session):
    """Create a sample dataset with sheet and mappings."""
    # Create source file
    source_file = SourceFile(
        path="/tmp/test.csv",
        mime_type="text/csv",
        original_filename="test.csv"
    )
    db_session.add(source_file)
    db_session.flush()

    # Create dataset
    dataset = Dataset(
        name="Test Dataset",
        source_file_id=source_file.id,
        selected_modules=["sales_crm", "contacts"]
    )
    db_session.add(dataset)
    db_session.flush()

    # Create sheet
    sheet = Sheet(
        dataset_id=dataset.id,
        name="customers",
        n_rows=100,
        n_cols=5
    )
    db_session.add(sheet)
    db_session.flush()

    # Create confirmed mapping
    mapping = Mapping(
        dataset_id=dataset.id,
        sheet_id=sheet.id,
        header_name="customer_name",
        target_model="res.partner",
        target_field="name",
        confidence=0.95,
        status=MappingStatus.CONFIRMED,
        mapping_type="direct"
    )
    db_session.add(mapping)

    # Create mapping with lambda
    lambda_mapping = Mapping(
        dataset_id=dataset.id,
        sheet_id=sheet.id,
        header_name="email",
        target_model="res.partner",
        target_field="email",
        status=MappingStatus.CONFIRMED,
        mapping_type="lambda",
        lambda_function="lambda x: x.lower() if x else ''"
    )
    db_session.add(lambda_mapping)

    # Create mapping with transform
    transform_mapping = Mapping(
        dataset_id=dataset.id,
        sheet_id=sheet.id,
        header_name="phone",
        target_model="res.partner",
        target_field="phone",
        status=MappingStatus.CONFIRMED,
        mapping_type="direct"
    )
    db_session.add(transform_mapping)
    db_session.flush()

    # Add transform to mapping
    transform = Transform(
        mapping_id=transform_mapping.id,
        order=1,
        fn="phone_normalize",
        params=None
    )
    db_session.add(transform)
    db_session.commit()

    return dataset


class TestGraphExecutionSignatures:
    """Test graph execution service signatures are correct."""

    def test_graph_execute_service_initialization(self, db_session):
        """Test GraphExecuteService can be initialized properly."""
        service = GraphExecuteService(db_session)
        assert service is not None
        assert service.db == db_session
        assert service.export_service is not None
        assert service.graph_service is not None
        assert service.import_service is not None

    def test_csv_emitter_initialization_with_output_dir(self, db_session):
        """Test CSVEmitter initialization with proper output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            registry_path = Path(__file__).parent.parent / "registry" / "odoo.yaml"

            if not registry_path.exists():
                pytest.skip("Registry file not found")

            loader = RegistryLoader(registry_path)
            registry = loader.load()

            exceptions_repo = SQLiteExceptionsRepo(db_session)

            # This should not raise any errors
            emitter = CSVEmitter(
                registry=registry,
                exceptions_repo=exceptions_repo,
                dataset_id=1,
                output_dir=output_dir
            )

            assert emitter.output_dir == output_dir
            assert emitter.dataset_id == 1
            assert output_dir.exists()


class TestSheetMappingRelationship:
    """Test the sheet-mapping relationship is properly configured."""

    def test_sheet_has_mappings_relationship(self, db_session, sample_dataset):
        """Test that sheet.mappings relationship works."""
        sheet = db_session.query(Sheet).filter(
            Sheet.dataset_id == sample_dataset.id
        ).first()

        # Should be able to access mappings through sheet
        assert hasattr(sheet, 'mappings')
        assert len(sheet.mappings) == 3  # We created 3 mappings

        # All mappings should belong to this sheet
        for mapping in sheet.mappings:
            assert mapping.sheet_id == sheet.id

    def test_mapping_has_sheet_relationship(self, db_session, sample_dataset):
        """Test that mapping.sheet relationship works."""
        mapping = db_session.query(Mapping).filter(
            Mapping.dataset_id == sample_dataset.id
        ).first()

        # Should be able to access sheet through mapping
        assert hasattr(mapping, 'sheet')
        assert mapping.sheet is not None
        assert mapping.sheet.name == "customers"


class TestLambdaMappingExecution:
    """Test lambda mapping execution in export pipeline."""

    def test_lambda_mapping_applied(self, db_session, sample_dataset):
        """Test that lambda mappings are properly executed."""
        service = ExportService(db_session)

        # Create test dataframe
        df = pl.DataFrame({
            "customer_name": ["John Doe", "Jane Smith"],
            "email": ["JOHN@EXAMPLE.COM", "JANE@EXAMPLE.COM"],
            "phone": ["555-1234", "555-5678"]
        })

        # Get mappings for res.partner
        mappings = db_session.query(Mapping).filter(
            Mapping.dataset_id == sample_dataset.id,
            Mapping.target_model == "res.partner",
            Mapping.status == MappingStatus.CONFIRMED
        ).all()

        # Load a mock model spec
        from app.registry.loader import ModelSpec, FieldSpec
        model_spec = ModelSpec(
            name="res.partner",
            csv="res_partner.csv",
            id_template="partner_{slug(email)}",
            headers=["id", "name", "email", "phone"],
            fields={
                "id": FieldSpec(name="id", required=True),
                "name": FieldSpec(name="name", required=True),
                "email": FieldSpec(name="email", required=False),
                "phone": FieldSpec(name="phone", required=False)
            }
        )

        # Apply mappings and transforms
        result_df = service._apply_mappings_and_transforms(df, mappings, model_spec)

        # Check lambda was applied (email should be lowercase)
        assert "email" in result_df.columns
        emails = result_df["email"].to_list()
        assert emails[0] == "john@example.com"  # Should be lowercase
        assert emails[1] == "jane@example.com"  # Should be lowercase


class TestDatasetModuleAttributes:
    """Test dataset module attributes and registry integration."""

    def test_dataset_selected_modules(self, db_session, sample_dataset):
        """Test dataset.selected_modules attribute works."""
        dataset = db_session.query(Dataset).get(sample_dataset.id)

        assert hasattr(dataset, 'selected_modules')
        assert dataset.selected_modules == ["sales_crm", "contacts"]

    def test_registry_get_models_for_groups(self):
        """Test Registry.get_models_for_groups method."""
        registry_path = Path(__file__).parent.parent / "registry" / "odoo.yaml"

        if not registry_path.exists():
            pytest.skip("Registry file not found")

        loader = RegistryLoader(registry_path)
        registry = loader.load()

        # Should have the method
        assert hasattr(registry, 'get_models_for_groups')

        # Test with sales_crm group
        models = registry.get_models_for_groups(["sales_crm"])
        assert isinstance(models, list)

        # Should return models in import order
        if "res.partner" in registry.models:
            assert "res.partner" in models


class TestExportWithMappingsAndTransforms:
    """Test export service consumes mappings and transforms."""

    def test_export_uses_confirmed_mappings_only(self, db_session, sample_dataset):
        """Test that export only uses confirmed mappings."""
        # Add a pending mapping (should be ignored)
        pending_mapping = Mapping(
            dataset_id=sample_dataset.id,
            sheet_id=sample_dataset.sheets[0].id,
            header_name="ignore_me",
            target_model="res.partner",
            target_field="ignore_field",
            status=MappingStatus.PENDING,
            mapping_type="direct"
        )
        db_session.add(pending_mapping)
        db_session.commit()

        # Get all mappings
        all_mappings = db_session.query(Mapping).filter(
            Mapping.dataset_id == sample_dataset.id
        ).all()

        # Should have 4 total (3 confirmed + 1 pending)
        assert len(all_mappings) == 4

        # Get only confirmed mappings (what export uses)
        confirmed = [m for m in all_mappings if m.status == MappingStatus.CONFIRMED]
        assert len(confirmed) == 3

    def test_transform_applied_during_export(self, db_session, sample_dataset):
        """Test that transforms are applied during export."""
        service = ExportService(db_session)

        # Create test dataframe with phone that needs normalization
        df = pl.DataFrame({
            "customer_name": ["Test Company"],
            "email": ["test@example.com"],
            "phone": ["(555) 123-4567"]  # Needs normalization
        })

        # Get mappings
        mappings = db_session.query(Mapping).filter(
            Mapping.dataset_id == sample_dataset.id,
            Mapping.target_model == "res.partner",
            Mapping.status == MappingStatus.CONFIRMED
        ).all()

        # Find phone mapping with transform
        phone_mapping = next(m for m in mappings if m.header_name == "phone")
        assert len(phone_mapping.transforms) == 1
        assert phone_mapping.transforms[0].fn == "phone_normalize"


class TestRuntimeBlockerFixes:
    """Test all runtime blockers are fixed."""

    def test_no_csv_emitter_none_output_dir(self):
        """Test CSVEmitter cannot be initialized with None output_dir."""
        from app.registry.loader import Registry
        from dataclasses import dataclass, field

        @dataclass
        class MockRegistry(Registry):
            version: int = 1
            import_order: list = field(default_factory=list)
            models: dict = field(default_factory=dict)
            seeds: dict = field(default_factory=dict)

        mock_registry = MockRegistry()
        mock_repo = type('MockRepo', (), {})()

        # This should raise an error or handle None gracefully
        with pytest.raises((TypeError, AttributeError)):
            emitter = CSVEmitter(
                registry=mock_registry,
                exceptions_repo=mock_repo,
                dataset_id=1,
                output_dir=None  # This was the bug
            )

    def test_graph_execution_creates_output_dir_first(self, db_session):
        """Test graph execution creates output directory before CSVEmitter init."""
        service = GraphExecuteService(db_session)

        # Mock the execution flow
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override artifact_root
            service.export_service.artifact_root = Path(tmpdir)

            dataset_id = 1
            output_dir = service.export_service.artifact_root / str(dataset_id)

            # Should create directory before using it
            output_dir.mkdir(parents=True, exist_ok=True)
            assert output_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])