"""
Repository interfaces for data access.

Ports (interfaces) for lean stack → scale migration path:
- Current: SQLite
- Future: Postgres

Easy to swap implementations without changing business logic.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import polars as pl


class ExceptionsRepo(ABC):
    """
    Repository for managing validation exceptions.

    Exceptions track rows that fail validation during export pipeline.
    """

    @abstractmethod
    def add(
        self,
        dataset_id: int,
        model: str,
        row_ptr: str,
        error_code: str,
        hint: str,
        offending: Dict[str, Any],
    ) -> int:
        """
        Add a new exception record.

        Args:
            dataset_id: ID of the dataset
            model: Odoo model name (e.g., "res.partner")
            row_ptr: Stable row pointer (source_ptr from ingest)
            error_code: Error code (REQ_MISSING, ENUM_UNKNOWN, etc.)
            hint: Actionable hint for user
            offending: Dict of problematic field values

        Returns:
            Exception ID
        """
        pass

    @abstractmethod
    def list(
        self, dataset_id: int, model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List exceptions for a dataset.

        Args:
            dataset_id: ID of the dataset
            model: Optional model filter (e.g., "res.partner")

        Returns:
            List of exception dicts with all fields
        """
        pass

    @abstractmethod
    def clear(self, dataset_id: int, model: Optional[str] = None) -> int:
        """
        Clear exceptions for a dataset.

        Args:
            dataset_id: ID of the dataset
            model: Optional model filter (if None, clear all for dataset)

        Returns:
            Number of exceptions deleted
        """
        pass

    @abstractmethod
    def count(self, dataset_id: int, model: Optional[str] = None) -> int:
        """
        Count exceptions for a dataset.

        Args:
            dataset_id: ID of the dataset
            model: Optional model filter

        Returns:
            Number of exceptions
        """
        pass


class DatasetsRepo(ABC):
    """
    Repository for dataset operations.

    Provides access to dataset data (cleaned or raw).
    """

    @abstractmethod
    def get_dataframe(self, dataset_id: int, sheet_name: Optional[str] = None) -> pl.DataFrame:
        """
        Get DataFrame for a dataset.

        Prefers cleaned data if available, falls back to raw data.

        Args:
            dataset_id: ID of the dataset
            sheet_name: Optional sheet name filter

        Returns:
            Polars DataFrame with dataset data
        """
        pass

    @abstractmethod
    def put_artifact(self, dataset_id: int, name: str, path: str) -> None:
        """
        Store artifact metadata for a dataset.

        Args:
            dataset_id: ID of the dataset
            name: Artifact name (e.g., "export_res_partner.csv")
            path: Path to artifact file
        """
        pass

    @abstractmethod
    def get_artifact_path(self, dataset_id: int, name: str) -> Optional[str]:
        """
        Get artifact path by name.

        Args:
            dataset_id: ID of the dataset
            name: Artifact name

        Returns:
            Path to artifact, or None if not found
        """
        pass
