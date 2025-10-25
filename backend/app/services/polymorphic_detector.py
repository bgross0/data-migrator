"""
Polymorphic Relationship Detector.

Detects and resolves polymorphic foreign keys (e.g., mail.activity, mail.message)
where a record can link to multiple parent entity types.

Implements hybrid detection + confirmation strategy:
1. Detect polymorphic patterns in column names/values
2. Infer anchor model with confidence scoring
3. Require user confirmation for ambiguous cases (confidence < threshold)
"""
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import re
from collections import Counter


@dataclass
class PolymorphicSignature:
    """
    Detected polymorphic relationship signature.

    Attributes:
        model_col: Column containing model/type name (e.g., "related_to_type", "res_model")
        id_col: Column containing foreign key ID (e.g., "related_to_id", "res_id")
        confidence: Confidence score (0.0-1.0)
        detected_models: Distinct model names found in model_col
        sample_values: Sample (model, id) pairs for user review
        inference: Inferred canonical anchor model ('fact_lead', 'dim_partner', etc.)
    """
    model_col: str
    id_col: str
    confidence: float
    detected_models: List[str]
    sample_values: List[Tuple[str, Any]]
    inference: Optional[str] = None
    rationale: Optional[str] = None


@dataclass
class AnchorInference:
    """
    Inferred anchor model with confidence.

    Attributes:
        canonical_model: Canonical table name ('fact_lead', 'dim_partner', etc.)
        odoo_model: Odoo model name ('crm.lead', 'res.partner', etc.)
        confidence: Confidence score (0.0-1.0)
        rationale: Explanation of inference
    """
    canonical_model: str
    odoo_model: str
    confidence: float
    rationale: str


class PolymorphicDetector:
    """
    Detects polymorphic relationships in source data.

    Polymorphic relationships use a (model, id) pair to reference
    different entity types from a single column set.

    Example:
        mail.activity has (res_model='crm.lead', res_id=42)
        mail.message has (model='res.partner', res_id=100)
    """

    # Known polymorphic column name patterns
    MODEL_COL_PATTERNS = [
        r'^res_model$',
        r'^model$',
        r'^related_to_type$',
        r'^parent_type$',
        r'^record_type$',
        r'_model$',
        r'_type$',
    ]

    ID_COL_PATTERNS = [
        r'^res_id$',
        r'^record_id$',
        r'^related_to_id$',
        r'^parent_id$',
        r'_id$',
    ]

    # Odoo model → canonical model mapping
    ODOO_TO_CANONICAL = {
        'crm.lead': 'fact_lead',
        'res.partner': 'dim_partner',
        'sale.order': 'fact_order',
        'project.project': 'fact_project',
        'project.task': 'fact_task',
        'account.move': 'fact_invoice',
    }

    def __init__(self, confidence_threshold: float = 0.75):
        """
        Initialize detector.

        Args:
            confidence_threshold: Minimum confidence for auto-inference (default 0.75)
        """
        self.confidence_threshold = confidence_threshold

    def detect_polymorphic_columns(
        self,
        column_names: List[str],
        sample_data: List[Dict[str, Any]]
    ) -> List[PolymorphicSignature]:
        """
        Detect polymorphic column pairs in dataset.

        Args:
            column_names: List of column names in dataset
            sample_data: Sample rows from dataset (for value analysis)

        Returns:
            List of detected polymorphic signatures
        """
        signatures = []

        # Find potential model columns
        model_cols = self._find_columns_matching_patterns(column_names, self.MODEL_COL_PATTERNS)

        for model_col in model_cols:
            # Find corresponding ID column
            id_col = self._find_paired_id_column(model_col, column_names)

            if not id_col:
                continue

            # Analyze values in model_col to detect distinct models
            detected_models = self._extract_distinct_models(model_col, sample_data)

            # Calculate confidence
            confidence = self._calculate_confidence(model_col, id_col, detected_models, sample_data)

            # Extract sample values
            sample_values = self._extract_sample_values(model_col, id_col, sample_data, limit=10)

            # Infer anchor model
            inference, rationale = self._infer_anchor_model(detected_models, sample_data)

            signature = PolymorphicSignature(
                model_col=model_col,
                id_col=id_col,
                confidence=confidence,
                detected_models=detected_models,
                sample_values=sample_values,
                inference=inference,
                rationale=rationale
            )

            signatures.append(signature)

        return signatures

    def _find_columns_matching_patterns(
        self,
        column_names: List[str],
        patterns: List[str]
    ) -> List[str]:
        """Find columns matching regex patterns."""
        matches = []
        for col in column_names:
            normalized = col.lower().strip()
            for pattern in patterns:
                if re.match(pattern, normalized):
                    matches.append(col)
                    break
        return matches

    def _find_paired_id_column(
        self,
        model_col: str,
        column_names: List[str]
    ) -> Optional[str]:
        """
        Find the ID column paired with model column.

        Heuristics:
        1. If model_col='res_model', look for 'res_id'
        2. If model_col='related_to_type', look for 'related_to_id'
        3. If model_col ends with '_model', look for '_id' with same prefix
        """
        normalized_model = model_col.lower().strip()

        # Direct mappings
        direct_mappings = {
            'res_model': 'res_id',
            'model': 'record_id',
            'parent_type': 'parent_id',
            'related_to_type': 'related_to_id',
        }

        if normalized_model in direct_mappings:
            expected_id = direct_mappings[normalized_model]
            for col in column_names:
                if col.lower().strip() == expected_id:
                    return col

        # Pattern-based: replace _model/_type with _id
        if normalized_model.endswith('_model') or normalized_model.endswith('_type'):
            prefix = normalized_model.rsplit('_', 1)[0]
            expected_id = f"{prefix}_id"
            for col in column_names:
                if col.lower().strip() == expected_id:
                    return col

        # Fallback: find any ID column
        id_cols = self._find_columns_matching_patterns(column_names, self.ID_COL_PATTERNS)
        return id_cols[0] if id_cols else None

    def _extract_distinct_models(
        self,
        model_col: str,
        sample_data: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract distinct model names from model column."""
        models = set()
        for row in sample_data:
            value = row.get(model_col)
            if value and isinstance(value, str):
                models.add(value.strip())
        return sorted(models)

    def _calculate_confidence(
        self,
        model_col: str,
        id_col: str,
        detected_models: List[str],
        sample_data: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate confidence score for polymorphic detection.

        Factors:
        - Multiple distinct models found (higher confidence)
        - Model values look like Odoo models (e.g., 'crm.lead', 'res.partner')
        - ID column has numeric values
        - Column names match known patterns strongly
        """
        score = 0.0

        # Factor 1: Multiple distinct models (0-0.3)
        if len(detected_models) >= 2:
            score += 0.3
        elif len(detected_models) == 1:
            score += 0.15

        # Factor 2: Models look like Odoo models (0-0.4)
        odoo_like_count = sum(1 for m in detected_models if '.' in m and m.split('.')[0] in ['crm', 'res', 'sale', 'project', 'account', 'mail'])
        if detected_models:
            odoo_like_ratio = odoo_like_count / len(detected_models)
            score += 0.4 * odoo_like_ratio

        # Factor 3: ID column has numeric values (0-0.2)
        id_numeric_count = sum(1 for row in sample_data if isinstance(row.get(id_col), (int, float)))
        if sample_data:
            id_numeric_ratio = id_numeric_count / len(sample_data)
            score += 0.2 * id_numeric_ratio

        # Factor 4: Column names match strong patterns (0-0.1)
        if model_col.lower() in ['res_model', 'model']:
            score += 0.05
        if id_col.lower() in ['res_id', 'record_id']:
            score += 0.05

        return min(score, 1.0)

    def _extract_sample_values(
        self,
        model_col: str,
        id_col: str,
        sample_data: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Tuple[str, Any]]:
        """Extract sample (model, id) pairs."""
        samples = []
        for row in sample_data[:limit]:
            model_val = row.get(model_col)
            id_val = row.get(id_col)
            if model_val and id_val:
                samples.append((str(model_val), id_val))
        return samples

    def _infer_anchor_model(
        self,
        detected_models: List[str],
        sample_data: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Infer the canonical anchor model for this polymorphic relationship.

        If multiple models detected, choose the most common one.
        If single model, use that.

        Returns:
            (canonical_model, rationale) tuple
        """
        if not detected_models:
            return None, "No models detected"

        # If single model, use it
        if len(detected_models) == 1:
            odoo_model = detected_models[0]
            canonical = self.ODOO_TO_CANONICAL.get(odoo_model)
            if canonical:
                return canonical, f"Single model detected: {odoo_model} → {canonical}"
            else:
                return None, f"Unknown Odoo model: {odoo_model}"

        # Multiple models: choose most common
        model_counts = Counter()
        for row in sample_data:
            for model in detected_models:
                # Assuming model column is in the row
                for key, val in row.items():
                    if val == model:
                        model_counts[model] += 1
                        break

        if not model_counts:
            return None, "Could not determine most common model"

        most_common_model, count = model_counts.most_common(1)[0]
        canonical = self.ODOO_TO_CANONICAL.get(most_common_model)

        if canonical:
            return canonical, f"Most common model: {most_common_model} ({count} occurrences) → {canonical}"
        else:
            return None, f"Unknown Odoo model: {most_common_model}"

    def requires_confirmation(self, signature: PolymorphicSignature) -> bool:
        """
        Check if polymorphic signature requires user confirmation.

        Requires confirmation if:
        - Confidence < threshold
        - No inference could be made
        - Multiple models detected but unclear which to use
        """
        if signature.confidence < self.confidence_threshold:
            return True
        if not signature.inference:
            return True
        if len(signature.detected_models) > 2:
            return True
        return False

    def generate_confirmation_prompt(self, signature: PolymorphicSignature) -> Dict[str, Any]:
        """
        Generate user confirmation prompt for ambiguous polymorphic relationship.

        Returns:
            Dict with prompt details for UI
        """
        return {
            "type": "polymorphic_confirmation",
            "model_column": signature.model_col,
            "id_column": signature.id_col,
            "detected_models": signature.detected_models,
            "sample_values": signature.sample_values,
            "confidence": signature.confidence,
            "inference": signature.inference,
            "rationale": signature.rationale,
            "message": (
                f"Detected polymorphic relationship using columns ({signature.model_col}, {signature.id_col}). "
                f"Found {len(signature.detected_models)} distinct model types. "
                f"Confidence: {signature.confidence:.2%}. "
                f"Please confirm the anchor model."
            ),
            "options": [
                {"label": anchor, "description": f"Map to {anchor}"}
                for anchor in ['fact_lead', 'dim_partner', 'fact_order', 'skip']
            ]
        }


class AnchorInferenceService:
    """
    Infers the canonical anchor model for polymorphic relationships.

    Given a polymorphic reference (res_model, res_id), determines which
    canonical table to link to (fact_lead vs dim_partner, etc.).
    """

    def __init__(self):
        self.odoo_to_canonical = PolymorphicDetector.ODOO_TO_CANONICAL

    def infer_anchor(
        self,
        odoo_model: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AnchorInference:
        """
        Infer canonical anchor model from Odoo model name.

        Args:
            odoo_model: Odoo model name (e.g., 'crm.lead', 'res.partner')
            context: Additional context (e.g., dataset name, column values)

        Returns:
            AnchorInference with canonical model and confidence
        """
        canonical = self.odoo_to_canonical.get(odoo_model)

        if canonical:
            return AnchorInference(
                canonical_model=canonical,
                odoo_model=odoo_model,
                confidence=1.0,
                rationale=f"Direct mapping: {odoo_model} → {canonical}"
            )

        # Fuzzy matching for unknown models
        fuzzy_match = self._fuzzy_match_model(odoo_model)
        if fuzzy_match:
            return AnchorInference(
                canonical_model=fuzzy_match[0],
                odoo_model=odoo_model,
                confidence=fuzzy_match[1],
                rationale=f"Fuzzy match: {odoo_model} → {fuzzy_match[0]} (confidence: {fuzzy_match[1]:.2%})"
            )

        # Unknown model
        return AnchorInference(
            canonical_model='unknown',
            odoo_model=odoo_model,
            confidence=0.0,
            rationale=f"Unknown Odoo model: {odoo_model}"
        )

    def _fuzzy_match_model(self, odoo_model: str) -> Optional[Tuple[str, float]]:
        """
        Fuzzy match unknown Odoo model to known canonical models.

        Heuristics:
        - If model contains 'lead' or 'opportunity' → fact_lead
        - If model contains 'partner' or 'contact' → dim_partner
        - If model contains 'order' or 'sale' → fact_order
        """
        normalized = odoo_model.lower()

        if 'lead' in normalized or 'opportunity' in normalized:
            return ('fact_lead', 0.7)
        if 'partner' in normalized or 'contact' in normalized:
            return ('dim_partner', 0.7)
        if 'order' in normalized or 'sale' in normalized:
            return ('fact_order', 0.7)
        if 'project' in normalized:
            return ('fact_project', 0.6)
        if 'task' in normalized:
            return ('fact_task', 0.6)

        return None
