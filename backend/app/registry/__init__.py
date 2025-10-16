"""
Registry module for loading and caching Odoo model specifications.
"""
from app.registry.loader import RegistryLoader, Registry, ModelSpec, FieldSpec

__all__ = ["RegistryLoader", "Registry", "ModelSpec", "FieldSpec"]
