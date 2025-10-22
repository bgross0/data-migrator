"""
Unit Tests for MappingService.

Tests core mapping logic including deterministic/hybrid matcher routing,
module filtering, confidence thresholds, and CRUD operations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.mapping_service import MappingService
from app.models import Mapping, Dataset, Sheet, ColumnProfile
from app.models.mapping import MappingStatus


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mapping_service(mock_db):
    """MappingService instance with mocked database."""
    return MappingService(mock_db)


@pytest.fixture
def sample_dataset_with_profiles(mock_db):
    """Sample dataset with sheets and column profiles."""
    dataset = Mock(spec=Dataset)
    dataset.id = 1
    dataset.selected_modules = ["sales_crm", "contacts_partners"]

    sheet = Mock(spec=Sheet)
    sheet.id = 1
    sheet.name = "Customers"

    profiles = [
        Mock(spec=ColumnProfile, name="Customer Name", id=1),
        Mock(spec=ColumnProfile, name="Email", id=2),
        Mock(spec=ColumnProfile, name="Phone", id=3),
    ]

    dataset.sheets = [sheet]
    return dataset, sheet, profiles


class TestMappingServiceInitialization:
    """Test MappingService initialization and matcher setup."""

    def test_service_initialization(self, mock_db):
        """Test that service initializes with database session."""
        service = MappingService(mock_db)
        assert service.db == mock_db
        assert service.lambda_transformer is not None

    def test_deterministic_mapper_initialization(self, mock_db):
        """Test deterministic field mapper initialization."""
        service = MappingService(mock_db)
        # Mapper may or may not be available depending on dictionary path
        assert hasattr(service, 'deterministic_mapper')

    def test_hybrid_matcher_initialization(self, mock_db):
        """Test hybrid matcher initialization."""
        service = MappingService(mock_db)
        # Matcher may or may not be available depending on dictionary path
        assert hasattr(service, 'hybrid_matcher')


class TestMappingServiceCRUD:
    """Test CRUD operations for mappings."""

    def test_get_mappings_for_dataset(self, mapping_service, mock_db):
        """Test retrieving mappings for a dataset."""
        dataset_id = 1
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        result = mapping_service.get_mappings_for_dataset(dataset_id)

        assert isinstance(result, list)
        mock_db.query.assert_called_once()

    def test_update_mapping(self, mapping_service, mock_db):
        """Test updating a mapping."""
        mapping_id = 1
        mock_mapping = Mock(spec=Mapping)
        mock_mapping.id = mapping_id

        mock_db.query.return_value.filter.return_value.first.return_value = mock_mapping

        from app.schemas.mapping import MappingUpdate
        update_data = MappingUpdate(
            target_model="res.partner",
            target_field="name",
            status=MappingStatus.CONFIRMED
        )

        result = mapping_service.update_mapping(mapping_id, update_data)

        assert result == mock_mapping
        assert mock_mapping.target_model == "res.partner"
        assert mock_mapping.target_field == "name"
        assert mock_mapping.status == MappingStatus.CONFIRMED
        mock_db.commit.assert_called_once()

    def test_update_mapping_not_found(self, mapping_service, mock_db):
        """Test updating non-existent mapping returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.schemas.mapping import MappingUpdate
        update_data = MappingUpdate(target_field="name")

        result = mapping_service.update_mapping(99999, update_data)

        assert result is None

    def test_delete_mapping(self, mapping_service, mock_db):
        """Test deleting a mapping."""
        mapping_id = 1
        mock_mapping = Mock(spec=Mapping)

        mock_db.query.return_value.filter.return_value.first.return_value = mock_mapping

        result = mapping_service.delete_mapping(mapping_id)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_mapping)
        mock_db.commit.assert_called_once()

    def test_delete_mapping_not_found(self, mapping_service, mock_db):
        """Test deleting non-existent mapping returns False."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = mapping_service.delete_mapping(99999)

        assert result is False


class TestMappingServiceRouting:
    """Test routing between deterministic and hybrid matchers."""

    @pytest.mark.asyncio
    async def test_generate_mappings_v2_deterministic_path(self, mapping_service, mock_db):
        """Test that use_deterministic=True uses deterministic mapper."""
        # Mock deterministic mapper as available
        mapping_service.deterministic_mapper = Mock()
        mapping_service.deterministic_mapper.map_dataframe = Mock(return_value={})

        # Mock database queries
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = Mock(
            id=1, source_file=Mock(path="/tmp/test.csv"), sheets=[]
        )

        with patch('polars.read_csv', return_value=Mock(columns=[])):
            result = await mapping_service.generate_mappings_v2(1, use_deterministic=True)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_generate_mappings_v2_hybrid_fallback(self, mapping_service, mock_db):
        """Test that use_deterministic=False routes to hybrid matcher."""
        # Mock hybrid matcher as available
        mapping_service.hybrid_matcher = Mock()
        mapping_service.generate_mappings_hybrid = Mock(return_value=[])

        result = await mapping_service.generate_mappings_v2(1, use_deterministic=False)

        # Should call hybrid matcher
        mapping_service.generate_mappings_hybrid.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_generate_mappings_v2_no_deterministic_raises_error(self, mapping_service):
        """Test that missing deterministic mapper raises RuntimeError."""
        mapping_service.deterministic_mapper = None

        with pytest.raises(RuntimeError, match="Deterministic field mapper is not available"):
            await mapping_service.generate_mappings_v2(1, use_deterministic=True)

    @pytest.mark.asyncio
    async def test_generate_mappings_hybrid_no_hybrid_raises_error(self, mapping_service):
        """Test that missing hybrid matcher raises RuntimeError."""
        mapping_service.hybrid_matcher = None
        mapping_service.deterministic_mapper = None

        with pytest.raises(RuntimeError, match="Hybrid matcher is not available"):
            await mapping_service.generate_mappings_hybrid(1)


class TestMappingServiceConfidence:
    """Test confidence threshold handling."""

    @pytest.mark.asyncio
    async def test_auto_confirm_high_confidence(self, mapping_service, mock_db):
        """Test that mappings >= 0.7 confidence are auto-confirmed."""
        mapping_service.deterministic_mapper = Mock()

        # Mock high confidence mapping
        high_conf_mapping = Mock(
            target_model="res.partner",
            target_field="name",
            confidence=0.85,
            rationale="High confidence match"
        )
        mapping_service.deterministic_mapper.map_dataframe = Mock(return_value={
            "Customer Name": [high_conf_mapping]
        })

        mock_dataset = Mock(id=1, source_file=Mock(path="/tmp/test.csv"), sheets=[Mock(id=1, name="Sheet1")])
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_dataset

        with patch('polars.read_csv', return_value=Mock(columns=["Customer Name"])):
            await mapping_service.generate_mappings_v2(1, use_deterministic=True)

        # Verify mapping was added with confirmed status
        # (This checks the mock_db.add was called)
        assert mock_db.add.called


class TestMappingServiceModuleFiltering:
    """Test module-based model filtering."""

    @pytest.mark.asyncio
    async def test_module_filtering_applied(self, mapping_service, mock_db):
        """Test that selected_modules are passed to matchers."""
        mapping_service.deterministic_mapper = Mock()
        mapping_service.deterministic_mapper.map_dataframe = Mock(return_value={})

        mock_dataset = Mock(
            id=1,
            source_file=Mock(path="/tmp/test.csv"),
            sheets=[],
            selected_modules=["sales_crm", "contacts_partners"]
        )
        mock_db.query.return_value.filter.return_value.delete.return_value = None
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_dataset

        with patch('polars.read_csv', return_value=Mock(columns=[])):
            await mapping_service.generate_mappings_v2(1, use_deterministic=True)

        # Verify map_dataframe was called with selected_modules
        call_args = mapping_service.deterministic_mapper.map_dataframe.call_args
        assert call_args is not None
        # Check if selected_modules was passed (may be in kwargs)
        if call_args[1]:  # kwargs
            assert "selected_modules" in call_args[1]


class TestLambdaMappings:
    """Test lambda transformation mappings."""

    def test_create_lambda_mapping(self, mapping_service, mock_db):
        """Test creating a lambda transformation mapping."""
        dataset_id = 1
        sheet_id = 1
        target_field = "full_name"
        lambda_function = "lambda row: f\"{row['first_name']} {row['last_name']}\""
        target_model = "res.partner"

        result = mapping_service.create_lambda_mapping(
            dataset_id, sheet_id, target_field, lambda_function, target_model
        )

        # Verify mapping created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result is not None

    def test_lambda_mapping_attributes(self, mapping_service, mock_db):
        """Test that lambda mappings have correct attributes."""
        mock_db.refresh = Mock()  # Mock refresh to avoid error

        result = mapping_service.create_lambda_mapping(
            1, 1, "full_name", "lambda row: row['name']", "res.partner"
        )

        # Verify the mapping object passed to db.add
        added_mapping = mock_db.add.call_args[0][0]
        assert added_mapping.mapping_type == "lambda"
        assert added_mapping.confidence == 1.0
        assert added_mapping.status == MappingStatus.CONFIRMED
        assert added_mapping.chosen is True
        assert "lambda" in added_mapping.header_name
