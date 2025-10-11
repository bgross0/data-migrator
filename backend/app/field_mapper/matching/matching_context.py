"""
Matching Context for field mapping.

This module provides the MatchingContext class which holds all necessary
information for the matching process.
"""
from typing import List, Optional, Set
from dataclasses import dataclass, field

from ..core.data_structures import ColumnProfile, FieldDefinition, ModelDefinition
from ..core.knowledge_base import OdooKnowledgeBase


@dataclass
class MatchingContext:
    """
    Context object that holds all information needed for field matching.

    This class encapsulates:
    - The knowledge base (Odoo models and fields)
    - Column profiles from the uploaded spreadsheet
    - Target models to consider (for scoped matching)
    - Additional metadata for decision making
    """

    # Knowledge base containing all Odoo information
    knowledge_base: OdooKnowledgeBase

    # Profile of the column we're trying to match
    column_profile: ColumnProfile

    # All column profiles from the same sheet (for contextual matching)
    all_column_profiles: List[ColumnProfile] = field(default_factory=list)

    # Target models to consider (if None, consider all models)
    target_models: Optional[Set[str]] = None

    # Candidate models detected from column names (for filtering)
    candidate_models: Optional[Set[str]] = None

    # Sheet name for context
    sheet_name: str = "Sheet1"

    # Additional metadata
    metadata: dict = field(default_factory=dict)

    def get_candidate_fields(self) -> List[FieldDefinition]:
        """
        Get all candidate fields to consider for matching.

        If target_models or candidate_models are set, only return fields
        from those models. Otherwise, return all fields from the knowledge base.

        Returns:
            List of FieldDefinition objects to consider
        """
        if self.target_models:
            models_to_search = self.target_models
        elif self.candidate_models:
            models_to_search = self.candidate_models
        else:
            # No filtering - consider all models
            return list(self.knowledge_base.fields.values())

        # Filter fields by model
        candidate_fields = []
        for (model_name, field_name), field in self.knowledge_base.fields.items():
            if model_name in models_to_search:
                candidate_fields.append(field)

        return candidate_fields

    def get_model_definitions(self, model_names: Set[str]) -> List[ModelDefinition]:
        """
        Get ModelDefinition objects for the given model names.

        Args:
            model_names: Set of model names to retrieve

        Returns:
            List of ModelDefinition objects
        """
        models = []
        for model_name in model_names:
            model = self.knowledge_base.get_model(model_name)
            if model:
                models.append(model)
        return models

    def get_related_models(
        self,
        model_name: str,
        max_depth: int = 1
    ) -> Set[str]:
        """
        Get models related to the given model within max_depth steps.

        Args:
            model_name: Starting model name
            max_depth: Maximum depth to traverse

        Returns:
            Set of related model names
        """
        return self.knowledge_base.get_related_models(model_name, max_depth)

    def filter_by_models(self, model_names: Set[str]) -> "MatchingContext":
        """
        Create a new MatchingContext filtered to specific models.

        Args:
            model_names: Set of model names to filter to

        Returns:
            New MatchingContext with target_models set
        """
        return MatchingContext(
            knowledge_base=self.knowledge_base,
            column_profile=self.column_profile,
            all_column_profiles=self.all_column_profiles,
            target_models=model_names,
            candidate_models=self.candidate_models,
            sheet_name=self.sheet_name,
            metadata=self.metadata.copy(),
        )

    def __repr__(self) -> str:
        """String representation of the context."""
        return (
            f"MatchingContext("
            f"column={self.column_profile.column_name}, "
            f"sheet={self.sheet_name}, "
            f"target_models={len(self.target_models) if self.target_models else 'all'}, "
            f"candidate_models={len(self.candidate_models) if self.candidate_models else 'none'})"
        )
