# Deterministic Field Mapper

A truly deterministic, rule-based system for mapping business spreadsheet columns to Odoo fields using authoritative Odoo model definitions as the single source of truth.

## Overview

This system provides intelligent, explainable field mapping for Odoo data migration. It uses 5 Odoo dictionary Excel files as the authoritative source and applies a multi-strategy matching pipeline to map ANY business spreadsheet to the appropriate Odoo fields.

### Key Features

- **Truly Deterministic**: No hardcoded mappings, works universally for any spreadsheet
- **Rule-Based**: Uses 8 complementary matching strategies with configurable weights
- **Explainable**: Every mapping decision includes a detailed rationale
- **Fast**: O(1) lookups via multiple indexes and Trie structures
- **Comprehensive**: Validates against Odoo constraints and suggests transformations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Deterministic Field Mapper                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Excel/CSV     │  │  Odoo Dict      │  │  Knowledge      │  │
│  │  Upload        │──▶│  Loaders        │──▶│  Base           │  │
│  │  (5 files)     │  │  (5 loaders)    │  │  (Graph + Index)│  │
│  └────────────────┘  └─────────────────┘  └─────────────────┘  │
│           │                                         │            │
│           ▼                                         ▼            │
│  ┌────────────────┐                    ┌─────────────────────┐  │
│  │  Column        │                    │  8 Matching         │  │
│  │  Profiler      │                    │  Strategies         │  │
│  │  (Stats+Types) │                    │  • ExactName        │  │
│  └────────────────┘                    │  • Label            │  │
│           │                             │  • SelectionValue   │  │
│           │                             │  • DataType         │  │
│           ▼                             │  • Pattern          │  │
│  ┌────────────────┐                    │  • Statistical      │  │
│  │  Matching      │◀───────────────────│  • Contextual       │  │
│  │  Pipeline      │                    │  • Fuzzy            │  │
│  │  (Orchestrator)│                    └─────────────────────┘  │
│  └────────────────┘                                             │
│           │                                                      │
│           ▼                                                      │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Constraint    │  │  Mapping        │  │  FastAPI        │  │
│  │  Validator     │  │  Executor       │  │  Endpoints      │  │
│  └────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Navigate to backend directory
cd /home/ben/Documents/GitHub/data-migrator/backend

# Activate virtual environment
source venv/bin/activate

# Dependencies are already in requirements.txt
# Install if needed:
# pip install networkx==3.2.1 pygtrie==2.5.0 cachetools==5.3.2 psutil==5.9.8
```

## Quick Start

### Python API

```python
from app.field_mapper.main import DeterministicFieldMapper

# Initialize mapper with Odoo dictionary path
mapper = DeterministicFieldMapper(
    dictionary_path="/path/to/odoo-dictionary"
)

# Map a file
result = mapper.map_file("customer_data.xlsx")

# Access mappings
for sheet_name, sheet_mappings in result.mappings.items():
    print(f"\nSheet: {sheet_name}")
    for column_name, field_mappings in sheet_mappings.items():
        best_mapping = field_mappings[0]
        print(f"  {column_name} -> {best_mapping.target_model}.{best_mapping.target_field}")
        print(f"    Confidence: {best_mapping.confidence:.2f}")
        print(f"    Rationale: {best_mapping.rationale}")
```

### REST API

```bash
# Start the API server
cd app/field_mapper
python -m api.app

# Or with uvicorn
uvicorn app.field_mapper.api.app:app --reload --host 0.0.0.0 --port 8000
```

#### API Endpoints

**Health Check**
```bash
curl http://localhost:8000/health
```

**Map a File**
```bash
curl -X POST http://localhost:8000/api/v1/map \
  -F "file=@customer_data.xlsx" \
  -F "sheet_name=Customers"
```

**Get All Models**
```bash
curl http://localhost:8000/api/v1/models
```

**Get Fields for a Model**
```bash
curl http://localhost:8000/api/v1/models/res.partner/fields
```

**Validate Mappings**
```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "mappings": {...},
    "target_model": "res.partner"
  }'
```

## Configuration

Configuration is managed via `config/settings.py`:

```python
class FieldMapperSettings(BaseSettings):
    # Odoo dictionary path
    odoo_dictionary_path: str = "/path/to/odoo-dictionary"

    # Caching
    cache_enabled: bool = True
    cache_size: int = 10000

    # Matching
    confidence_threshold: float = 0.6

    # Strategy Weights
    exact_match_weight: float = 1.0
    label_match_weight: float = 0.95
    selection_value_weight: float = 0.90
    data_type_weight: float = 0.70
    pattern_match_weight: float = 0.75
    statistical_weight: float = 0.60
    contextual_weight: float = 0.80
    fuzzy_match_weight: float = 0.65
```

## Matching Strategies

### 1. ExactNameMatchStrategy (weight: 1.0)
Perfect match between column name and field name.
```
Column: "customer_id" → Field: "customer_id" (confidence: 1.0)
```

### 2. LabelMatchStrategy (weight: 0.95)
Matches column name to field label.
```
Column: "Customer Name" → Field: "name" (label: "Customer Name")
```

### 3. SelectionValueMatchStrategy (weight: 0.90)
Matches based on selection field values.
```
Column with ["draft", "confirmed"] → Field: "state" (same selections)
```

### 4. DataTypeCompatibilityStrategy (weight: 0.70)
Matches based on data type compatibility.
```
Column: integer → Field: integer/float/many2one
```

### 5. PatternMatchStrategy (weight: 0.75)
Detects patterns like email, phone, URL, currency.
```
Column with emails → Field: "email"
```

### 6. StatisticalSimilarityStrategy (weight: 0.60)
Analyzes statistical properties.
```
High uniqueness → ID fields
Low uniqueness → Status/selection fields
```

### 7. ContextualMatchStrategy (weight: 0.80)
Uses context from other columns to detect likely models.
```
Sheet with ["customer_id", "email", "phone"] → res.partner
```

### 8. FuzzyMatchStrategy (weight: 0.65)
Fuzzy string matching as fallback.
```
Column: "cust_name" → Field: "customer_name" (similarity: 0.73)
```

## Knowledge Base

The knowledge base is built from 5 Odoo dictionary Excel files:

1. **Models (ir.model)** - All Odoo models
2. **Fields (ir.model.fields)** - All fields with types and labels
3. **Field Selections** - Selection values for selection fields
4. **Model Constraints** - Unique and check constraints
5. **Relation Model** - Many2many relation tables

### Data Structures

```python
# NetworkX Graph
model_graph: nx.DiGraph  # Model relationships

# Inverted Indexes (O(1) lookup)
field_name_index: Dict[str, List[Tuple[str, str]]]
field_label_index: Dict[str, List[Tuple[str, str]]]
selection_value_index: Dict[str, List[Tuple[str, str]]]
field_type_index: Dict[str, List[Tuple[str, str]]]

# Trie Structures (prefix matching)
field_name_trie: pygtrie.CharTrie
field_label_trie: pygtrie.CharTrie
```

## Validation

The system validates mappings against Odoo constraints:

```python
from app.field_mapper.validation import ConstraintValidator

validator = ConstraintValidator(knowledge_base)
result = validator.validate_mappings(mappings, "res.partner", df)

if not result.is_valid:
    print("Errors:", result.errors)
    print("Warnings:", result.warnings)
    print("Missing required:", result.missing_required_fields)
    print("Suggestions:", result.suggestions)
```

## Data Transformation

The MappingExecutor applies transformations:

```python
from app.field_mapper.executor import MappingExecutor

executor = MappingExecutor(knowledge_base)

# Execute mappings
transformed_df = executor.execute_mappings(df, mappings)

# Group by model
by_model = executor.execute_by_model(df, mappings)

# Generate Odoo import files
executor.generate_odoo_import_csv(
    by_model["res.partner"],
    "res.partner",
    "output.csv"
)
```

## Performance

The system is optimized for performance:

- **O(1) lookups** via inverted indexes
- **Trie structures** for prefix matching
- **LRU/TTL caching** for expensive operations
- **Parallel strategy execution**
- **Performance monitoring** built-in

```python
from app.field_mapper.performance import get_monitor

monitor = get_monitor()

with monitor.measure("load_knowledge_base"):
    # operation
    pass

print(monitor.get_summary())
```

## Testing

Run the test suite:

```bash
# Unit tests
pytest app/field_mapper/tests/

# Integration tests
pytest app/field_mapper/tests/integration/

# Performance tests
pytest app/field_mapper/tests/performance/
```

## Example Usage

See `examples/` directory for complete examples:

- `basic_mapping.py` - Basic file mapping
- `api_client.py` - API usage examples
- `custom_strategies.py` - Custom strategy development
- `batch_processing.py` - Batch file processing

## Logging

Logs are written to `logs/field_mapper/`:

- `field_mapper.log` - Main log
- `knowledge_base.log` - KB operations
- `matching.log` - Matching operations
- `profiling.log` - Column profiling
- `validation.log` - Validation operations
- `api.log` - API requests
- `performance.log` - Performance metrics

## Troubleshooting

**Issue: Low confidence mappings**
- Check confidence threshold in settings
- Review strategy weights
- Inspect column profiles for data quality

**Issue: Missing required fields**
- Use validation endpoint to identify missing fields
- Check if fields are in the spreadsheet with different names
- Review field labels vs technical names

**Issue: Slow performance**
- Enable caching in settings
- Check performance metrics
- Consider reducing sample size for profiling

## Contributing

The system is designed to be extensible:

1. **Custom Strategies**: Extend `BaseStrategy`
2. **Custom Transformations**: Add to `MappingExecutor`
3. **Custom Validators**: Extend `ConstraintValidator`

## License

[Your License Here]

## Support

For issues and questions:
- GitHub Issues: [link]
- Documentation: [link]
- API Docs: http://localhost:8000/docs (when running)
