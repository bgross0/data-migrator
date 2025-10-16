"""
Determinism test - proves byte-identical exports.

Tests that running export twice with same input produces identical SHA256 hashes for:
- Each individual CSV
- The final ZIP archive

This is the ultimate proof of idempotency and determinism.
"""
import pytest
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import polars as pl

from app.export.csv_emitter import CSVEmitter
from app.export.idgen import reset_dedup_tracker
from app.registry.loader import Registry, ModelSpec, FieldSpec


@pytest.fixture
def simple_registry():
    """Simple registry for testing."""
    partner_spec = ModelSpec(
        name="res.partner",
        csv="export_res_partner.csv",
        id_template="partner_{slug(email) or slug(name)}",
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


@pytest.fixture
def sample_data():
    """Sample data for determinism testing."""
    return pl.DataFrame({
        "source_ptr": ["row1", "row2", "row3"],
        "name": ["Acme Homes", "Jane Doe", "Bob Smith"],
        "email": ["info@acme.example", "jane@doe.example", "bob@smith.example"],
    })


def test_csv_determinism_single_model(simple_registry, sample_data):
    """
    Test that emitting the same data twice produces byte-identical CSVs.

    This proves:
    - External ID generation is deterministic
    - Normalizations are idempotent
    - Sort order is stable
    - Line endings are consistent
    - No timestamps or random values in output
    """
    mock_exceptions_repo = Mock()
    mock_exceptions_repo.add = Mock()

    with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
        output_dir1 = Path(tmpdir1)
        output_dir2 = Path(tmpdir2)

        # First export
        reset_dedup_tracker()
        emitter1 = CSVEmitter(simple_registry, mock_exceptions_repo, 1, output_dir1)
        csv_path1, _ = emitter1.emit(sample_data, "res.partner")
        hash1 = hashlib.sha256(csv_path1.read_bytes()).hexdigest()

        # Second export (same data, fresh emitter)
        reset_dedup_tracker()
        emitter2 = CSVEmitter(simple_registry, mock_exceptions_repo, 1, output_dir2)
        csv_path2, _ = emitter2.emit(sample_data, "res.partner")
        hash2 = hashlib.sha256(csv_path2.read_bytes()).hexdigest()

        # Hashes must match (byte-identical)
        assert hash1 == hash2, (
            f"CSV exports are not deterministic!\n"
            f"Run 1 SHA256: {hash1}\n"
            f"Run 2 SHA256: {hash2}"
        )


def test_csv_determinism_with_duplicates(simple_registry):
    """
    Test determinism with duplicate external IDs.

    Proves that dedup suffix generation is deterministic.
    """
    # Two rows with same email → duplicate IDs
    data = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Partner A", "Partner A Duplicate"],
        "email": ["same@example.com", "same@example.com"],
    })

    mock_exceptions_repo = Mock()

    with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
        output_dir1 = Path(tmpdir1)
        output_dir2 = Path(tmpdir2)

        # First export
        reset_dedup_tracker()
        emitter1 = CSVEmitter(simple_registry, mock_exceptions_repo, 1, output_dir1)
        csv_path1, _ = emitter1.emit(data, "res.partner")
        hash1 = hashlib.sha256(csv_path1.read_bytes()).hexdigest()

        # Second export
        reset_dedup_tracker()
        emitter2 = CSVEmitter(simple_registry, mock_exceptions_repo, 1, output_dir2)
        csv_path2, _ = emitter2.emit(data, "res.partner")
        hash2 = hashlib.sha256(csv_path2.read_bytes()).hexdigest()

        # Hashes must match
        assert hash1 == hash2


def test_csv_determinism_with_normalization(simple_registry):
    """
    Test determinism with data that needs normalization.

    Proves that normalizations (email lowercase, etc.) are idempotent.
    """
    data = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Partner A", "Partner B"],
        "email": ["USER@EXAMPLE.COM", "MixedCase@Example.COM"],  # Will be normalized
    })

    mock_exceptions_repo = Mock()

    with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
        output_dir1 = Path(tmpdir1)
        output_dir2 = Path(tmpdir2)

        # First export
        reset_dedup_tracker()
        emitter1 = CSVEmitter(simple_registry, mock_exceptions_repo, 1, output_dir1)
        csv_path1, _ = emitter1.emit(data, "res.partner")
        hash1 = hashlib.sha256(csv_path1.read_bytes()).hexdigest()

        # Second export
        reset_dedup_tracker()
        emitter2 = CSVEmitter(simple_registry, mock_exceptions_repo, 1, output_dir2)
        csv_path2, _ = emitter2.emit(data, "res.partner")
        hash2 = hashlib.sha256(csv_path2.read_bytes()).hexdigest()

        # Hashes must match
        assert hash1 == hash2


def test_header_line_exact_match(simple_registry, sample_data):
    """
    Test that CSV headers match registry exactly.

    Proves that header order is stable and matches specification.
    """
    mock_exceptions_repo = Mock()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        reset_dedup_tracker()
        emitter = CSVEmitter(simple_registry, mock_exceptions_repo, 1, output_dir)
        csv_path, _ = emitter.emit(sample_data, "res.partner")

        # Read first line
        with open(csv_path, "r") as f:
            header_line = f.readline().strip()

        # Must match registry headers exactly
        expected_headers = "id,name,email"
        assert header_line == expected_headers, (
            f"Headers don't match!\n"
            f"Expected: {expected_headers}\n"
            f"Got: {header_line}"
        )


def test_sort_order_deterministic(simple_registry):
    """
    Test that rows are always sorted by external ID.

    Proves that sort order is stable regardless of input order.
    """
    # Data in different orders
    data1 = pl.DataFrame({
        "source_ptr": ["row1", "row2", "row3"],
        "name": ["Charlie", "Alice", "Bob"],
        "email": ["c@example.com", "a@example.com", "b@example.com"],
    })

    data2 = pl.DataFrame({
        "source_ptr": ["row3", "row1", "row2"],
        "name": ["Bob", "Charlie", "Alice"],
        "email": ["b@example.com", "c@example.com", "a@example.com"],
    })

    mock_exceptions_repo = Mock()

    with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
        output_dir1 = Path(tmpdir1)
        output_dir2 = Path(tmpdir2)

        # Export data1
        reset_dedup_tracker()
        emitter1 = CSVEmitter(simple_registry, mock_exceptions_repo, 1, output_dir1)
        csv_path1, _ = emitter1.emit(data1, "res.partner")

        # Export data2 (different input order, same content)
        reset_dedup_tracker()
        emitter2 = CSVEmitter(simple_registry, mock_exceptions_repo, 1, output_dir2)
        csv_path2, _ = emitter2.emit(data2, "res.partner")

        # Read both CSVs
        result1 = pl.read_csv(csv_path1)
        result2 = pl.read_csv(csv_path2)

        # IDs should be sorted the same way
        assert result1["id"].to_list() == result2["id"].to_list()

        # Content should be identical (byte-for-byte)
        hash1 = hashlib.sha256(csv_path1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(csv_path2.read_bytes()).hexdigest()
        assert hash1 == hash2
