"""
DeterministicFieldMapper - Main entry point for the field mapping system.

This is the primary interface for using the deterministic field mapper.
"""
from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd

from .core.knowledge_base import OdooKnowledgeBase
from .core.data_structures import ColumnProfile, FieldMapping, MappingResult, MappingStatus
from .profiling.column_profiler import ColumnProfiler
from .matching.matching_pipeline import MatchingPipeline
from .config.settings import FieldMapperSettings
from .config.logging_config import setup_logger

logger = setup_logger(__name__)


class DeterministicFieldMapper:
    """
    Main class for deterministic field mapping.

    This class provides a high-level interface for:
    1. Loading Odoo dictionary definitions
    2. Profiling uploaded spreadsheets
    3. Matching columns to Odoo fields
    4. Generating mapping results

    Usage:
        mapper = DeterministicFieldMapper(dictionary_path="/path/to/odoo-dictionary")
        result = mapper.map_file("/path/to/spreadsheet.xlsx")
    """

    def __init__(
        self,
        dictionary_path: Union[str, Path],
        settings: Optional[FieldMapperSettings] = None
    ):
        """
        Initialize the field mapper.

        Args:
            dictionary_path: Path to the odoo-dictionary directory
            settings: Optional FieldMapperSettings for configuration
        """
        self.dictionary_path = Path(dictionary_path)
        self.settings = settings or FieldMapperSettings()

        logger.info(f"Initializing DeterministicFieldMapper")
        logger.info(f"Dictionary path: {self.dictionary_path}")

        # Initialize knowledge base
        self.knowledge_base = OdooKnowledgeBase(dictionary_path=self.dictionary_path)

        # Load the knowledge base
        self._load_knowledge_base()

        # Initialize profiler
        self.profiler = ColumnProfiler(sample_size=self.settings.sample_size)

        # Initialize matching pipeline
        self.pipeline = MatchingPipeline(
            knowledge_base=self.knowledge_base,
            settings=self.settings
        )

        logger.info("DeterministicFieldMapper initialized successfully")

    def _load_knowledge_base(self) -> None:
        """
        Load the knowledge base from Odoo dictionary files.
        """
        logger.info("Loading knowledge base...")
        try:
            self.knowledge_base.load_from_dictionary()
            stats = self.knowledge_base.get_statistics()
            logger.info(
                f"Knowledge base loaded: "
                f"{stats['total_models']} models, "
                f"{stats['total_fields']} fields, "
                f"{stats['total_selections']} selections"
            )
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}", exc_info=True)
            raise

    def map_file(
        self,
        file_path: Union[str, Path],
        sheet_name: Optional[str] = None
    ) -> MappingResult:
        """
        Map a spreadsheet file to Odoo fields.

        Args:
            file_path: Path to the Excel or CSV file
            sheet_name: Optional sheet name (for Excel files with multiple sheets)

        Returns:
            MappingResult with all mappings and metadata
        """
        file_path = Path(file_path)
        logger.info(f"Mapping file: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine file type
        if file_path.suffix.lower() in ['.xlsx', '.xls']:
            return self._map_excel_file(file_path, sheet_name)
        elif file_path.suffix.lower() == '.csv':
            return self._map_csv_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    def _map_excel_file(
        self,
        file_path: Path,
        sheet_name: Optional[str] = None
    ) -> MappingResult:
        """
        Map an Excel file to Odoo fields.

        Args:
            file_path: Path to the Excel file
            sheet_name: Optional sheet name

        Returns:
            MappingResult with all mappings
        """
        logger.info(f"Processing Excel file: {file_path}")

        # Read Excel file
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            sheets = {sheet_name: df}
        else:
            # Read all sheets
            sheets = pd.read_excel(file_path, sheet_name=None)

        # Process each sheet
        all_mappings = {}
        all_profiles = {}

        for sheet_name, df in sheets.items():
            logger.info(f"Processing sheet: {sheet_name}")

            # Profile all columns
            profiles = self.profiler.profile_dataframe(df, sheet_name=sheet_name)
            all_profiles[sheet_name] = profiles

            # Match columns
            mappings = self.pipeline.match_sheet(profiles, sheet_name=sheet_name)
            all_mappings[sheet_name] = mappings

        # Create result
        result = MappingResult(
            status=MappingStatus.SUCCESS,
            mappings=all_mappings,
            column_profiles=all_profiles,
            errors=[],
            warnings=[],
            statistics={
                "total_sheets": len(sheets),
                "total_columns": sum(len(profiles) for profiles in all_profiles.values()),
                "total_mappings": sum(
                    len(mappings) for sheet_mappings in all_mappings.values()
                    for mappings in sheet_mappings.values()
                ),
            },
        )

        logger.info(f"Mapping complete: {result.statistics}")

        return result

    def _map_csv_file(self, file_path: Path) -> MappingResult:
        """
        Map a CSV file to Odoo fields.

        Args:
            file_path: Path to the CSV file

        Returns:
            MappingResult with all mappings
        """
        logger.info(f"Processing CSV file: {file_path}")

        # Read CSV file
        df = pd.read_csv(file_path)
        sheet_name = file_path.stem  # Use filename as sheet name

        # Profile all columns
        profiles = self.profiler.profile_dataframe(df, sheet_name=sheet_name)

        # Match columns
        mappings = self.pipeline.match_sheet(profiles, sheet_name=sheet_name)

        # Create result
        result = MappingResult(
            status=MappingStatus.SUCCESS,
            mappings={sheet_name: mappings},
            column_profiles={sheet_name: profiles},
            errors=[],
            warnings=[],
            statistics={
                "total_sheets": 1,
                "total_columns": len(profiles),
                "total_mappings": sum(len(m) for m in mappings.values()),
            },
        )

        logger.info(f"Mapping complete: {result.statistics}")

        return result

    def map_dataframe(
        self,
        df: pd.DataFrame,
        sheet_name: str = "Data",
        selected_modules: Optional[List[str]] = None
    ) -> Dict[str, List[FieldMapping]]:
        """
        Map a pandas DataFrame to Odoo fields.

        Args:
            df: Pandas DataFrame to map
            sheet_name: Name for this dataset
            selected_modules: Optional list of module names to constrain matching

        Returns:
            Dictionary mapping column names to FieldMapping lists
        """
        logger.info(f"Processing DataFrame: {sheet_name}")
        if selected_modules:
            logger.info(f"Using selected modules: {selected_modules}")

        # Profile all columns
        profiles = self.profiler.profile_dataframe(df, sheet_name=sheet_name)

        # Match columns
        mappings = self.pipeline.match_sheet(
            profiles,
            sheet_name=sheet_name,
            selected_modules=selected_modules
        )

        return mappings

    def get_field_suggestions(
        self,
        column_name: str,
        sample_values: List,
        data_type: str,
        max_suggestions: int = 10
    ) -> List[FieldMapping]:
        """
        Get field suggestions for a single column.

        Args:
            column_name: Name of the column
            sample_values: Sample values from the column
            data_type: Detected data type
            max_suggestions: Maximum number of suggestions

        Returns:
            List of FieldMapping suggestions
        """
        # Create a minimal column profile
        non_null_count = len([v for v in sample_values if v is not None])
        unique_count = len(set(sample_values))
        profile = ColumnProfile(
            column_name=column_name,
            sheet_name="manual",
            data_type=data_type,
            sample_values=sample_values,
            total_rows=len(sample_values),
            non_null_count=non_null_count,
            unique_count=unique_count,
            null_percentage=0.0,
            uniqueness_ratio=unique_count / non_null_count if non_null_count > 0 else 0.0,
            patterns={},
            value_frequencies={},
        )

        # Match
        mappings = self.pipeline.match_column(
            column_profile=profile,
            all_column_profiles=[profile],
            max_results=max_suggestions
        )

        return mappings

    def reload_knowledge_base(self) -> None:
        """
        Reload the knowledge base from dictionary files.

        Useful if the dictionary files have been updated.
        """
        logger.info("Reloading knowledge base...")
        self.knowledge_base.load_from_dictionary(force_reload=True)
        logger.info("Knowledge base reloaded")

    def get_statistics(self) -> Dict:
        """
        Get statistics about the field mapper.

        Returns:
            Dictionary with statistics
        """
        kb_stats = self.knowledge_base.get_statistics()
        pipeline_stats = self.pipeline.get_statistics()

        return {
            "knowledge_base": kb_stats,
            "pipeline": pipeline_stats,
            "settings": {
                "confidence_threshold": self.settings.confidence_threshold,
                "sample_size": self.settings.sample_size,
            }
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"DeterministicFieldMapper("
            f"models={len(self.knowledge_base.models)}, "
            f"fields={len(self.knowledge_base.fields)}, "
            f"loaded={self.knowledge_base.is_loaded})"
        )
