"""
Tests for validator module.

Validates that each error code can be triggered and tracked.
"""
import pytest
import polars as pl
from unittest.mock import Mock
from app.validate.validator import Validator, ValidationResult
from app.registry.loader import ModelSpec, FieldSpec, SeedSpec


@pytest.fixture
def mock_exceptions_repo():
    """Mock exceptions repository."""
    repo = Mock()
    repo.add = Mock(return_value=1)
    return repo


@pytest.fixture
def fk_cache():
    """FK cache with available IDs."""
    return {"res.partner": {"partner_1", "partner_2", "partner_3"}}


@pytest.fixture
def seed_specs():
    """Seed specifications for enum resolution."""
    return {
        "crm_stages": SeedSpec(
            canonical={"stage_won": "stage_won", "stage_open": "stage_open"},
            synonyms_map={"won": "stage_won", "open": "stage_open"},
        )
    }


def test_validate_required_missing(mock_exceptions_repo, fk_cache):
    """Test REQ_MISSING error code."""
    model_spec = ModelSpec(
        name="res.partner",
        csv="export_res_partner.csv",
        id_template="partner_{slug(name)}",
        headers=["id", "name"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
        },
    )

    df = pl.DataFrame({"source_ptr": ["row1", "row2"], "name": ["Valid Name", None]})

    validator = Validator(mock_exceptions_repo, fk_cache, dataset_id=1)
    result = validator.validate(df, model_spec, {})

    assert result.exception_count == 1
    assert "REQ_MISSING" in result.exceptions_by_code
    assert len(result.valid_df) == 1
    mock_exceptions_repo.add.assert_called_once()
    call_args = mock_exceptions_repo.add.call_args[1]
    assert call_args["error_code"] == "REQ_MISSING"
    assert call_args["row_ptr"] == "row2"


def test_validate_invalid_email(mock_exceptions_repo, fk_cache):
    """Test INVALID_EMAIL error code."""
    model_spec = ModelSpec(
        name="res.partner",
        csv="export_res_partner.csv",
        id_template="partner_{slug(name)}",
        headers=["id", "name", "email"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
            "email": FieldSpec(name="email", type="email", transform="normalize_email"),
        },
    )

    df = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Name1", "Name2"],
        "email": ["valid@example.com", "not-an-email"],
    })

    validator = Validator(mock_exceptions_repo, fk_cache, dataset_id=1)
    result = validator.validate(df, model_spec, {})

    assert result.exception_count == 1
    assert "INVALID_EMAIL" in result.exceptions_by_code
    assert len(result.valid_df) == 1
    mock_exceptions_repo.add.assert_called_once()
    call_args = mock_exceptions_repo.add.call_args[1]
    assert call_args["error_code"] == "INVALID_EMAIL"
    assert call_args["row_ptr"] == "row2"


def test_validate_invalid_phone(mock_exceptions_repo, fk_cache):
    """Test INVALID_PHONE error code."""
    model_spec = ModelSpec(
        name="res.partner",
        csv="export_res_partner.csv",
        id_template="partner_{slug(name)}",
        headers=["id", "name", "phone"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
            "phone": FieldSpec(name="phone", type="phone", transform="normalize_phone_us"),
        },
    )

    df = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Name1", "Name2"],
        "phone": ["5551234567", "123"],  # Second phone invalid
    })

    validator = Validator(mock_exceptions_repo, fk_cache, dataset_id=1)
    result = validator.validate(df, model_spec, {})

    assert result.exception_count == 1
    assert "INVALID_PHONE" in result.exceptions_by_code
    assert len(result.valid_df) == 1


def test_validate_date_parse_fail(mock_exceptions_repo, fk_cache):
    """Test DATE_PARSE_FAIL error code."""
    model_spec = ModelSpec(
        name="crm.lead",
        csv="export_crm_lead.csv",
        id_template="lead_{slug(name)}",
        headers=["id", "name", "date_deadline"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
            "date_deadline": FieldSpec(
                name="date_deadline", type="date", transform="normalize_date_any"
            ),
        },
    )

    df = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Lead1", "Lead2"],
        "date_deadline": ["2024-01-15", "not-a-date"],
    })

    validator = Validator(mock_exceptions_repo, fk_cache, dataset_id=1)
    result = validator.validate(df, model_spec, {})

    assert result.exception_count == 1
    assert "DATE_PARSE_FAIL" in result.exceptions_by_code


def test_validate_enum_unknown(mock_exceptions_repo, fk_cache, seed_specs):
    """Test ENUM_UNKNOWN error code."""
    model_spec = ModelSpec(
        name="crm.lead",
        csv="export_crm_lead.csv",
        id_template="lead_{slug(name)}",
        headers=["id", "name", "stage_id/id"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
            "stage_id/id": FieldSpec(
                name="stage_id/id", type="enum", map_from_seed="crm_stages"
            ),
        },
    )

    df = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Lead1", "Lead2"],
        "stage_id/id": ["won", "unknown_stage"],  # Second stage unknown
    })

    validator = Validator(mock_exceptions_repo, fk_cache, dataset_id=1)
    result = validator.validate(df, model_spec, seed_specs)

    assert result.exception_count == 1
    assert "ENUM_UNKNOWN" in result.exceptions_by_code
    assert len(result.valid_df) == 1
    call_args = mock_exceptions_repo.add.call_args[1]
    assert call_args["error_code"] == "ENUM_UNKNOWN"
    assert call_args["row_ptr"] == "row2"


def test_validate_fk_unresolved(mock_exceptions_repo, fk_cache):
    """Test FK_UNRESOLVED error code."""
    model_spec = ModelSpec(
        name="crm.lead",
        csv="export_crm_lead.csv",
        id_template="lead_{slug(name)}",
        headers=["id", "name", "partner_id/id"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
            "partner_id/id": FieldSpec(
                name="partner_id/id", type="m2o", target="res.partner"
            ),
        },
    )

    df = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Lead1", "Lead2"],
        "partner_id/id": ["partner_1", "partner_999"],  # Second FK invalid
    })

    validator = Validator(mock_exceptions_repo, fk_cache, dataset_id=1)
    result = validator.validate(df, model_spec, {})

    assert result.exception_count == 1
    assert "FK_UNRESOLVED" in result.exceptions_by_code
    assert len(result.valid_df) == 1
    call_args = mock_exceptions_repo.add.call_args[1]
    assert call_args["error_code"] == "FK_UNRESOLVED"
    assert call_args["row_ptr"] == "row2"


def test_validate_multiple_errors_one_per_row(mock_exceptions_repo, fk_cache):
    """Test that only one exception per row is tracked per pass."""
    model_spec = ModelSpec(
        name="res.partner",
        csv="export_res_partner.csv",
        id_template="partner_{slug(name)}",
        headers=["id", "name", "email"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
            "email": FieldSpec(name="email", type="email", transform="normalize_email"),
        },
    )

    # Row with missing required + invalid email
    df = pl.DataFrame({
        "source_ptr": ["row1"],
        "name": [None],  # Missing required
        "email": ["not-an-email"],  # Invalid email
    })

    validator = Validator(mock_exceptions_repo, fk_cache, dataset_id=1)
    result = validator.validate(df, model_spec, {})

    # Should catch required first (validation order)
    assert result.exception_count == 1
    assert "REQ_MISSING" in result.exceptions_by_code
    assert len(result.valid_df) == 0


def test_validate_all_valid_rows(mock_exceptions_repo, fk_cache, seed_specs):
    """Test that all valid rows pass through."""
    model_spec = ModelSpec(
        name="res.partner",
        csv="export_res_partner.csv",
        id_template="partner_{slug(name)}",
        headers=["id", "name", "email"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
            "email": FieldSpec(name="email", type="email", transform="normalize_email"),
        },
    )

    df = pl.DataFrame({
        "source_ptr": ["row1", "row2", "row3"],
        "name": ["Name1", "Name2", "Name3"],
        "email": ["email1@example.com", "email2@example.com", "email3@example.com"],
    })

    validator = Validator(mock_exceptions_repo, fk_cache, dataset_id=1)
    result = validator.validate(df, model_spec, seed_specs)

    assert result.exception_count == 0
    assert len(result.valid_df) == 3
    assert len(result.exceptions_by_code) == 0
    mock_exceptions_repo.add.assert_not_called()


def test_validate_requires_source_ptr(mock_exceptions_repo, fk_cache):
    """Test that DataFrame must include source_ptr column."""
    model_spec = ModelSpec(
        name="res.partner",
        csv="export_res_partner.csv",
        id_template="partner_{slug(name)}",
        headers=["id", "name"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
        },
    )

    df = pl.DataFrame({"name": ["Name1", "Name2"]})  # Missing source_ptr

    validator = Validator(mock_exceptions_repo, fk_cache, dataset_id=1)

    with pytest.raises(ValueError, match="must include source_ptr column"):
        validator.validate(df, model_spec, {})


def test_validate_optional_enum_null_allowed(mock_exceptions_repo, fk_cache, seed_specs):
    """Test that optional enum fields allow null values."""
    model_spec = ModelSpec(
        name="crm.lead",
        csv="export_crm_lead.csv",
        id_template="lead_{slug(name)}",
        headers=["id", "name", "lost_reason_id/id"],
        fields={
            "id": FieldSpec(name="id", derived=True),
            "name": FieldSpec(name="name", required=True, type="string"),
            "lost_reason_id/id": FieldSpec(
                name="lost_reason_id/id",
                type="enum",
                map_from_seed="crm_lost_reasons",
                optional=True,
            ),
        },
    )

    df = pl.DataFrame({
        "source_ptr": ["row1", "row2"],
        "name": ["Lead1", "Lead2"],
        "lost_reason_id/id": [None, ""],  # Both should be allowed
    })

    validator = Validator(mock_exceptions_repo, fk_cache, dataset_id=1)
    result = validator.validate(df, model_spec, seed_specs)

    assert result.exception_count == 0
    assert len(result.valid_df) == 2
