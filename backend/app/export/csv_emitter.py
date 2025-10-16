"""
CSV emitter - deterministic CSV generation with exact specs.

Polars-based implementation:
- write_csv(include_header=True, separator=',', quote_style='necessary', line_terminator='\n')
- Cast all columns to Utf8, fill nulls with empty string
- Sort by external ID (deterministic order)
- Assert header line equals registry headers exactly

Byte-identical on repeated runs (idempotent).
"""
from pathlib import Path
from typing import Dict, Set, List, Optional
import polars as pl
from app.registry.loader import ModelSpec, Registry
from app.export.idgen import render_id, reset_dedup_tracker, get_duplicate_info
from app.ports.repositories import ExceptionsRepo
from app.transform.normalizers import (
    normalize_phone_us,
    normalize_email,
    normalize_date_any,
    coerce_bool,
    coerce_enum,
    NormalizeError,
)


class CSVEmitter:
    """
    Emits deterministic CSVs for Odoo import.

    Features:
    - Deterministic external ID generation with dedup tracking
    - Apply normalizations (idempotent transforms)
    - Sort by external ID
    - Exact header order from registry
    - UTF-8, LF line endings, necessary quoting
    """

    def __init__(
        self,
        registry: Registry,
        exceptions_repo: ExceptionsRepo,
        dataset_id: int,
        output_dir: Path,
    ):
        """
        Initialize CSV emitter.

        Args:
            registry: Registry with model specs
            exceptions_repo: Repository for tracking exceptions
            dataset_id: Dataset ID
            output_dir: Output directory for CSVs
        """
        self.registry = registry
        self.exceptions_repo = exceptions_repo
        self.dataset_id = dataset_id
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def emit(
        self, df: pl.DataFrame, model_name: str
    ) -> tuple[Path, Set[str]]:
        """
        Emit CSV for a model.

        Args:
            df: Valid DataFrame (already validated)
            model_name: Odoo model name

        Returns:
            Tuple of (csv_path, emitted_external_ids)
        """
        model_spec = self.registry.models[model_name]

        # Reset dedup tracker for this model
        reset_dedup_tracker()

        # Generate external IDs
        df = self._generate_external_ids(df, model_spec)

        # Track duplicates as exceptions (all but first occurrence)
        self._track_duplicate_ids(df, model_spec)

        # Apply normalizations (final emit-time transforms)
        df = self._apply_normalizations(df, model_spec)

        # Apply rules (defaults, derived fields)
        df = self._apply_rules(df, model_spec)

        # Select and order columns per registry headers
        df = self._select_and_order_columns(df, model_spec)

        # Cast to Utf8 and fill nulls
        df = self._cast_and_fill(df)

        # Sort by external ID (deterministic)
        df = df.sort("id")

        # Write CSV
        csv_path = self.output_dir / model_spec.csv
        df.write_csv(
            csv_path,
            include_header=True,
            separator=",",
            quote_style="necessary",
            line_terminator="\n",
        )

        # Verify header line
        self._verify_headers(csv_path, model_spec)

        # Collect emitted external IDs
        emitted_ids = set(df["id"].to_list())

        return csv_path, emitted_ids

    def _generate_external_ids(
        self, df: pl.DataFrame, model_spec: ModelSpec
    ) -> pl.DataFrame:
        """Generate external IDs from template."""
        # Use map_elements to apply render_id to each row
        def generate_id(row_dict: Dict) -> str:
            return render_id(model_spec.id_template, row_dict, track_dedup=True)

        # Convert to row dicts, generate IDs, add back as column
        ids = []
        for row in df.iter_rows(named=True):
            external_id = generate_id(row)
            ids.append(external_id)

        return df.with_columns(pl.Series("id", ids))

    def _track_duplicate_ids(self, df: pl.DataFrame, model_spec: ModelSpec) -> None:
        """Track duplicate external IDs as exceptions (all but first)."""
        from app.export.idgen import get_duplicate_info

        # Check dedup tracker for IDs that were duplicated
        seen_base_ids = set()
        for row in df.iter_rows(named=True):
            external_id = row["id"]
            # Check if this ID has a suffix (_2, _3, etc.)
            if "_" in external_id:
                base_id = "_".join(external_id.split("_")[:-1])
                # Check if last part is numeric (dedup suffix)
                last_part = external_id.split("_")[-1]
                if last_part.isdigit() and int(last_part) > 1:
                    # This is a deduplicated ID
                    if base_id not in seen_base_ids:
                        seen_base_ids.add(base_id)

                    self.exceptions_repo.add(
                        dataset_id=self.dataset_id,
                        model=model_spec.name,
                        row_ptr=row.get("source_ptr", "unknown"),
                        error_code="DUP_EXT_ID",
                        hint=f"Duplicate external ID (deduplicated as '{external_id}')",
                        offending={"id": external_id, "base_id": base_id},
                    )

    def _apply_normalizations(
        self, df: pl.DataFrame, model_spec: ModelSpec
    ) -> pl.DataFrame:
        """Apply final normalizations (idempotent transforms)."""
        result_df = df.clone()

        for field_name, field_spec in model_spec.fields.items():
            if not field_spec.transform or field_name not in result_df.columns:
                continue

            # Get normalizer
            normalizer = None
            if field_spec.transform == "normalize_email":
                normalizer = normalize_email
            elif field_spec.transform == "normalize_phone_us":
                normalizer = normalize_phone_us
            elif field_spec.transform == "normalize_date_any":
                normalizer = normalize_date_any

            if not normalizer:
                continue

            # Apply using map_elements (skip nulls)
            def safe_normalize(value):
                if value is None or value == "":
                    return None
                try:
                    return normalizer(value)
                except NormalizeError:
                    return None  # Should already be caught by validator

            result_df = result_df.with_columns(
                pl.col(field_name).map_elements(safe_normalize, return_dtype=pl.Utf8)
            )

        return result_df

    def _apply_rules(self, df: pl.DataFrame, model_spec: ModelSpec) -> pl.DataFrame:
        """Apply defaults and rules from registry."""
        result_df = df.clone()

        for field_name, field_spec in model_spec.fields.items():
            # Apply defaults
            if field_spec.default is not None and field_name in result_df.columns:
                result_df = result_df.with_columns(
                    pl.col(field_name).fill_null(field_spec.default)
                )

            # Apply rules (DSL expressions) - already handled by rules.py in validation
            # For emit, we just ensure defaults are applied

        return result_df

    def _select_and_order_columns(
        self, df: pl.DataFrame, model_spec: ModelSpec
    ) -> pl.DataFrame:
        """Select columns per registry headers and order exactly."""
        # Select only headers (missing columns → null)
        selected_cols = []
        for header in model_spec.headers:
            if header in df.columns:
                selected_cols.append(pl.col(header))
            else:
                # Add null column for missing headers
                selected_cols.append(pl.lit(None).alias(header))

        return df.select(selected_cols)

    def _cast_and_fill(self, df: pl.DataFrame) -> pl.DataFrame:
        """Cast all columns to Utf8 and fill nulls with empty string."""
        # Cast all to Utf8
        casted = df.select([pl.col(c).cast(pl.Utf8) for c in df.columns])

        # Fill nulls with empty string
        filled = casted.select([pl.col(c).fill_null("") for c in casted.columns])

        return filled

    def _verify_headers(self, csv_path: Path, model_spec: ModelSpec) -> None:
        """Verify that CSV headers match registry exactly."""
        with open(csv_path, "r", encoding="utf-8") as f:
            header_line = f.readline().strip()

        expected_headers = ",".join(model_spec.headers)

        if header_line != expected_headers:
            raise ValueError(
                f"CSV headers mismatch for {model_spec.name}.\n"
                f"Expected: {expected_headers}\n"
                f"Got: {header_line}"
            )
