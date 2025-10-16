"""
Import order validation.

Uses existing importers/graph.py as the canonical precedence validator.
Fail fast on mismatch.
"""
from typing import List
from app.importers.graph import ImportGraph


def validate_import_order(registry_order: List[str], models_in_registry: List[str]) -> None:
    """
    Validate that registry import order matches ImportGraph topological sort.

    Args:
        registry_order: Import order from registry
        models_in_registry: List of models actually defined in registry

    Raises:
        ValueError: If order doesn't match canonical graph order
    """
    # Build graph from default
    graph = ImportGraph.from_default()
    canonical_order = graph.topological_sort()

    # Filter to models present in registry
    registry_models = [m for m in registry_order if m in models_in_registry]
    canonical_filtered = [m for m in canonical_order if m in registry_models]

    if canonical_filtered != registry_models:
        raise ValueError(
            f"Registry import_order does not match ImportGraph topological sort.\n"
            f"Expected (from ImportGraph): {canonical_filtered}\n"
            f"Got (from registry): {registry_models}\n"
            f"Please update registry/odoo.yaml to match canonical order."
        )


def get_import_order(registry_order: List[str], models_in_registry: List[str]) -> List[str]:
    """
    Get validated import order for models.

    Args:
        registry_order: Import order from registry
        models_in_registry: List of models actually defined in registry

    Returns:
        Validated import order (filtered to models in registry)

    Raises:
        ValueError: If order doesn't match canonical precedence
    """
    validate_import_order(registry_order, models_in_registry)
    return [m for m in registry_order if m in models_in_registry]
