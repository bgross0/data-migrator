"""
Tests for CSV emitter.

Validates:
- Exact header order
- Sort by external ID
- Determinism (byte-identical repeated writes)
- UTF-8, LF line endings
- Dedup tracking with DUP_EXT_ID exceptions
"""
import pytest
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import Mock
import polars as pl
from app.export.csv_emitter import CSVEmitter
from app.export.idgen import reset_dedup_tracker
from app.registry.loader import Registry, ModelSpec, FieldSpec


@pytest.fixture
def temp_output_dir():
    """Temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_exceptions_repo():
    """Mock exceptions repository."""
    repo = Mock()
    repo.add = Mock(return_value=1)
    return repo


@pytest.fixture
def simple_registry():
    """Simple registry for testing."""
    partner_spec = ModelSpec(
        name="res.partner",
        csv="export_res_partner.csv",
        id_template="partner_{slug(email)}",
        headers=["id", "name", "email"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
            "email": FieldSpec(name="email", type="email", transform="normalize_email"),
        },
    )

    return Registry(
        version=1,
        import_order=["res.partner"],
        models={"res.partner": partner_spec},
        seeds={},
    )


def test_emit_basic(temp_output_dir, mock_exceptions_repo, simple_registry):
    """Test basic CSV emission."""
    df = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Partner A", "Partner B"],
        "email": ["a@example.com", "b@example.com"],
    })

    emitter = CSVEmitter(simple_registry, mock_exceptions_repo, 1, temp_output_dir)
    csv_path, emitted_ids = emitter.emit(df, "res.partner")

    assert csv_path.exists()
    assert len(emitted_ids) == 2

    # Verify content
    result_df = pl.read_csv(csv_path)
    assert list(result_df.columns) == ["id", "name", "email"]
    assert len(result_df) == 2


def test_emit_exact_header_order(temp_output_dir, mock_exceptions_repo, simple_registry):
    """Test that headers match registry exactly."""
    df = pl.DataFrame({
        "source_ptr": ["row1"],
        "name": ["Partner A"],
        "email": ["a@example.com"],
    })

    emitter = CSVEmitter(simple_registry, mock_exceptions_repo, 1, temp_output_dir)
    csv_path, _ = emitter.emit(df, "res.partner")

    # Read first line
    with open(csv_path, "r") as f:
        header_line = f.readline().strip()

    assert header_line == "id,name,email"


def test_emit_sorted_by_id(temp_output_dir, mock_exceptions_repo, simple_registry):
    """Test that rows are sorted by external ID."""
    df = pl.DataFrame({
        "source_ptr": ["row1", "row2", "row3"],
        "name": ["Partner C", "Partner A", "Partner B"],
        "email": ["c@example.com", "a@example.com", "b@example.com"],
    })

    emitter = CSVEmitter(simple_registry, mock_exceptions_repo, 1, temp_output_dir)
    csv_path, _ = emitter.emit(df, "res.partner")

    result_df = pl.read_csv(csv_path)

    # IDs should be sorted
    ids = result_df["id"].to_list()
    assert ids == sorted(ids)


def test_emit_deterministic(temp_output_dir, mock_exceptions_repo, simple_registry):
    """Test that repeated writes produce identical output."""
    df = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Partner A", "Partner B"],
        "email": ["a@example.com", "b@example.com"],
    })

    emitter = CSVEmitter(simple_registry, mock_exceptions_repo, 1, temp_output_dir)

    # First write
    reset_dedup_tracker()
    csv_path1, _ = emitter.emit(df, "res.partner")
    hash1 = hashlib.sha256(csv_path1.read_bytes()).hexdigest()

    # Second write (same data, fresh emitter)
    output_dir2 = temp_output_dir / "run2"
    output_dir2.mkdir()
    emitter2 = CSVEmitter(simple_registry, mock_exceptions_repo, 1, output_dir2)
    reset_dedup_tracker()
    csv_path2, _ = emitter2.emit(df, "res.partner")
    hash2 = hashlib.sha256(csv_path2.read_bytes()).hexdigest()

    # Should be byte-identical
    assert hash1 == hash2


def test_emit_duplicate_ids_tracked(temp_output_dir, mock_exceptions_repo, simple_registry):
    """Test that duplicate external IDs are tracked as exceptions."""
    # Two rows with same email → duplicate IDs
    df = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Partner A", "Partner A Duplicate"],
        "email": ["same@example.com", "same@example.com"],
    })

    emitter = CSVEmitter(simple_registry, mock_exceptions_repo, 1, temp_output_dir)
    reset_dedup_tracker()
    csv_path, emitted_ids = emitter.emit(df, "res.partner")

    # Should emit both rows (with _2 suffix for duplicate)
    result_df = pl.read_csv(csv_path)
    assert len(result_df) == 2

    # Should have called exceptions repo for duplicate
    mock_exceptions_repo.add.assert_called_once()
    call_args = mock_exceptions_repo.add.call_args[1]
    assert call_args["error_code"] == "DUP_EXT_ID"
    assert call_args["row_ptr"] == "row2"


def test_emit_cast_to_utf8_and_fill_nulls(temp_output_dir, mock_exceptions_repo, simple_registry):
    """Test that all columns are cast to Utf8 and nulls filled with empty string."""
    df = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Partner A", None],  # Null name
        "email": ["a@example.com", "b@example.com"],
    })

    emitter = CSVEmitter(simple_registry, mock_exceptions_repo, 1, temp_output_dir)
    csv_path, _ = emitter.emit(df, "res.partner")

    result_df = pl.read_csv(csv_path)

    # All columns should be Utf8
    for col in result_df.columns:
        assert result_df[col].dtype == pl.Utf8

    # Null should be empty string
    assert result_df["name"][1] == ""


def test_emit_line_endings(temp_output_dir, mock_exceptions_repo, simple_registry):
    """Test that CSV uses LF line endings."""
    df = pl.DataFrame({
        "source_ptr": ["row1"],
        "name": ["Partner A"],
        "email": ["a@example.com"],
    })

    emitter = CSVEmitter(simple_registry, mock_exceptions_repo, 1, temp_output_dir)
    csv_path, _ = emitter.emit(df, "res.partner")

    # Read as binary to check line endings
    content = csv_path.read_bytes()

    # Should not contain CRLF (Windows line endings)
    assert b"\r\n" not in content

    # Should contain LF (Unix line endings)
    assert b"\n" in content


def test_emit_normalization_applied(temp_output_dir, mock_exceptions_repo, simple_registry):
    """Test that normalizations are applied during emit."""
    df = pl.DataFrame({
        "source_ptr": ["row1"],
        "name": ["Partner A"],
        "email": ["USER@EXAMPLE.COM"],  # Uppercase email
    })

    emitter = CSVEmitter(simple_registry, mock_exceptions_repo, 1, temp_output_dir)
    csv_path, _ = emitter.emit(df, "res.partner")

    result_df = pl.read_csv(csv_path)

    # Email should be normalized to lowercase
    assert result_df["email"][0] == "user@example.com"


def test_emit_missing_columns_filled(temp_output_dir, mock_exceptions_repo):
    """Test that missing columns are added as null."""
    # Registry expects 3 columns, but DF only has 2
    partner_spec = ModelSpec(
        name="res.partner",
        csv="export_res_partner.csv",
        id_template="partner_{slug(name)}",
        headers=["id", "name", "email", "phone"],  # 4 headers
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
            "email": FieldSpec(name="email", type="email"),
            "phone": FieldSpec(name="phone", type="phone"),
        },
    )

    registry = Registry(
        version=1,
        import_order=["res.partner"],
        models={"res.partner": partner_spec},
        seeds={},
    )

    df = pl.DataFrame({
        "source_ptr": ["row1"],
        "name": ["Partner A"],
        "email": ["a@example.com"],
        # phone is missing
    })

    emitter = CSVEmitter(registry, mock_exceptions_repo, 1, temp_output_dir)
    csv_path, _ = emitter.emit(df, "res.partner")

    result_df = pl.read_csv(csv_path)

    # Should have all 4 columns
    assert list(result_df.columns) == ["id", "name", "email", "phone"]

    # Phone should be empty
    assert result_df["phone"][0] == ""
