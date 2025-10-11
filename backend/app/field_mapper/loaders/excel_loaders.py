"""
Excel loaders for Odoo dictionary files.

This module provides loader classes for reading the 5 Odoo dictionary Excel files
and converting them into our internal data structures.
"""
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd

from ..core.data_structures import (
    ModelDefinition,
    FieldDefinition,
    SelectionOption,
    ConstraintDefinition,
    RelationDefinition,
)
from ..config.logging_config import knowledge_base_logger as logger


class ModelLoader:
    """
    Loader for Models (ir.model) Excel file.

    Expected columns:
    - Model: Technical model name (e.g., "account.account")
    - Model Description: Human-readable description
    - Type: Model type (e.g., "Base Object", "Custom")
    - Transient Model: Boolean indicating if transient
    """

    def __init__(self, file_path: Path):
        """
        Initialize the loader.

        Args:
            file_path: Path to the Models Excel file
        """
        self.file_path = Path(file_path)
        logger.info(f"Initialized ModelLoader for {self.file_path}")

    def load(self) -> List[ModelDefinition]:
        """
        Load models from the Excel file.

        Returns:
            List of ModelDefinition objects
        """
        logger.info(f"Loading models from {self.file_path}")

        try:
            df = pd.read_excel(self.file_path)
            logger.info(f"Read {len(df)} rows from models file")

            models = []
            for idx, row in df.iterrows():
                try:
                    model = ModelDefinition(
                        name=str(row["Model"]).strip(),
                        description=str(row["Model Description"]).strip(),
                        type=str(row["Type"]).strip(),
                        is_transient=bool(row["Transient Model"]),
                        field_ids=[],
                        parent_models=[],
                        child_models=[],
                    )
                    models.append(model)
                except Exception as e:
                    logger.error(f"Error parsing model at row {idx}: {e}")
                    logger.debug(f"Row data: {row.to_dict()}")

            logger.info(f"Successfully loaded {len(models)} models")
            return models

        except Exception as e:
            logger.error(f"Failed to load models from {self.file_path}: {e}")
            raise


class FieldLoader:
    """
    Loader for Fields (ir.model.fields) Excel file.

    Expected columns:
    - Field Name: Technical field name
    - Field Label: User-friendly label
    - Model: Parent model name
    - Field Type: Field type (char, integer, many2one, etc.)
    - Type: Base type (Base Field, Related Field, etc.)
    - Indexed: Boolean indicating if indexed
    - Stored: Boolean indicating if stored
    - Readonly: Boolean indicating if readonly
    - Related Model: For relational fields, the target model
    """

    def __init__(self, file_path: Path):
        """
        Initialize the loader.

        Args:
            file_path: Path to the Fields Excel file
        """
        self.file_path = Path(file_path)
        logger.info(f"Initialized FieldLoader for {self.file_path}")

    def load(self) -> List[FieldDefinition]:
        """
        Load fields from the Excel file.

        Returns:
            List of FieldDefinition objects
        """
        logger.info(f"Loading fields from {self.file_path}")

        try:
            df = pd.read_excel(self.file_path)
            logger.info(f"Read {len(df)} rows from fields file")

            fields = []
            for idx, row in df.iterrows():
                try:
                    # Handle NaN values for optional fields
                    related_model = row.get("Related Model")
                    if pd.isna(related_model):
                        related_model = None
                    else:
                        related_model = str(related_model).strip()

                    field = FieldDefinition(
                        name=str(row["Field Name"]).strip(),
                        label=str(row["Field Label"]).strip(),
                        model=str(row["Model"]).strip(),
                        field_type=str(row["Field Type"]).strip(),
                        base_type=str(row["Type"]).strip(),
                        is_indexed=bool(row["Indexed"]),
                        is_stored=bool(row["Stored"]),
                        is_readonly=bool(row["Readonly"]),
                        is_required=False,  # Will be determined from constraints
                        related_model=related_model,
                        size=None,  # Not in Excel, would be in field definition
                        domain=None,  # Not in Excel
                        selection_values=[],  # Will be populated from selections
                        help_text=None,  # Not in Excel
                    )
                    fields.append(field)
                except Exception as e:
                    logger.error(f"Error parsing field at row {idx}: {e}")
                    logger.debug(f"Row data: {row.to_dict()}")

            logger.info(f"Successfully loaded {len(fields)} fields")
            return fields

        except Exception as e:
            logger.error(f"Failed to load fields from {self.file_path}: {e}")
            raise


class SelectionLoader:
    """
    Loader for Fields Selection (ir.model.fields.selection) Excel file.

    Expected columns:
    - Sequence: Display order
    - Field: Full field identifier (e.g., "Type (Models)")
    - Value: Internal value
    - Name: Display name
    """

    def __init__(self, file_path: Path):
        """
        Initialize the loader.

        Args:
            file_path: Path to the Field Selections Excel file
        """
        self.file_path = Path(file_path)
        logger.info(f"Initialized SelectionLoader for {self.file_path}")

    def load(self) -> List[SelectionOption]:
        """
        Load selection options from the Excel file.

        Returns:
            List of SelectionOption objects
        """
        logger.info(f"Loading selections from {self.file_path}")

        try:
            df = pd.read_excel(self.file_path)
            logger.info(f"Read {len(df)} rows from selections file")

            selections = []
            for idx, row in df.iterrows():
                try:
                    selection = SelectionOption(
                        sequence=int(row["Sequence"]),
                        field=str(row["Field"]).strip(),
                        value=str(row["Value"]).strip(),
                        name=str(row["Name"]).strip(),
                    )
                    selections.append(selection)
                except Exception as e:
                    logger.error(f"Error parsing selection at row {idx}: {e}")
                    logger.debug(f"Row data: {row.to_dict()}")

            logger.info(f"Successfully loaded {len(selections)} selections")
            return selections

        except Exception as e:
            logger.error(f"Failed to load selections from {self.file_path}: {e}")
            raise


class ConstraintLoader:
    """
    Loader for Model Constraint (ir.model.constraint) Excel file.

    Expected columns:
    - Constraint Type: Type ('u' for unique, 'c' for check, 'f' for foreign key)
    - Constraint: Constraint name
    - Module: Odoo module defining the constraint
    - Model: Model the constraint applies to
    """

    def __init__(self, file_path: Path):
        """
        Initialize the loader.

        Args:
            file_path: Path to the Model Constraint Excel file
        """
        self.file_path = Path(file_path)
        logger.info(f"Initialized ConstraintLoader for {self.file_path}")

    def load(self) -> List[ConstraintDefinition]:
        """
        Load constraints from the Excel file.

        Returns:
            List of ConstraintDefinition objects
        """
        logger.info(f"Loading constraints from {self.file_path}")

        try:
            df = pd.read_excel(self.file_path)
            logger.info(f"Read {len(df)} rows from constraints file")

            constraints = []
            for idx, row in df.iterrows():
                try:
                    constraint = ConstraintDefinition(
                        type=str(row["Constraint Type"]).strip(),
                        name=str(row["Constraint"]).strip(),
                        module=str(row["Module"]).strip(),
                        model=str(row["Model"]).strip(),
                        definition="",  # Not provided in Excel
                        fields=[],  # Would need to parse constraint definition
                    )
                    constraints.append(constraint)
                except Exception as e:
                    logger.error(f"Error parsing constraint at row {idx}: {e}")
                    logger.debug(f"Row data: {row.to_dict()}")

            logger.info(f"Successfully loaded {len(constraints)} constraints")
            return constraints

        except Exception as e:
            logger.error(f"Failed to load constraints from {self.file_path}: {e}")
            raise


class RelationLoader:
    """
    Loader for Relation Model (ir.model.relation) Excel file.

    Expected columns:
    - Relation Name: Relation table name
    - Module: Odoo module defining the relation
    - Model: Model using this relation
    """

    def __init__(self, file_path: Path):
        """
        Initialize the loader.

        Args:
            file_path: Path to the Relation Model Excel file
        """
        self.file_path = Path(file_path)
        logger.info(f"Initialized RelationLoader for {self.file_path}")

    def load(self) -> List[RelationDefinition]:
        """
        Load relations from the Excel file.

        Returns:
            List of RelationDefinition objects
        """
        logger.info(f"Loading relations from {self.file_path}")

        try:
            df = pd.read_excel(self.file_path)
            logger.info(f"Read {len(df)} rows from relations file")

            relations = []
            for idx, row in df.iterrows():
                try:
                    relation = RelationDefinition(
                        name=str(row["Relation Name"]).strip(),
                        module=str(row["Module"]).strip(),
                        model=str(row["Model"]).strip(),
                        source_field=None,  # Not provided in Excel
                        target_field=None,  # Not provided in Excel
                    )
                    relations.append(relation)
                except Exception as e:
                    logger.error(f"Error parsing relation at row {idx}: {e}")
                    logger.debug(f"Row data: {row.to_dict()}")

            logger.info(f"Successfully loaded {len(relations)} relations")
            return relations

        except Exception as e:
            logger.error(f"Failed to load relations from {self.file_path}: {e}")
            raise


class OdooDictionaryLoader:
    """
    Orchestrator for loading all Odoo dictionary files.

    This class coordinates loading all 5 Excel files and returns them
    in a structured format.
    """

    def __init__(self, dictionary_path: Path):
        """
        Initialize the dictionary loader.

        Args:
            dictionary_path: Path to the directory containing all Excel files
        """
        self.dictionary_path = Path(dictionary_path)
        logger.info(f"Initialized OdooDictionaryLoader for {self.dictionary_path}")

        # Define expected file names (with variations)
        self.models_file = self._find_file(["Models (ir.model)", "Models"])
        self.fields_file = self._find_file(["Fields (ir.model.fields)", "Fields"])
        self.selections_file = self._find_file(
            ["Fields Selection (ir.model.fields.selection)", "Field Selections"]
        )
        self.constraints_file = self._find_file(
            ["Model Constraint (ir.model.constraint)", "Model Constraints"]
        )
        self.relations_file = self._find_file(
            ["Relation Model (ir.model.relation)", "Relations"]
        )

    def _find_file(self, name_variations: List[str]) -> Optional[Path]:
        """
        Find an Excel file by trying multiple name variations.

        Args:
            name_variations: List of possible file names (without extension)

        Returns:
            Path to the file if found, None otherwise
        """
        for name in name_variations:
            for ext in [".xlsx", ".xls"]:
                # Try with exact name
                path = self.dictionary_path / f"{name}{ext}"
                if path.exists():
                    logger.debug(f"Found file: {path}")
                    return path

                # Try with (1), (2), etc. suffix
                for i in range(1, 10):
                    path_with_num = self.dictionary_path / f"{name} ({i}){ext}"
                    if path_with_num.exists():
                        logger.debug(f"Found file: {path_with_num}")
                        return path_with_num

        logger.warning(f"Could not find file matching: {name_variations}")
        return None

    def load_all(self) -> Dict[str, List]:
        """
        Load all Odoo dictionary files.

        Returns:
            Dictionary containing:
                - models: List[ModelDefinition]
                - fields: List[FieldDefinition]
                - selections: List[SelectionOption]
                - constraints: List[ConstraintDefinition]
                - relations: List[RelationDefinition]
        """
        logger.info("Loading all Odoo dictionary files...")

        result = {
            "models": [],
            "fields": [],
            "selections": [],
            "constraints": [],
            "relations": [],
        }

        # Load models
        if self.models_file:
            loader = ModelLoader(self.models_file)
            result["models"] = loader.load()
        else:
            logger.error("Models file not found")

        # Load fields
        if self.fields_file:
            loader = FieldLoader(self.fields_file)
            result["fields"] = loader.load()
        else:
            logger.error("Fields file not found")

        # Load selections
        if self.selections_file:
            loader = SelectionLoader(self.selections_file)
            result["selections"] = loader.load()
        else:
            logger.error("Selections file not found")

        # Load constraints
        if self.constraints_file:
            loader = ConstraintLoader(self.constraints_file)
            result["constraints"] = loader.load()
        else:
            logger.error("Constraints file not found")

        # Load relations
        if self.relations_file:
            loader = RelationLoader(self.relations_file)
            result["relations"] = loader.load()
        else:
            logger.error("Relations file not found")

        logger.info(
            f"Finished loading dictionary: "
            f"{len(result['models'])} models, "
            f"{len(result['fields'])} fields, "
            f"{len(result['selections'])} selections, "
            f"{len(result['constraints'])} constraints, "
            f"{len(result['relations'])} relations"
        )

        return result
