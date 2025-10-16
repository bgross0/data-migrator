"""
Validator - validates DataFrames against model specs.

Validation order (one exception per row per pass):
1. Required fields → REQ_MISSING
2. Normalization → NORMALIZE_FAIL, INVALID_EMAIL, INVALID_PHONE, DATE_PARSE_FAIL
3. Enum values → ENUM_UNKNOWN
4. FK resolution → FK_UNRESOLVED
5. Duplicate external IDs → DUP_EXT_ID

Bad rows → exceptions table; good rows → continue to emit.
"""
from dataclasses import dataclass
from typing import Dict, Set, Optional, List
import polars as pl
from app.registry.loader import ModelSpec, FieldSpec
from app.ports.repositories import ExceptionsRepo
from app.transform.normalizers import (
    normalize_phone_us,
    normalize_email,
    normalize_date_any,
    coerce_bool,
    coerce_enum,
    NormalizeError,
)


@dataclass
class ValidationResult:
    """Result of validation."""

    valid_df: pl.DataFrame  # Rows that passed validation
    exception_count: int  # Number of rows that failed
    exceptions_by_code: Dict[str, int]  # Counts by error code


class Validator:
    """
    Validates DataFrames against model specifications.

    Tracks exceptions in repository, returns only valid rows.
    """

    def __init__(
        self,
        exceptions_repo: ExceptionsRepo,
        fk_cache: Dict[str, Set[str]],
        dataset_id: int,
    ):
        """
        Initialize validator.

        Args:
            exceptions_repo: Repository for storing exceptions
            fk_cache: In-memory cache of available external IDs {model: {id1, id2, ...}}
            dataset_id: ID of dataset being validated
        """
        self.exceptions_repo = exceptions_repo
        self.fk_cache = fk_cache
        self.dataset_id = dataset_id

    def validate(
        self, df: pl.DataFrame, model_spec: ModelSpec, seed_specs: Dict[str, any]
    ) -> ValidationResult:
        """
        Validate DataFrame against model spec.

        Args:
            df: Input DataFrame (must include source_ptr column)
            model_spec: Model specification
            seed_specs: Dict of seed specs for enum resolution

        Returns:
            ValidationResult with valid rows and exception counts
        """
        if "source_ptr" not in df.columns:
            raise ValueError("DataFrame must include source_ptr column for exceptions tracking")

        valid_mask = pl.Series([True] * len(df))
        exceptions_by_code: Dict[str, int] = {}

        # Validation passes (one exception per row per pass)
        valid_mask = self._validate_required(
            df, model_spec, valid_mask, exceptions_by_code
        )
        valid_mask = self._validate_normalization(
            df, model_spec, valid_mask, exceptions_by_code
        )
        valid_mask = self._validate_enums(
            df, model_spec, seed_specs, valid_mask, exceptions_by_code
        )
        valid_mask = self._validate_fks(
            df, model_spec, valid_mask, exceptions_by_code
        )

        # Note: DUP_EXT_ID is handled during ID generation in csv_emitter

        # Filter to valid rows
        valid_df = df.filter(valid_mask)
        exception_count = (~valid_mask).sum()

        return ValidationResult(
            valid_df=valid_df,
            exception_count=exception_count,
            exceptions_by_code=exceptions_by_code,
        )

    def _validate_required(
        self,
        df: pl.DataFrame,
        model_spec: ModelSpec,
        valid_mask: pl.Series,
        exceptions_by_code: Dict[str, int],
    ) -> pl.Series:
        """Validate required fields are not null."""
        for field_name, field_spec in model_spec.fields.items():
            if not field_spec.required or field_spec.derived:
                continue

            if field_name not in df.columns:
                continue

            # Find rows where required field is null
            null_mask = df[field_name].is_null()
            failed_mask = valid_mask & null_mask

            if failed_mask.sum() > 0:
                # Track first failure per row
                failed_df = df.filter(failed_mask)
                for row in failed_df.iter_rows(named=True):
                    self.exceptions_repo.add(
                        dataset_id=self.dataset_id,
                        model=model_spec.name,
                        row_ptr=row["source_ptr"],
                        error_code="REQ_MISSING",
                        hint=f"Required field '{field_name}' is missing",
                        offending={field_name: None},
                    )

                # Update counts and mask
                count = failed_mask.sum()
                exceptions_by_code["REQ_MISSING"] = (
                    exceptions_by_code.get("REQ_MISSING", 0) + count
                )
                valid_mask = valid_mask & ~failed_mask

        return valid_mask

    def _validate_normalization(
        self,
        df: pl.DataFrame,
        model_spec: ModelSpec,
        valid_mask: pl.Series,
        exceptions_by_code: Dict[str, int],
    ) -> pl.Series:
        """Validate that fields can be normalized."""
        for field_name, field_spec in model_spec.fields.items():
            if not field_spec.transform or field_name not in df.columns:
                continue

            # Get normalization function
            normalizer = None
            error_code = "NORMALIZE_FAIL"

            if field_spec.transform == "normalize_email":
                normalizer = normalize_email
                error_code = "INVALID_EMAIL"
            elif field_spec.transform == "normalize_phone_us":
                normalizer = normalize_phone_us
                error_code = "INVALID_PHONE"
            elif field_spec.transform == "normalize_date_any":
                normalizer = normalize_date_any
                error_code = "DATE_PARSE_FAIL"

            if not normalizer:
                continue

            # Test normalization on valid rows only
            test_df = df.filter(valid_mask)
            if len(test_df) == 0:
                continue

            failed_rows = []
            for row in test_df.iter_rows(named=True):
                value = row.get(field_name)
                if value is None or value == "":
                    continue  # Skip nulls (handled by required check)

                try:
                    normalizer(value)
                except NormalizeError as e:
                    failed_rows.append(
                        {
                            "source_ptr": row["source_ptr"],
                            "value": value,
                            "error": str(e),
                        }
                    )

            if failed_rows:
                # Add exceptions
                for failed in failed_rows:
                    self.exceptions_repo.add(
                        dataset_id=self.dataset_id,
                        model=model_spec.name,
                        row_ptr=failed["source_ptr"],
                        error_code=error_code,
                        hint=f"Field '{field_name}' normalization failed: {failed['error']}",
                        offending={field_name: failed["value"]},
                    )

                # Update mask
                failed_ptrs = {f["source_ptr"] for f in failed_rows}
                failed_mask = df["source_ptr"].is_in(list(failed_ptrs))
                count = failed_mask.sum()
                exceptions_by_code[error_code] = (
                    exceptions_by_code.get(error_code, 0) + count
                )
                valid_mask = valid_mask & ~failed_mask

        return valid_mask

    def _validate_enums(
        self,
        df: pl.DataFrame,
        model_spec: ModelSpec,
        seed_specs: Dict[str, any],
        valid_mask: pl.Series,
        exceptions_by_code: Dict[str, int],
    ) -> pl.Series:
        """Validate enum values against seed mappings."""
        for field_name, field_spec in model_spec.fields.items():
            if field_spec.type != "enum" or field_name not in df.columns:
                continue

            # Get synonyms map
            synonyms_map = {}
            mapping = field_spec.map or {}

            if field_spec.map_from_seed:
                seed_spec = seed_specs.get(field_spec.map_from_seed)
                if seed_spec:
                    synonyms_map = seed_spec.synonyms_map
                    # Add canonical values
                    for canonical_id in seed_spec.canonical.values():
                        synonyms_map[canonical_id] = canonical_id

            # Test enum resolution on valid rows only
            test_df = df.filter(valid_mask)
            if len(test_df) == 0:
                continue

            failed_rows = []
            for row in test_df.iter_rows(named=True):
                value = row.get(field_name)
                if value is None or value == "":
                    if field_spec.optional:
                        continue
                    # Non-optional enum with null value
                    failed_rows.append({"source_ptr": row["source_ptr"], "value": None})
                    continue

                try:
                    coerce_enum(value, mapping, synonyms_map)
                except NormalizeError:
                    failed_rows.append(
                        {"source_ptr": row["source_ptr"], "value": value}
                    )

            if failed_rows:
                # Add exceptions
                for failed in failed_rows:
                    self.exceptions_repo.add(
                        dataset_id=self.dataset_id,
                        model=model_spec.name,
                        row_ptr=failed["source_ptr"],
                        error_code="ENUM_UNKNOWN",
                        hint=f"Unknown enum value for '{field_name}': {failed['value']}",
                        offending={field_name: failed["value"]},
                    )

                # Update mask
                failed_ptrs = {f["source_ptr"] for f in failed_rows}
                failed_mask = df["source_ptr"].is_in(list(failed_ptrs))
                count = failed_mask.sum()
                exceptions_by_code["ENUM_UNKNOWN"] = (
                    exceptions_by_code.get("ENUM_UNKNOWN", 0) + count
                )
                valid_mask = valid_mask & ~failed_mask

        return valid_mask

    def _validate_fks(
        self,
        df: pl.DataFrame,
        model_spec: ModelSpec,
        valid_mask: pl.Series,
        exceptions_by_code: Dict[str, int],
    ) -> pl.Series:
        """Validate FK fields against available IDs in cache."""
        for field_name, field_spec in model_spec.fields.items():
            if field_spec.type != "m2o" or field_name not in df.columns:
                continue

            target_model = field_spec.target
            if not target_model or target_model not in self.fk_cache:
                continue

            available_ids = self.fk_cache[target_model]

            # Test FK resolution on valid rows only
            test_df = df.filter(valid_mask)
            if len(test_df) == 0:
                continue

            failed_rows = []
            for row in test_df.iter_rows(named=True):
                fk_value = row.get(field_name)
                if fk_value is None or fk_value == "":
                    continue  # Nullable FK

                if fk_value not in available_ids:
                    failed_rows.append(
                        {"source_ptr": row["source_ptr"], "value": fk_value}
                    )

            if failed_rows:
                # Add exceptions
                for failed in failed_rows:
                    self.exceptions_repo.add(
                        dataset_id=self.dataset_id,
                        model=model_spec.name,
                        row_ptr=failed["source_ptr"],
                        error_code="FK_UNRESOLVED",
                        hint=f"FK '{field_name}' references non-existent '{target_model}': {failed['value']}",
                        offending={field_name: failed["value"]},
                    )

                # Update mask
                failed_ptrs = {f["source_ptr"] for f in failed_rows}
                failed_mask = df["source_ptr"].is_in(list(failed_ptrs))
                count = failed_mask.sum()
                exceptions_by_code["FK_UNRESOLVED"] = (
                    exceptions_by_code.get("FK_UNRESOLVED", 0) + count
                )
                valid_mask = valid_mask & ~failed_mask

        return valid_mask
