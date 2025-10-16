"""
Matching Pipeline - Orchestrates all matching strategies.

This module provides the MatchingPipeline class which coordinates all 8 matching
strategies to find the best field mappings for spreadsheet columns.
"""
from typing import List, Dict, Optional, Set
from collections import defaultdict

from .base_strategy import BaseStrategy
from .business_context_analyzer import BusinessContextAnalyzer
from .cell_data_analyzer import CellDataAnalyzer
from .strategies import (
    ExactNameMatchStrategy,
    LabelMatchStrategy,
    SelectionValueMatchStrategy,
    DataTypeCompatibilityStrategy,
    PatternMatchStrategy,
    StatisticalSimilarityStrategy,
    ContextualMatchStrategy,
    FuzzyMatchStrategy,
)
from .matching_context import MatchingContext
from ..core.data_structures import FieldMapping, ColumnProfile
from ..core.knowledge_base import OdooKnowledgeBase
from ..config.settings import FieldMapperSettings
from ..config.logging_config import matching_logger as logger


class MatchingPipeline:
    """
    Orchestrates all matching strategies to find best field mappings.

    The pipeline:
    1. Runs all enabled strategies on the column
    2. Collects all candidate mappings
    3. Merges duplicate candidates (same model+field)
    4. Ranks candidates by combined confidence scores
    5. Returns top N mappings with alternatives
    """

    def __init__(
        self,
        knowledge_base: OdooKnowledgeBase,
        settings: Optional[FieldMapperSettings] = None
    ):
        """
        Initialize the matching pipeline.

        Args:
            knowledge_base: OdooKnowledgeBase with all Odoo information
            settings: FieldMapperSettings for configuration
        """
        self.knowledge_base = knowledge_base
        self.settings = settings or FieldMapperSettings()

        # Initialize analyzers for intelligent context detection
        self.business_analyzer = BusinessContextAnalyzer()
        self.cell_analyzer = CellDataAnalyzer()

        # Initialize all strategies with configured weights
        self.strategies: List[BaseStrategy] = [
            ExactNameMatchStrategy(weight=self.settings.exact_match_weight),
            LabelMatchStrategy(weight=self.settings.label_match_weight),
            SelectionValueMatchStrategy(weight=self.settings.selection_value_weight),
            DataTypeCompatibilityStrategy(weight=self.settings.data_type_weight),
            PatternMatchStrategy(weight=self.settings.pattern_match_weight),
            StatisticalSimilarityStrategy(weight=self.settings.statistical_weight),
            ContextualMatchStrategy(weight=self.settings.contextual_weight),
            FuzzyMatchStrategy(weight=self.settings.fuzzy_match_weight),
        ]

        logger.info(
            f"MatchingPipeline initialized with {len(self.strategies)} strategies and context analyzers"
        )

    def match_column(
        self,
        column_profile: ColumnProfile,
        all_column_profiles: List[ColumnProfile],
        target_models: Optional[Set[str]] = None,
        candidate_models: Optional[Set[str]] = None,
        max_results: Optional[int] = None
    ) -> List[FieldMapping]:
        """
        Find best field mappings for a column.

        Args:
            column_profile: Profile of the column to match
            all_column_profiles: Profiles of all columns in the sheet (for context)
            target_models: Optional set of models to restrict matching to
            candidate_models: Optional set of likely models detected from context
            max_results: Maximum number of results to return

        Returns:
            List of FieldMapping objects, sorted by confidence (highest first)
        """
        # Use settings value if max_results not provided
        if max_results is None:
            max_results = self.settings.max_suggestions

        logger.info(f"Matching column: {column_profile.column_name}")

        # Create matching context
        context = MatchingContext(
            knowledge_base=self.knowledge_base,
            column_profile=column_profile,
            all_column_profiles=all_column_profiles,
            target_models=target_models,
            candidate_models=candidate_models,
            sheet_name=column_profile.sheet_name,
        )

        # Run all strategies
        all_candidates: List[FieldMapping] = []

        for strategy in self.strategies:
            try:
                logger.debug(f"Running strategy: {strategy.name}")
                candidates = strategy.match(context)
                all_candidates.extend(candidates)
                logger.debug(
                    f"Strategy {strategy.name} returned {len(candidates)} candidates"
                )
            except Exception as e:
                logger.error(f"Error in strategy {strategy.name}: {e}", exc_info=True)

        logger.info(
            f"Total candidates before merging: {len(all_candidates)}"
        )

        # Merge duplicate candidates
        merged_candidates = self._merge_duplicates(all_candidates)

        # Apply model priority based on detected context
        merged_candidates = self._apply_model_priority(
            merged_candidates,
            candidate_models,
            column_profile
        )

        logger.info(
            f"Total candidates after merging and prioritization: {len(merged_candidates)}"
        )

        # Rank candidates
        ranked_candidates = self._rank_candidates(merged_candidates)

        # Two-tier confidence system (use settings)
        HIGH_CONFIDENCE = self.settings.high_confidence_threshold
        MEDIUM_CONFIDENCE = self.settings.medium_confidence_threshold

        # Filter by medium confidence threshold (more inclusive)
        all_viable_candidates = [
            m for m in ranked_candidates
            if m.confidence >= MEDIUM_CONFIDENCE
        ]

        logger.info(
            f"Candidates after confidence filter (≥{MEDIUM_CONFIDENCE}): {len(all_viable_candidates)}"
        )

        # Return top N results with alternatives
        if not all_viable_candidates:
            logger.warning(f"No viable matches found for {column_profile.column_name}")
            return []

        # Tag confidence tier for each candidate
        for candidate in all_viable_candidates:
            if candidate.confidence >= HIGH_CONFIDENCE:
                candidate.confidence_tier = "high"
            elif candidate.confidence >= MEDIUM_CONFIDENCE:
                candidate.confidence_tier = "medium"
            else:
                candidate.confidence_tier = "low"

        # Best match
        best_match = all_viable_candidates[0]

        # Alternatives (remaining candidates)
        best_match.alternatives = all_viable_candidates[1:max_results]

        logger.info(
            f"Best match for '{column_profile.column_name}': "
            f"{best_match.target_model}.{best_match.target_field} "
            f"(confidence={best_match.confidence:.2f}, tier={best_match.confidence_tier})"
        )

        return all_viable_candidates[:max_results]

    def match_sheet(
        self,
        column_profiles: List[ColumnProfile],
        sheet_name: str = "Sheet1",
        selected_modules: Optional[List[str]] = None
    ) -> Dict[str, List[FieldMapping]]:
        """
        Match all columns in a sheet.

        Args:
            column_profiles: List of ColumnProfile objects for the sheet
            sheet_name: Name of the sheet
            selected_modules: Optional list of module names to constrain matching

        Returns:
            Dictionary mapping column names to their field mappings
        """
        logger.info(f"Matching sheet '{sheet_name}' with {len(column_profiles)} columns")

        # If modules are pre-selected, get the associated models
        target_models = None
        if selected_modules:
            logger.info(f"Using pre-selected modules: {selected_modules}")
            from ..core.module_registry import get_module_registry
            registry = get_module_registry()
            target_models = registry.get_models_for_groups(selected_modules)
            logger.info(f"Module selection provides {len(target_models)} models")

        # Detect candidate models from all columns (for contextual matching)
        candidate_models = self._detect_candidate_models(column_profiles)

        # If we have selected modules, constrain candidate models
        if target_models:
            candidate_models = candidate_models & target_models
            logger.info(
                f"After module filtering: {len(candidate_models)} candidate models"
            )

        logger.info(
            f"Detected {len(candidate_models)} candidate models: "
            f"{', '.join(list(candidate_models)[:5])}"
        )

        # Match each column
        results = {}

        for col_profile in column_profiles:
            try:
                mappings = self.match_column(
                    column_profile=col_profile,
                    all_column_profiles=column_profiles,
                    target_models=target_models,  # Pass target models constraint
                    candidate_models=candidate_models,
                )
                results[col_profile.column_name] = mappings
            except Exception as e:
                logger.error(
                    f"Error matching column '{col_profile.column_name}': {e}",
                    exc_info=True
                )
                results[col_profile.column_name] = []

        logger.info(f"Successfully matched {len(results)} columns")

        lambda_mappings = self._generate_lambda_suggestions(
            column_profiles,
            results
        )
        if lambda_mappings:
            logger.info(
                "Generated %s lambda-based mapping suggestion(s)",
                len(lambda_mappings),
            )
            results.update(lambda_mappings)

        return results

    def _generate_lambda_suggestions(
        self,
        column_profiles: List[ColumnProfile],
        existing_results: Dict[str, List[FieldMapping]],
    ) -> Dict[str, List[FieldMapping]]:
        """
        Create heuristic lambda mapping suggestions based on available columns.

        Currently supports combining first/last name style columns into
        res.partner.name.
        """
        suggestions: Dict[str, List[FieldMapping]] = {}

        column_names = [profile.column_name for profile in column_profiles]
        first_name_cols = [
            name for name in column_names if self._looks_like_first_name(name)
        ]
        last_name_cols = [
            name for name in column_names if self._looks_like_last_name(name)
        ]

        if not first_name_cols or not last_name_cols:
            return suggestions

        # Prefer the first detected columns for heuristics.
        first_col = first_name_cols[0]
        last_col = last_name_cols[0]

        virtual_column = "lambda_name"

        # Avoid duplicating an existing lambda suggestion.
        if virtual_column in existing_results or virtual_column in suggestions:
            return suggestions

        lambda_fn = (
            "lambda self, row, **kwargs: (' '.join("
            f"str(part).strip() for part in (row.get('{first_col}'), row.get('{last_col}')) if part"
            ")) or None"
        )

        mapping = FieldMapping(
            source_column=virtual_column,
            target_model="res.partner",
            target_field="name",
            confidence=0.85,
            scores={"lambda_heuristic": 0.85},
            rationale=(
                f"[LambdaHeuristics] Combine '{first_col}' and '{last_col}' "
                "into res.partner name"
            ),
            matching_strategy="LambdaHeuristics",
            alternatives=[],
            transformations=[],
            mapping_type="lambda",
            lambda_function=lambda_fn,
            lambda_dependencies=[first_col, last_col],
        )

        suggestions[virtual_column] = [mapping]
        return suggestions

    @staticmethod
    def _normalize_header(value: str) -> str:
        """Normalize a column header for rule-based detection."""
        return value.lower().replace("_", " ").strip()

    def _looks_like_first_name(self, value: str) -> bool:
        normalized = self._normalize_header(value)
        return "first" in normalized and "name" in normalized

    def _looks_like_last_name(self, value: str) -> bool:
        normalized = self._normalize_header(value)
        return "last" in normalized and "name" in normalized

    def _merge_duplicates(
        self,
        candidates: List[FieldMapping]
    ) -> List[FieldMapping]:
        """
        Merge duplicate candidates (same model+field) by combining scores.

        Args:
            candidates: List of FieldMapping objects

        Returns:
            List of merged FieldMapping objects
        """
        # Group by (model, field)
        groups: Dict[tuple, List[FieldMapping]] = defaultdict(list)

        for candidate in candidates:
            key = (candidate.target_model, candidate.target_field)
            groups[key].append(candidate)

        # Merge each group
        merged = []

        for (model, field), group_candidates in groups.items():
            if len(group_candidates) == 1:
                # No duplicates
                merged.append(group_candidates[0])
                continue

            # Merge multiple candidates
            merged_candidate = self._merge_candidate_group(group_candidates)
            merged.append(merged_candidate)

        return merged

    def _merge_candidate_group(
        self,
        candidates: List[FieldMapping]
    ) -> FieldMapping:
        """
        Merge a group of candidates for the same field.

        Args:
            candidates: List of FieldMapping objects for the same field

        Returns:
            Single merged FieldMapping
        """
        # Use the highest confidence as base
        best = max(candidates, key=lambda c: c.confidence)

        # Combine scores from all strategies
        combined_scores = {}
        strategies_used = []

        for candidate in candidates:
            combined_scores.update(candidate.scores)
            strategies_used.append(candidate.matching_strategy)

        # Calculate combined confidence (weighted average)
        total_confidence = sum(c.confidence for c in candidates)
        avg_confidence = total_confidence / len(candidates)

        # Use max confidence with a boost from multiple strategies
        multi_strategy_boost = min(0.1, (len(candidates) - 1) * 0.03)
        final_confidence = min(1.0, best.confidence + multi_strategy_boost)

        # Combine rationales
        combined_rationale = (
            f"Multiple strategies agree ({len(candidates)} strategies): "
            f"{', '.join(set(strategies_used))}. "
            f"Primary rationale: {best.rationale}"
        )

        # Create merged mapping
        merged = FieldMapping(
            source_column=best.source_column,
            target_model=best.target_model,
            target_field=best.target_field,
            confidence=final_confidence,
            scores=combined_scores,
            rationale=combined_rationale,
            matching_strategy=f"Combined[{', '.join(strategies_used)}]",
            alternatives=[],
            transformations=best.transformations,
            mapping_type=best.mapping_type,
            lambda_function=best.lambda_function,
            lambda_dependencies=best.lambda_dependencies,
            data_type=best.data_type,
        )

        return merged

    def _apply_model_priority(
        self,
        candidates: List[FieldMapping],
        candidate_models: Optional[Set[str]],
        column_profile: ColumnProfile
    ) -> List[FieldMapping]:
        """
        Apply model priority based on detected context.

        Boost confidence for models in the detected context and penalize unlikely models.

        Args:
            candidates: List of FieldMapping objects
            candidate_models: Set of models detected from context
            column_profile: Column profile for additional context

        Returns:
            List of FieldMapping objects with adjusted confidence
        """
        # Parse compound names to get entity hints
        from .compound_name_parser import CompoundNameParser
        parser = CompoundNameParser()
        hints = parser.extract_all_hints(column_profile.column_name)

        prioritized = []
        for candidate in candidates:
            model = candidate.target_model

            # STRONG boost if compound name suggests this specific model
            if hints["is_compound"] and hints["suggested_model"]:
                if model == hints["suggested_model"]:
                    # Very strong boost for matching compound name suggestion
                    candidate.confidence = min(1.0, candidate.confidence * 2.0)
                    candidate.rationale += f" [STRONG BOOST: Compound name '{hints['entity_prefix']}' suggests this model]"
                elif model != hints["suggested_model"]:
                    # Penalize models that don't match compound name suggestion
                    candidate.confidence *= 0.3
                    candidate.rationale += f" [PENALIZED: Compound name suggests {hints['suggested_model']}, not {model}]"

            # Apply confidence adjustments based on model context
            elif candidate_models:
                if model in candidate_models:
                    # Boost confidence for models in detected context
                    candidate.confidence = min(1.0, candidate.confidence * 1.5)
                    candidate.rationale += " [Boosted: Model in detected context]"
                else:
                    # Penalize models NOT in detected context
                    candidate.confidence *= 0.5
                    candidate.rationale += " [Penalized: Model outside detected context]"

            # Additional specific penalties
            if model.startswith("hr.") and "employee" not in column_profile.column_name.lower():
                # Strong penalty for HR models unless column explicitly mentions employee
                candidate.confidence *= 0.2
                candidate.rationale += " [Strongly penalized: HR model outside HR context]"
            elif model.startswith("stock.") and not any(
                word in column_profile.column_name.lower()
                for word in ["stock", "inventory", "warehouse"]
            ):
                # Penalize stock models unless column mentions inventory
                candidate.confidence *= 0.4
                candidate.rationale += " [Penalized: Stock model outside inventory context]"
            elif model.startswith("project.") and not any(
                word in column_profile.column_name.lower()
                for word in ["project", "task", "milestone"]
            ):
                # Penalize project models unless relevant
                candidate.confidence *= 0.4
                candidate.rationale += " [Penalized: Project model outside project context]"

            prioritized.append(candidate)

        return prioritized

    def _rank_candidates(
        self,
        candidates: List[FieldMapping]
    ) -> List[FieldMapping]:
        """
        Rank candidates by confidence score.

        Args:
            candidates: List of FieldMapping objects

        Returns:
            Sorted list of FieldMapping objects (highest confidence first)
        """
        return sorted(
            candidates,
            key=lambda m: m.confidence,
            reverse=True
        )

    def _detect_candidate_models(
        self,
        column_profiles: List[ColumnProfile]
    ) -> Set[str]:
        """
        Detect candidate models using intelligent business context analysis.

        This replaces the naive voting system with context-aware model detection
        that understands business domains and data semantics.

        Args:
            column_profiles: List of ColumnProfile objects

        Returns:
            Set of likely model names
        """
        logger.info("Detecting candidate models using business context analysis")

        # 1. Use BusinessContextAnalyzer to detect domain and get recommended models
        recommended_models = self.business_analyzer.get_recommended_models(
            column_profiles, max_models=10
        )

        # 2. Get user-selected modules if available (would need to be passed in)
        # This is a placeholder - in real usage, this would come from dataset.selected_modules
        selected_module_models = set()

        # 3. Use CellDataAnalyzer to get field hints from actual values
        value_based_models = set()
        for col_profile in column_profiles[:10]:  # Analyze first 10 columns
            suggestions = self.cell_analyzer.suggest_field_mappings(col_profile)
            for suggestion in suggestions:
                if "model" in suggestion:
                    value_based_models.add(suggestion["model"])

        # 4. Combine all sources with priority
        candidate_models = set(recommended_models)

        # Add value-based models
        candidate_models.update(value_based_models)

        # If we have selected modules, filter to only those
        if selected_module_models:
            candidate_models = candidate_models & selected_module_models

        # Fallback: If no models detected, use a sensible default set
        if not candidate_models:
            logger.warning("No candidate models detected, using default set")
            candidate_models = {
                "res.partner",  # Most common
                "product.product",
                "sale.order",
                "account.move"
            }

        # DON'T expand to related models - this causes too many false matches
        # Keep only the models directly detected from context
        logger.info(f"Detected {len(candidate_models)} candidate models from context analysis")

        return candidate_models

    def get_strategy_by_name(self, name: str) -> Optional[BaseStrategy]:
        """
        Get a strategy by its name.

        Args:
            name: Name of the strategy

        Returns:
            BaseStrategy if found, None otherwise
        """
        for strategy in self.strategies:
            if strategy.name == name:
                return strategy
        return None

    def enable_strategy(self, name: str) -> bool:
        """
        Enable a strategy.

        Args:
            name: Name of the strategy

        Returns:
            True if enabled, False if not found
        """
        strategy = self.get_strategy_by_name(name)
        if strategy:
            strategy.weight = 1.0
            logger.info(f"Enabled strategy: {name}")
            return True
        return False

    def disable_strategy(self, name: str) -> bool:
        """
        Disable a strategy.

        Args:
            name: Name of the strategy

        Returns:
            True if disabled, False if not found
        """
        strategy = self.get_strategy_by_name(name)
        if strategy:
            strategy.weight = 0.0
            logger.info(f"Disabled strategy: {name}")
            return True
        return False

    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about the pipeline.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_strategies": len(self.strategies),
            "enabled_strategies": sum(1 for s in self.strategies if s.weight > 0),
            "models_in_kb": len(self.knowledge_base.models),
            "fields_in_kb": len(self.knowledge_base.fields),
        }
