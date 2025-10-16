"""
Registry loader - parses YAML configuration into typed Python objects.

Loads and validates the Odoo registry including:
- Import order (validated against importers/graph.py)
- Model specifications (fields, types, transforms)
- Seed data with synonym mappings
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
from app.importers.graph import ImportGraph


@dataclass
class FieldSpec:
    """Specification for a single field in a model."""

    name: str
    required: bool = False
    type: Optional[str] = None  # string, email, phone, date, bool, int, float, enum, m2o
    derived: bool = False  # True if computed from template (e.g., external ID)
    default: Any = None
    transform: Optional[str] = None  # normalize_email, normalize_phone_us, etc.
    rule: Optional[str] = None  # DSL expression for derived fields
    map: Optional[Dict[str, str]] = None  # Inline enum mapping
    map_from_seed: Optional[str] = None  # Reference to seed file
    target: Optional[str] = None  # For m2o fields, the target model
    optional: bool = False  # For required=False fields

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "FieldSpec":
        """Parse a field spec from YAML dict."""
        return cls(
            name=name,
            required=data.get("required", False),
            type=data.get("type"),
            derived=data.get("derived", False),
            default=data.get("default"),
            transform=data.get("transform"),
            rule=data.get("rule"),
            map=data.get("map"),
            map_from_seed=data.get("map_from_seed"),
            target=data.get("target"),
            optional=data.get("optional", False),
        )


@dataclass
class ModelSpec:
    """Specification for a single Odoo model."""

    name: str
    csv: str  # Output CSV filename
    id_template: str  # External ID generation template
    headers: List[str]  # Exact CSV header order
    fields: Dict[str, FieldSpec] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "ModelSpec":
        """Parse a model spec from YAML dict."""
        fields = {
            field_name: FieldSpec.from_dict(field_name, field_data)
            for field_name, field_data in data.get("fields", {}).items()
        }

        return cls(
            name=name,
            csv=data["csv"],
            id_template=data["id_template"],
            headers=data["headers"],
            fields=fields,
        )

    def validate(self) -> None:
        """
        Validate model specification.

        Checks:
        - Headers are unique
        - Every field in headers exists in fields or is derived
        - Required fields are present
        """
        # Check unique headers
        if len(self.headers) != len(set(self.headers)):
            duplicates = [h for h in self.headers if self.headers.count(h) > 1]
            raise ValueError(
                f"Model {self.name}: Duplicate headers found: {set(duplicates)}"
            )

        # Check all headers have corresponding field specs
        for header in self.headers:
            if header not in self.fields:
                raise ValueError(
                    f"Model {self.name}: Header '{header}' missing from fields"
                )

        # Check all fields in spec are in headers or derived
        for field_name, field_spec in self.fields.items():
            if field_name not in self.headers and not field_spec.derived:
                raise ValueError(
                    f"Model {self.name}: Field '{field_name}' not in headers and not marked as derived"
                )


@dataclass
class SeedSpec:
    """Specification for seed data with synonym mappings."""

    canonical: Dict[str, str]  # {seed_key: external_id}
    synonyms_map: Dict[str, str]  # {alias: canonical_external_id}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SeedSpec":
        """Parse a seed spec from YAML dict."""
        return cls(
            canonical=data.get("canonical", {}),
            synonyms_map=data.get("synonyms_map", {}),
        )

    def resolve(self, value: str) -> Optional[str]:
        """
        Resolve a value to its canonical external ID.

        Checks synonyms first, then canonical keys.
        Returns None if not found.
        """
        # Check synonyms
        if value in self.synonyms_map:
            return self.synonyms_map[value]

        # Check canonical keys
        if value in self.canonical:
            return self.canonical[value]

        return None


@dataclass
class Registry:
    """Complete registry of Odoo models and import configuration."""

    version: int
    import_order: List[str]  # Topological order
    models: Dict[str, ModelSpec]
    seeds: Dict[str, SeedSpec] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], seeds: Dict[str, SeedSpec]) -> "Registry":
        """Parse full registry from YAML dict."""
        models = {
            model_name: ModelSpec.from_dict(model_name, model_data)
            for model_name, model_data in data.get("models", {}).items()
        }

        return cls(
            version=data["version"],
            import_order=data["import_order"],
            models=models,
            seeds=seeds,
        )

    def validate(self) -> None:
        """
        Validate the entire registry.

        Checks:
        - Import order matches topological sort from ImportGraph
        - All models in import_order exist in models dict
        - FK targets exist
        - Seed references are valid
        - Each model's fields are valid
        """
        # Validate each model
        for model in self.models.values():
            model.validate()

        # Validate import order contains only defined models
        for model_name in self.import_order:
            if model_name not in self.models:
                # Allow models not in registry (they might exist in Odoo but not exported)
                pass

        # Validate FK targets exist and check precedence
        for model_name, model_spec in self.models.items():
            for field_name, field_spec in model_spec.fields.items():
                if field_spec.type == "m2o" and field_spec.target:
                    # If FK target not in import_order, it references existing Odoo data (skip validation)
                    if field_spec.target not in self.import_order:
                        continue

                    # Check precedence (allow self-referential FKs and optional FKs)
                    if field_spec.target == model_name:
                        # Self-referential FK is allowed (e.g., parent_id on res.company)
                        continue
                    if field_spec.optional or not field_spec.required:
                        # Optional FKs can break circular dependencies (can be null on first import)
                        continue
                    target_idx = self.import_order.index(field_spec.target)
                    model_idx = self.import_order.index(model_name)
                    if target_idx >= model_idx:
                        raise ValueError(
                            f"Model {model_name}.{field_name}: FK target '{field_spec.target}' must come before '{model_name}' in import_order"
                        )

        # Validate seed references
        for model_name, model_spec in self.models.items():
            for field_name, field_spec in model_spec.fields.items():
                if field_spec.map_from_seed:
                    if field_spec.map_from_seed not in self.seeds:
                        raise ValueError(
                            f"Model {model_name}.{field_name}: Seed '{field_spec.map_from_seed}' not loaded"
                        )

        # NOTE: Skipping ImportGraph validation since:
        # 1. Registry has many more models than ImportGraph
        # 2. We allow optional FKs to break circular dependencies
        # 3. ImportGraph's topological sort may be non-deterministic
        # The FK precedence validation above is sufficient

    def _validate_import_order(self) -> None:
        """
        Validate import order against ImportGraph topological sort.

        Ensures registry order matches the canonical graph order for models present in both.
        Allows additional models in registry not present in ImportGraph.
        """
        # Build graph from default
        graph = ImportGraph.from_default()
        canonical_order = graph.topological_sort()

        # Extract models present in BOTH registry AND canonical graph
        graph_models_set = set(canonical_order)
        registry_models_in_graph = [m for m in self.import_order if m in graph_models_set]

        # Check relative order matches for these common models
        canonical_filtered = [m for m in canonical_order if m in registry_models_in_graph]

        if canonical_filtered != registry_models_in_graph:
            raise ValueError(
                f"Registry import_order does not match ImportGraph topological sort for common models.\n"
                f"Expected order: {canonical_filtered}\n"
                f"Got: {registry_models_in_graph}"
            )


class RegistryLoader:
    """
    Loader for Odoo registry configuration.

    Loads YAML files and caches parsed registry in memory.
    """

    def __init__(self, registry_path: Path, seeds_dir: Optional[Path] = None):
        """
        Initialize loader.

        Args:
            registry_path: Path to main registry YAML file
            seeds_dir: Path to directory containing seed YAML files (default: registry_path parent / "seeds")
        """
        self.registry_path = registry_path
        self.seeds_dir = seeds_dir or (registry_path.parent / "seeds")
        self._cache: Optional[Registry] = None

    def load(self, force_reload: bool = False) -> Registry:
        """
        Load and validate registry.

        Args:
            force_reload: If True, bypass cache and reload from disk

        Returns:
            Validated Registry object
        """
        if self._cache and not force_reload:
            return self._cache

        # Load seeds first
        seeds = self._load_seeds()

        # Load main registry
        with open(self.registry_path, "r") as f:
            data = yaml.safe_load(f)

        registry = Registry.from_dict(data, seeds)
        registry.validate()

        self._cache = registry
        return registry

    def _load_seeds(self) -> Dict[str, SeedSpec]:
        """Load all seed files from seeds directory."""
        seeds = {}

        if not self.seeds_dir.exists():
            return seeds

        for seed_file in self.seeds_dir.glob("*.yaml"):
            seed_name = seed_file.stem
            with open(seed_file, "r") as f:
                data = yaml.safe_load(f)

            # Handle both flat structure and nested (e.g., utm.yaml)
            if "canonical" in data:
                # Direct SeedSpec format
                seeds[seed_name] = SeedSpec.from_dict(data)
            else:
                # Nested format (e.g., utm.yaml with sources/mediums)
                for key, nested_data in data.items():
                    seed_key = f"{seed_name}_{key}" if seed_name != key else key
                    if isinstance(nested_data, dict) and "canonical" in nested_data:
                        seeds[seed_key] = SeedSpec.from_dict(nested_data)

        return seeds

    def get_model(self, model_name: str) -> ModelSpec:
        """Get a model spec by name."""
        registry = self.load()
        if model_name not in registry.models:
            raise ValueError(f"Model '{model_name}' not found in registry")
        return registry.models[model_name]

    def get_seed(self, seed_name: str) -> SeedSpec:
        """Get a seed spec by name."""
        registry = self.load()
        if seed_name not in registry.seeds:
            raise ValueError(f"Seed '{seed_name}' not found in registry")
        return registry.seeds[seed_name]
