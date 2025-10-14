"""
Core data structures for the deterministic field mapper system.

This module defines all the dataclasses used throughout the system for
representing Odoo models, fields, constraints, and mappings.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from enum import Enum


# ===========================
# Odoo Model Structures
# ===========================

@dataclass
class ModelDefinition:
    """
    Represents an Odoo model definition.

    Attributes:
        name: Technical model name (e.g., "res.partner")
        description: Human-readable description
        type: Model type (e.g., "Base Object", "Custom")
        is_transient: Whether this is a transient model
        field_ids: List of field names belonging to this model
        parent_models: Models this inherits from
        child_models: Models that inherit from this
    """
    name: str
    description: str
    type: str
    is_transient: bool
    field_ids: List[str] = field(default_factory=list)
    parent_models: List[str] = field(default_factory=list)
    child_models: List[str] = field(default_factory=list)


@dataclass
class FieldDefinition:
    """
    Represents a field in an Odoo model.

    Attributes:
        name: Technical field name
        label: User-friendly label
        model: Parent model name
        field_type: Field type (char, integer, many2one, etc.)
        base_type: Base Field, Related Field, etc.
        is_indexed: Whether field is indexed in database
        is_stored: Whether field value is stored
        is_readonly: Whether field is read-only
        is_required: Whether field is required (derived from constraints)
        related_model: For relational fields, the target model
        size: Maximum size for char fields
        domain: Domain constraint for relational fields
        selection_values: List of valid values for selection fields
        help_text: Help text/description for the field
    """
    name: str
    label: str
    model: str
    field_type: str
    base_type: str
    is_indexed: bool
    is_stored: bool
    is_readonly: bool
    is_required: bool = False
    related_model: Optional[str] = None
    size: Optional[int] = None
    domain: Optional[str] = None
    selection_values: List[str] = field(default_factory=list)
    help_text: Optional[str] = None


@dataclass
class SelectionOption:
    """
    Represents an option in a selection field.

    Attributes:
        sequence: Display order
        field: Full field identifier (model.field)
        value: Internal value
        name: Display name
    """
    sequence: int
    field: str
    value: str
    name: str


@dataclass
class ConstraintDefinition:
    """
    Represents a database or model constraint.

    Attributes:
        type: Constraint type ('u' unique, 'c' check, 'f' foreign key)
        name: Constraint name
        module: Odoo module defining the constraint
        model: Model the constraint applies to
        definition: SQL or Python expression
        fields: List of fields involved in the constraint
    """
    type: str
    name: str
    module: str
    model: str
    definition: str = ""
    fields: List[str] = field(default_factory=list)


@dataclass
class RelationDefinition:
    """
    Represents a many2many relation table.

    Attributes:
        name: Relation table name
        module: Odoo module defining the relation
        model: Model using this relation
        source_field: Field name in source model
        target_field: Field name in target model
    """
    name: str
    module: str
    model: str
    source_field: Optional[str] = None
    target_field: Optional[str] = None


# ===========================
# Column Profiling Structures
# ===========================

@dataclass
class ColumnProfile:
    """
    Statistical and structural analysis of a spreadsheet column.

    Attributes:
        column_name: Name of the column
        sheet_name: Name of the sheet
        data_type: Detected data type
        sample_values: Sample of unique values
        total_rows: Total number of rows
        non_null_count: Count of non-null values
        unique_count: Count of unique values
        null_percentage: Percentage of null values
        uniqueness_ratio: Ratio of unique values to total
        patterns: Detected patterns (email, phone, etc.)
        min_length: Minimum string length
        max_length: Maximum string length
        avg_length: Average string length
        min_value: Minimum numeric value
        max_value: Maximum numeric value
        value_frequencies: Most common values with counts
        date_format: Detected date format
        number_format: Detected number format
    """
    column_name: str
    sheet_name: str
    data_type: str
    sample_values: List[Any]
    total_rows: int
    non_null_count: int
    unique_count: int
    null_percentage: float
    uniqueness_ratio: float
    patterns: Dict[str, float] = field(default_factory=dict)
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    value_frequencies: Dict[Any, int] = field(default_factory=dict)
    date_format: Optional[str] = None
    number_format: Optional[str] = None


# ===========================
# Mapping Structures
# ===========================

class MappingStatus(Enum):
    """Status of a field mapping."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CUSTOM = "custom"


@dataclass
class DataTransformation:
    """
    Transformation needed to map source data to target field.

    Attributes:
        type: Transformation type (split, combine, format, convert, map)
        description: Human-readable description
        source_columns: Source column names
        target_field: Target field name
        transformation_rule: Python expression or function name
    """
    type: str
    description: str
    source_columns: List[str]
    target_field: str
    transformation_rule: str


@dataclass
class FieldMapping:
    """
    Result of matching a source column to an Odoo field.

    Attributes:
        source_column: Name of the source column
        target_model: Target Odoo model
        target_field: Target Odoo field
        confidence: Confidence score (0.0 to 1.0)
        scores: Breakdown of scores from different strategies
        rationale: Explanation for the mapping
        matching_strategy: Strategy that produced this mapping
        alternatives: Alternative mapping suggestions
        transformations: Required data transformations
        constraint_violations: List of constraint violations
        warnings: Warning messages
        status: Current status of the mapping
    """
    source_column: str
    target_model: str
    target_field: Optional[str]
    confidence: float
    scores: Dict[str, float] = field(default_factory=dict)
    rationale: str = ""
    matching_strategy: str = ""
    alternatives: List['FieldMapping'] = field(default_factory=list)
    transformations: List[DataTransformation] = field(default_factory=list)
    constraint_violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    status: MappingStatus = MappingStatus.PENDING
    mapping_type: str = "direct"  # direct, lambda, join, etc.
    lambda_function: Optional[str] = None
    lambda_dependencies: List[str] = field(default_factory=list)
    data_type: Optional[str] = None


@dataclass
class MatchingContext:
    """
    Context information for matching process.

    Attributes:
        sheet_name: Name of the sheet being processed
        column_group: List of all column names in the sheet
        identified_model: The model identified for this sheet
        confirmed_mappings: Already confirmed field mappings
        dataset_metadata: Additional metadata about the dataset
    """
    sheet_name: str
    column_group: List[str] = field(default_factory=list)
    identified_model: Optional[str] = None
    confirmed_mappings: Dict[str, FieldMapping] = field(default_factory=dict)
    dataset_metadata: Dict[str, Any] = field(default_factory=dict)


# ===========================
# Validation Structures
# ===========================

@dataclass
class ValidationResult:
    """
    Result of validating a field mapping.

    Attributes:
        is_valid: Whether the mapping is valid
        errors: List of error messages
        warnings: List of warning messages
        suggested_transformations: Transformations to fix issues
    """
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggested_transformations: List[DataTransformation] = field(default_factory=list)

    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0


# ===========================
# Result Structures
# ===========================

@dataclass
class MappingResult:
    """
    Complete result of mapping a dataset.

    Attributes:
        dataset_name: Name of the dataset
        sheet_mappings: Mappings organized by sheet and column
        primary_model: The primary model identified for the dataset
        overall_confidence: Overall confidence score
        warnings: Global warning messages
        created_at: Timestamp of creation
    """
    dataset_name: str = ""
    sheet_mappings: Dict[str, Dict[str, List[FieldMapping]]] = field(default_factory=dict)
    primary_model: Optional[str] = None
    overall_confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_mapping(self, sheet_name: str, column_name: str, mappings: List[FieldMapping]):
        """Add mappings for a column."""
        if sheet_name not in self.sheet_mappings:
            self.sheet_mappings[sheet_name] = {}
        self.sheet_mappings[sheet_name][column_name] = mappings

    @property
    def mappings(self) -> List[FieldMapping]:
        """Get all mappings (top suggestion for each column)."""
        all_mappings = []
        for sheet_mappings in self.sheet_mappings.values():
            for column_mappings in sheet_mappings.values():
                if column_mappings:
                    all_mappings.append(column_mappings[0])
        return all_mappings


# ===========================
# Performance Structures
# ===========================

@dataclass
class PerformanceMetrics:
    """
    Performance metrics for the mapping system.

    Attributes:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        memory_mb: Memory usage in MB
        timestamp: When the measurement was taken
        metadata: Additional metadata
    """
    operation: str
    duration_ms: float
    memory_mb: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
