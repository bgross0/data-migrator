"""
OdooKnowledgeBase: Central repository for Odoo model information.

This class serves as the single source of truth for all Odoo model definitions,
field information, constraints, and relationships. It provides fast lookups through
multiple indexing strategies.
"""
from typing import Dict, List, Optional, Tuple, Set, Any
from pathlib import Path
import networkx as nx
import pygtrie

from .data_structures import (
    ModelDefinition,
    FieldDefinition,
    SelectionOption,
    ConstraintDefinition,
    RelationDefinition,
)
from ..config.logging_config import knowledge_base_logger as logger


class OdooKnowledgeBase:
    """
    Central repository for all Odoo model information.

    This class manages:
    - Model definitions and their relationships
    - Field definitions with fast lookup by (model, field) tuples
    - Selection values for selection/many2one fields
    - Database and model constraints
    - Many2many relation tables
    - Relationship graph using NetworkX
    - Multiple indexes for O(1) lookups
    - Trie structures for prefix matching
    """

    def __init__(self, dictionary_path: Optional[Path] = None):
        """
        Initialize the knowledge base.

        Args:
            dictionary_path: Path to the odoo-dictionary directory containing Excel files
        """
        self.dictionary_path = dictionary_path

        # ===========================
        # Core Data Structures
        # ===========================

        # Primary storage: models indexed by name (e.g., "res.partner")
        self.models: Dict[str, ModelDefinition] = {}

        # Primary storage: fields indexed by (model, field_name) tuple
        self.fields: Dict[Tuple[str, str], FieldDefinition] = {}

        # Selection values indexed by (model, field_name) tuple
        self.selections: Dict[Tuple[str, str], List[SelectionOption]] = {}

        # Constraints indexed by model name
        self.constraints: Dict[str, List[ConstraintDefinition]] = {}

        # Relations indexed by relation table name
        self.relations: Dict[str, List[RelationDefinition]] = {}

        # ===========================
        # Graph Structures
        # ===========================

        # Directed graph of model relationships (many2one, one2many, many2many)
        self.model_graph: nx.DiGraph = nx.DiGraph()

        # ===========================
        # Inverted Indexes (O(1) lookup)
        # ===========================

        # Field name -> List[(model, field_name)] for exact name matches
        self.field_name_index: Dict[str, List[Tuple[str, str]]] = {}

        # Field label (lowercase) -> List[(model, field_name)] for label matches
        self.field_label_index: Dict[str, List[Tuple[str, str]]] = {}

        # Selection value (lowercase) -> List[(model, field_name)] for selection matching
        self.selection_value_index: Dict[str, List[Tuple[str, str]]] = {}

        # Field type -> List[(model, field_name)] for type-based filtering
        self.field_type_index: Dict[str, List[Tuple[str, str]]] = {}

        # Related model -> List[(source_model, field_name)] for relationship navigation
        self.related_model_index: Dict[str, List[Tuple[str, str]]] = {}

        # ===========================
        # Trie Structures (Prefix matching)
        # ===========================

        # Trie for field names (supports prefix matching like "cust" -> "customer_id")
        self.field_name_trie: pygtrie.CharTrie = pygtrie.CharTrie()

        # Trie for field labels (supports prefix matching like "Customer" -> "Customer Name")
        self.field_label_trie: pygtrie.CharTrie = pygtrie.CharTrie()

        # ===========================
        # Metadata
        # ===========================

        self.is_loaded: bool = False
        self.load_timestamp: Optional[str] = None
        self.statistics: Dict[str, int] = {
            "total_models": 0,
            "total_fields": 0,
            "total_selections": 0,
            "total_constraints": 0,
            "total_relations": 0,
        }

        logger.info("OdooKnowledgeBase initialized")

    # ===========================
    # Model Operations
    # ===========================

    def add_model(self, model: ModelDefinition) -> None:
        """
        Add a model definition to the knowledge base.

        Args:
            model: ModelDefinition to add
        """
        self.models[model.name] = model
        logger.debug(f"Added model: {model.name}")

    def get_model(self, model_name: str) -> Optional[ModelDefinition]:
        """
        Retrieve a model definition by name.

        Args:
            model_name: Technical name of the model (e.g., "res.partner")

        Returns:
            ModelDefinition if found, None otherwise
        """
        return self.models.get(model_name)

    def get_all_models(self) -> List[ModelDefinition]:
        """
        Get all model definitions.

        Returns:
            List of all ModelDefinition objects
        """
        return list(self.models.values())

    def model_exists(self, model_name: str) -> bool:
        """
        Check if a model exists in the knowledge base.

        Args:
            model_name: Technical name of the model

        Returns:
            True if model exists, False otherwise
        """
        return model_name in self.models

    # ===========================
    # Field Operations
    # ===========================

    def add_field(self, field: FieldDefinition) -> None:
        """
        Add a field definition to the knowledge base.

        Args:
            field: FieldDefinition to add
        """
        key = (field.model, field.name)
        self.fields[key] = field
        logger.debug(f"Added field: {field.model}.{field.name}")

    def get_field(self, model_name: str, field_name: str) -> Optional[FieldDefinition]:
        """
        Retrieve a field definition by model and field name.

        Args:
            model_name: Technical name of the model
            field_name: Technical name of the field

        Returns:
            FieldDefinition if found, None otherwise
        """
        return self.fields.get((model_name, field_name))

    def get_model_fields(self, model_name: str) -> List[FieldDefinition]:
        """
        Get all fields for a specific model.

        Args:
            model_name: Technical name of the model

        Returns:
            List of FieldDefinition objects for the model
        """
        return [
            field for (model, field_name), field in self.fields.items()
            if model == model_name
        ]

    def field_exists(self, model_name: str, field_name: str) -> bool:
        """
        Check if a field exists in the knowledge base.

        Args:
            model_name: Technical name of the model
            field_name: Technical name of the field

        Returns:
            True if field exists, False otherwise
        """
        return (model_name, field_name) in self.fields

    # ===========================
    # Selection Operations
    # ===========================

    def add_selection(self, model_name: str, field_name: str,
                      selection: SelectionOption) -> None:
        """
        Add a selection option to a field.

        Args:
            model_name: Technical name of the model
            field_name: Technical name of the field
            selection: SelectionOption to add
        """
        key = (model_name, field_name)
        if key not in self.selections:
            self.selections[key] = []
        self.selections[key].append(selection)
        logger.debug(f"Added selection '{selection.value}' to {model_name}.{field_name}")

    def get_selections(self, model_name: str, field_name: str) -> List[SelectionOption]:
        """
        Get all selection options for a field.

        Args:
            model_name: Technical name of the model
            field_name: Technical name of the field

        Returns:
            List of SelectionOption objects
        """
        return self.selections.get((model_name, field_name), [])

    def get_selection_values(self, model_name: str, field_name: str) -> List[str]:
        """
        Get selection values (internal values) for a field.

        Args:
            model_name: Technical name of the model
            field_name: Technical name of the field

        Returns:
            List of selection values
        """
        selections = self.get_selections(model_name, field_name)
        return [sel.value for sel in selections]

    # ===========================
    # Constraint Operations
    # ===========================

    def add_constraint(self, constraint: ConstraintDefinition) -> None:
        """
        Add a constraint definition.

        Args:
            constraint: ConstraintDefinition to add
        """
        if constraint.model not in self.constraints:
            self.constraints[constraint.model] = []
        self.constraints[constraint.model].append(constraint)
        logger.debug(f"Added constraint '{constraint.name}' to {constraint.model}")

    def get_constraints(self, model_name: str) -> List[ConstraintDefinition]:
        """
        Get all constraints for a model.

        Args:
            model_name: Technical name of the model

        Returns:
            List of ConstraintDefinition objects
        """
        return self.constraints.get(model_name, [])

    def get_unique_constraints(self, model_name: str) -> List[ConstraintDefinition]:
        """
        Get unique constraints for a model.

        Args:
            model_name: Technical name of the model

        Returns:
            List of unique ConstraintDefinition objects
        """
        constraints = self.get_constraints(model_name)
        return [c for c in constraints if c.type == 'u']

    def get_required_fields(self, model_name: str) -> List[str]:
        """
        Get required field names for a model based on constraints.

        Args:
            model_name: Technical name of the model

        Returns:
            List of required field names
        """
        # This will be populated during loading when we parse constraints
        # For now, also check the is_required attribute on fields
        model_fields = self.get_model_fields(model_name)
        return [field.name for field in model_fields if field.is_required]

    # ===========================
    # Relation Operations
    # ===========================

    def add_relation(self, relation: RelationDefinition) -> None:
        """
        Add a many2many relation definition.

        Args:
            relation: RelationDefinition to add
        """
        if relation.name not in self.relations:
            self.relations[relation.name] = []
        self.relations[relation.name].append(relation)
        logger.debug(f"Added relation '{relation.name}'")

    def get_relation(self, relation_name: str) -> List[RelationDefinition]:
        """
        Get relation definitions by relation table name.

        Args:
            relation_name: Name of the relation table

        Returns:
            List of RelationDefinition objects
        """
        return self.relations.get(relation_name, [])

    # ===========================
    # Graph Operations
    # ===========================

    def build_model_graph(self) -> None:
        """
        Build the NetworkX graph representing model relationships.

        This creates a directed graph where:
        - Nodes are models
        - Edges represent relationships (many2one, one2many, many2many)
        - Edge attributes include field_name, field_type, and cardinality
        """
        logger.info("Building model relationship graph...")

        # Add all models as nodes
        for model_name, model in self.models.items():
            self.model_graph.add_node(model_name, model=model)

        # Add edges based on field relationships
        for (model_name, field_name), field in self.fields.items():
            if field.related_model and field.related_model in self.models:
                # Add edge from source model to related model
                self.model_graph.add_edge(
                    model_name,
                    field.related_model,
                    field_name=field_name,
                    field_type=field.field_type,
                    label=field.label,
                )
                logger.debug(
                    f"Added edge: {model_name} -> {field.related_model} "
                    f"(via {field_name})"
                )

        logger.info(
            f"Graph built: {self.model_graph.number_of_nodes()} nodes, "
            f"{self.model_graph.number_of_edges()} edges"
        )

    def get_related_models(self, model_name: str, max_depth: int = 1) -> Set[str]:
        """
        Get models related to a given model within max_depth steps.

        Args:
            model_name: Starting model name
            max_depth: Maximum depth to traverse (1 = direct neighbors only)

        Returns:
            Set of related model names
        """
        if not self.model_graph.has_node(model_name):
            return set()

        related = set()

        # BFS traversal up to max_depth
        current_level = {model_name}
        for _ in range(max_depth):
            next_level = set()
            for node in current_level:
                # Get both successors (outgoing edges) and predecessors (incoming edges)
                neighbors = set(self.model_graph.successors(node)) | \
                           set(self.model_graph.predecessors(node))
                next_level.update(neighbors)
                related.update(neighbors)
            current_level = next_level

        return related

    def get_path_between_models(self, source_model: str,
                                target_model: str) -> Optional[List[str]]:
        """
        Find the shortest path between two models in the relationship graph.

        Args:
            source_model: Starting model name
            target_model: Target model name

        Returns:
            List of model names forming the path, or None if no path exists
        """
        try:
            # Use undirected graph for path finding (relationships work both ways)
            undirected = self.model_graph.to_undirected()
            return nx.shortest_path(undirected, source_model, target_model)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    # ===========================
    # Index Operations
    # ===========================

    def build_indexes(self) -> None:
        """
        Build all inverted indexes and trie structures for fast lookups.

        This should be called after all data is loaded.
        """
        logger.info("Building inverted indexes and tries...")

        for (model_name, field_name), field in self.fields.items():
            key = (model_name, field_name)

            # Index by field name
            if field.name not in self.field_name_index:
                self.field_name_index[field.name] = []
            self.field_name_index[field.name].append(key)

            # Index by field label (lowercase)
            label_lower = field.label.lower()
            if label_lower not in self.field_label_index:
                self.field_label_index[label_lower] = []
            self.field_label_index[label_lower].append(key)

            # Index by field type
            if field.field_type not in self.field_type_index:
                self.field_type_index[field.field_type] = []
            self.field_type_index[field.field_type].append(key)

            # Index by related model
            if field.related_model:
                if field.related_model not in self.related_model_index:
                    self.related_model_index[field.related_model] = []
                self.related_model_index[field.related_model].append(key)

            # Add to field name trie
            self.field_name_trie[field.name] = key

            # Add to field label trie (lowercase)
            self.field_label_trie[label_lower] = key

        # Index selection values
        for (model_name, field_name), selections in self.selections.items():
            key = (model_name, field_name)
            for selection in selections:
                value_lower = selection.value.lower()
                if value_lower not in self.selection_value_index:
                    self.selection_value_index[value_lower] = []
                self.selection_value_index[value_lower].append(key)

        logger.info(
            f"Indexes built: {len(self.field_name_index)} field names, "
            f"{len(self.field_label_index)} labels, "
            f"{len(self.selection_value_index)} selection values"
        )

    def lookup_by_field_name(self, field_name: str) -> List[Tuple[str, str]]:
        """
        Lookup fields by exact field name.

        Args:
            field_name: Technical field name to search for

        Returns:
            List of (model_name, field_name) tuples
        """
        return self.field_name_index.get(field_name, [])

    def lookup_by_label(self, label: str) -> List[Tuple[str, str]]:
        """
        Lookup fields by exact label (case-insensitive).

        Args:
            label: Field label to search for

        Returns:
            List of (model_name, field_name) tuples
        """
        return self.field_label_index.get(label.lower(), [])

    def lookup_by_selection_value(self, value: str) -> List[Tuple[str, str]]:
        """
        Lookup fields by selection value (case-insensitive).

        Args:
            value: Selection value to search for

        Returns:
            List of (model_name, field_name) tuples that have this selection value
        """
        return self.selection_value_index.get(value.lower(), [])

    def lookup_by_type(self, field_type: str) -> List[Tuple[str, str]]:
        """
        Lookup fields by field type.

        Args:
            field_type: Field type to search for (e.g., "char", "many2one")

        Returns:
            List of (model_name, field_name) tuples
        """
        return self.field_type_index.get(field_type, [])

    def prefix_match_field_name(self, prefix: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        Find fields whose names start with the given prefix.

        Args:
            prefix: Prefix to match
            limit: Maximum number of results to return

        Returns:
            List of (model_name, field_name) tuples
        """
        results = []
        try:
            for key, value in self.field_name_trie.items(prefix=prefix):
                results.append(value)
                if len(results) >= limit:
                    break
        except KeyError:
            # No matches found
            pass
        return results

    def prefix_match_label(self, prefix: str, limit: int = 10) -> List[Tuple[str, str]]:
        """
        Find fields whose labels start with the given prefix (case-insensitive).

        Args:
            prefix: Prefix to match
            limit: Maximum number of results to return

        Returns:
            List of (model_name, field_name) tuples
        """
        results = []
        try:
            for key, value in self.field_label_trie.items(prefix=prefix.lower()):
                results.append(value)
                if len(results) >= limit:
                    break
        except KeyError:
            # No matches found
            pass
        return results

    # ===========================
    # Statistics & Utilities
    # ===========================

    def update_statistics(self) -> None:
        """
        Update internal statistics about the knowledge base.
        """
        self.statistics["total_models"] = len(self.models)
        self.statistics["total_fields"] = len(self.fields)
        self.statistics["total_selections"] = sum(
            len(sels) for sels in self.selections.values()
        )
        self.statistics["total_constraints"] = sum(
            len(cons) for cons in self.constraints.values()
        )
        self.statistics["total_relations"] = len(self.relations)

        logger.info(f"Statistics updated: {self.statistics}")

    def get_statistics(self) -> Dict[str, int]:
        """
        Get current statistics about the knowledge base.

        Returns:
            Dictionary of statistics
        """
        return self.statistics.copy()

    def validate(self) -> bool:
        """
        Validate the integrity of the knowledge base.

        Returns:
            True if valid, False if errors detected
        """
        logger.info("Validating knowledge base integrity...")
        valid = True

        # Check that all field models exist
        for (model_name, field_name), field in self.fields.items():
            if model_name not in self.models:
                logger.error(f"Field {model_name}.{field_name} references non-existent model")
                valid = False

        # Check that all related models exist
        for (model_name, field_name), field in self.fields.items():
            if field.related_model and field.related_model not in self.models:
                logger.warning(
                    f"Field {model_name}.{field_name} references non-existent "
                    f"related model: {field.related_model}"
                )

        # Check that selection fields have selections
        for (model_name, field_name), field in self.fields.items():
            if field.field_type == "selection":
                if not self.get_selections(model_name, field_name):
                    logger.warning(
                        f"Selection field {model_name}.{field_name} has no selection values"
                    )

        logger.info(f"Validation complete: {'PASSED' if valid else 'FAILED'}")
        return valid

    # ===========================
    # Loading from Dictionary
    # ===========================

    def load_from_dictionary(self, force_reload: bool = False) -> None:
        """
        Load the knowledge base from Odoo dictionary Excel files.

        This is the main entry point for populating the knowledge base.
        It loads all 5 Excel files, builds dictionaries, constructs the graph,
        and creates indexes.

        Args:
            force_reload: If True, reload even if already loaded

        Raises:
            ValueError: If dictionary_path is not set
            FileNotFoundError: If dictionary files are not found
        """
        if self.is_loaded and not force_reload:
            logger.info("Knowledge base already loaded")
            return

        if not self.dictionary_path:
            raise ValueError("dictionary_path must be set to load from dictionary")

        logger.info("Starting knowledge base loading process...")

        # Import here to avoid circular imports
        from ..loaders.excel_loaders import OdooDictionaryLoader
        from datetime import datetime

        # Load all Excel files
        loader = OdooDictionaryLoader(self.dictionary_path)
        data = loader.load_all()

        # Build dictionaries
        self._build_models_dict(data["models"])
        self._build_fields_dict(data["fields"])
        self._build_selections_dict(data["selections"])
        self._build_constraints_dict(data["constraints"])
        self._build_relations_dict(data["relations"])

        # Post-processing: update field selection values
        self._populate_field_selection_values()

        # Build graph structure
        self.build_model_graph()

        # Build indexes for fast lookups
        self.build_indexes()

        # Update statistics
        self.update_statistics()

        # Validate integrity
        self.validate()

        # Mark as loaded
        self.is_loaded = True
        self.load_timestamp = datetime.utcnow().isoformat()

        logger.info(
            f"Knowledge base loaded successfully at {self.load_timestamp}"
        )

    def _build_models_dict(self, models: List[ModelDefinition]) -> None:
        """
        Build the models dictionary from loaded model definitions.

        Args:
            models: List of ModelDefinition objects
        """
        logger.info(f"Building models dictionary from {len(models)} models...")

        for model in models:
            self.add_model(model)

        logger.info(f"Models dictionary built: {len(self.models)} models")

    def _build_fields_dict(self, fields: List[FieldDefinition]) -> None:
        """
        Build the fields dictionary from loaded field definitions.

        Args:
            fields: List of FieldDefinition objects
        """
        logger.info(f"Building fields dictionary from {len(fields)} fields...")

        # Build a model name lookup table (lowercase -> proper case)
        # to handle potential casing mismatches
        model_name_map = {
            model.description.lower(): model.name
            for model in self.models.values()
        }
        model_name_map.update({
            model.name.lower(): model.name
            for model in self.models.values()
        })

        fields_added = 0
        fields_skipped = 0

        for field in fields:
            # Try to map the field's model to a known model
            # The Excel "Model" column contains the description, not the technical name
            model_key = field.model.lower()

            if model_key in model_name_map:
                # Update field with correct model name
                field.model = model_name_map[model_key]
                self.add_field(field)
                fields_added += 1
            else:
                # Log warning but don't fail - some fields may reference modules not installed
                logger.debug(f"Skipping field {field.name} - model '{field.model}' not found")
                fields_skipped += 1

        logger.info(
            f"Fields dictionary built: {fields_added} fields added, "
            f"{fields_skipped} skipped"
        )

    def _build_selections_dict(self, selections: List[SelectionOption]) -> None:
        """
        Build the selections dictionary from loaded selection options.

        Args:
            selections: List of SelectionOption objects
        """
        logger.info(f"Building selections dictionary from {len(selections)} selections...")

        # Build field lookup: "Field Label (Model Description)" -> (model, field)
        field_lookup = {}
        for (model_name, field_name), field in self.fields.items():
            model = self.get_model(model_name)
            if model:
                # Format: "Field Label (Model Description)"
                key = f"{field.label} ({model.description})"
                field_lookup[key] = (model_name, field_name)
                # Also try just field label
                field_lookup[field.label] = (model_name, field_name)

        selections_added = 0
        selections_skipped = 0

        for selection in selections:
            # Try to find the field this selection belongs to
            field_key = selection.field

            if field_key in field_lookup:
                model_name, field_name = field_lookup[field_key]
                self.add_selection(model_name, field_name, selection)
                selections_added += 1
            else:
                logger.debug(
                    f"Skipping selection '{selection.value}' - "
                    f"field '{field_key}' not found"
                )
                selections_skipped += 1

        logger.info(
            f"Selections dictionary built: {selections_added} selections added, "
            f"{selections_skipped} skipped"
        )

    def _build_constraints_dict(self, constraints: List[ConstraintDefinition]) -> None:
        """
        Build the constraints dictionary from loaded constraint definitions.

        Args:
            constraints: List of ConstraintDefinition objects
        """
        logger.info(f"Building constraints dictionary from {len(constraints)} constraints...")

        # Build model name lookup (description -> technical name)
        model_name_map = {
            model.description.lower(): model.name
            for model in self.models.values()
        }

        constraints_added = 0
        constraints_skipped = 0

        for constraint in constraints:
            # Map model description to technical name
            model_key = constraint.model.lower()

            if model_key in model_name_map:
                constraint.model = model_name_map[model_key]
                self.add_constraint(constraint)
                constraints_added += 1
            else:
                logger.debug(
                    f"Skipping constraint '{constraint.name}' - "
                    f"model '{constraint.model}' not found"
                )
                constraints_skipped += 1

        logger.info(
            f"Constraints dictionary built: {constraints_added} constraints added, "
            f"{constraints_skipped} skipped"
        )

    def _build_relations_dict(self, relations: List[RelationDefinition]) -> None:
        """
        Build the relations dictionary from loaded relation definitions.

        Args:
            relations: List of RelationDefinition objects
        """
        logger.info(f"Building relations dictionary from {len(relations)} relations...")

        # Build model name lookup (description -> technical name)
        model_name_map = {
            model.description.lower(): model.name
            for model in self.models.values()
        }

        relations_added = 0
        relations_skipped = 0

        for relation in relations:
            # Map model description to technical name
            model_key = relation.model.lower()

            if model_key in model_name_map:
                relation.model = model_name_map[model_key]
                self.add_relation(relation)
                relations_added += 1
            else:
                logger.debug(
                    f"Skipping relation '{relation.name}' - "
                    f"model '{relation.model}' not found"
                )
                relations_skipped += 1

        logger.info(
            f"Relations dictionary built: {relations_added} relations added, "
            f"{relations_skipped} skipped"
        )

    def _populate_field_selection_values(self) -> None:
        """
        Populate the selection_values list in FieldDefinition objects.

        This links the selections dictionary back to the field definitions.
        """
        logger.info("Populating field selection values...")

        count = 0
        for (model_name, field_name), field in self.fields.items():
            selections = self.get_selections(model_name, field_name)
            if selections:
                field.selection_values = [sel.value for sel in selections]
                count += 1

        logger.info(f"Populated selection values for {count} fields")

    def __repr__(self) -> str:
        """String representation of the knowledge base."""
        return (
            f"OdooKnowledgeBase("
            f"models={len(self.models)}, "
            f"fields={len(self.fields)}, "
            f"selections={sum(len(s) for s in self.selections.values())}, "
            f"constraints={sum(len(c) for c in self.constraints.values())}, "
            f"loaded={self.is_loaded})"
        )
