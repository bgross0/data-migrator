# Data Migrator - Architecture Documentation

This directory contains auto-generated architecture diagrams and dependency graphs for the Data Migrator codebase.

## 📊 Available Documentation

### 1. **Visual Diagrams** (from pyreverse & pydeps)
- **`classes_DataMigrator.dot`** - Complete class diagram showing all classes, attributes, and methods
- **`packages_DataMigrator.dot`** - Package/module diagram showing high-level structure
- **`field_mapper_deps.dot`** - Dependency graph for the field_mapper module
  - Shows internal dependencies within field_mapper
  - External dependencies: polars, pandas, networkx, pygtrie, pydantic_settings

### 2. **Semantic Documentation** (for AI context)
- **`ARCHITECTURE.yaml`** - Comprehensive module documentation with:
  - Entry points and method signatures
  - Decision trees for architectural choices
  - Integration points and dependencies
  - Performance metrics and common patterns

- **`EXECUTION_FLOWS.md`** - Step-by-step execution traces with file:line references for:
  - Upload → Profile → Map workflow
  - Module selection impact
  - Deterministic mapping generation (8 strategies)
  - Lambda transformation detection
  - Two-phase Odoo import with KeyMap

### 3. **Machine-Readable Paths** (for AI tools)
- **`critical_paths.py`** - Programmatic execution paths with helper functions:
  - 8 critical execution paths with call chains
  - Decision trees with criteria
  - Performance metrics
  - Known failure modes and solutions
  - Helper functions: `find_path()`, `get_call_chain()`, `get_failure_modes()`, etc.

### 4. **Automation & Maintenance**
- **`regenerate_diagrams.sh`** - Script to regenerate all diagrams after code changes
- **`README.md`** (this file) - Documentation index and viewing instructions

## 🔍 How to View These Diagrams

### Option 1: Online DOT Viewer (Easiest)
1. Copy the contents of any `.dot` file
2. Paste into one of these online viewers:
   - https://dreampuf.github.io/GraphvizOnline/
   - https://edotor.net/
   - https://viz-js.com/

### Option 2: VS Code Extension
1. Install "Graphviz Preview" extension in VS Code
2. Open any `.dot` file
3. Right-click → "Open Preview to the Side"

### Option 3: Install Graphviz (For PNG/SVG Generation)
```bash
# Ubuntu/Debian
sudo apt-get install graphviz

# macOS
brew install graphviz

# Then convert DOT to PNG/SVG:
dot -Tpng classes_DataMigrator.dot -o classes_DataMigrator.png
dot -Tsvg field_mapper_deps.dot -o field_mapper_deps.svg
```

### Option 4: Python Graphviz Library
```python
from graphviz import Source

# Render DOT file to PDF/PNG/SVG
Source.from_file('field_mapper_deps.dot').render('field_mapper_deps', format='png')
```

## 📚 Understanding the Diagrams

### Class Diagrams (`classes_DataMigrator.dot`)
Shows:
- All classes in the codebase
- Inheritance relationships (arrows)
- Class attributes and methods
- Relationships between classes

Key patterns to look for:
- **Services layer** (`app.services.*`) - Business logic
- **Models layer** (`app.models.*`) - Database ORM models
- **Field Mapper** (`app.field_mapper.*`) - Core mapping engine
- **API layer** (`app.api.*`) - FastAPI route handlers

### Dependency Graphs (`*_deps.dot`)
Shows:
- Module import dependencies
- Color coding by dependency depth (darker = more dependencies)
- External library dependencies (shown as folder shapes)

**Color Key:**
- Red shades: Internal modules (darker = more central/important)
- Green: pandas library
- Cyan: polars library
- Blue/Purple: Other external libraries

**Key Insights from `field_mapper_deps.dot`:**
- **Main entry point**: `field_mapper_main` (darkest red)
- **Core dependencies**:
  - `knowledge_base` - Loads Odoo dictionary
  - `matching_pipeline` - Orchestrates field matching
  - `column_profiler` - Analyzes spreadsheet columns
- **External deps**: Uses both pandas and polars (transitioning to polars)

## 🔄 Regenerating These Diagrams

Run the regeneration script after major code changes:

```bash
./docs/architecture/regenerate_diagrams.sh
```

Or manually:

```bash
cd backend

# Generate UML diagrams
PYTHONPATH=. venv/bin/pyreverse -o dot -p DataMigrator app/services app/field_mapper app/core
mv *.dot ../docs/architecture/

# Generate dependency graphs
PYTHONPATH=. venv/bin/pydeps app/field_mapper --max-module-depth=3 --cluster --show-dot --nodot > ../docs/architecture/field_mapper_deps.dot 2>&1
```

## 📖 Using These Diagrams and Documentation for AI Agents

This architecture documentation is designed to help AI agents understand the codebase and generate better code. There are three tiers of documentation:

### Tier 1: Visual Diagrams (For Human Understanding)
- `classes_DataMigrator.dot` - Complete UML class diagram
- `packages_DataMigrator.dot` - Module/package structure
- `field_mapper_deps.dot` - Field mapper dependency graph

### Tier 2: Semantic Documentation (For AI Context)
- `ARCHITECTURE.yaml` - Module purposes, entry points, decision criteria
- `EXECUTION_FLOWS.md` - Step-by-step execution traces with file:line references

### Tier 3: Programmatic Queries (For AI Tools)
- `critical_paths.py` - Machine-readable execution paths with helper functions

---

## 🤖 AI Agent Usage Examples

### Example 1: Understanding Architecture Before Making Changes

**Scenario**: You need to modify the mapping generation logic but don't know where to start.

**Prompt**:
```
I need to understand the mapping generation flow. Please read these files:
1. docs/architecture/ARCHITECTURE.yaml (look for field_mapper module)
2. docs/architecture/EXECUTION_FLOWS.md (look for Flow 3: Deterministic Mapping Generation)

Then explain:
- What is the entry point?
- What are the key components?
- Where should I make changes to add a new matching strategy?
```

**Expected Output**: AI will explain the flow from API → Service → Field Mapper → Matching Pipeline, and identify `backend/app/field_mapper/matching/strategies/` as the location to add new strategies.

---

### Example 2: Programmatic Path Querying

**Scenario**: You're debugging a mapping issue and want to trace the exact execution path.

**Prompt**:
```python
# In your Python environment or AI tool:
from docs.architecture.critical_paths import find_path, get_call_chain, get_failure_modes

# Find the mapping generation path
path = find_path("mapping")
print(path["description"])
print(path["entry"])

# Get the call chain
calls = get_call_chain("mapping_generation_v2")
for call in calls:
    print(f"Step {call['step']}: {call['function']} at {call['file']}:{call['line']}")

# Get known failure modes
failures = get_failure_modes("mapping_generation_v2")
for failure in failures:
    print(f"Error: {failure['error']}")
    print(f"Solution: {failure['solution']}")
```

**Use Case**: Quickly identify where to add logging, set breakpoints, or find error handling code.

---

### Example 3: Decision Tree Consultation

**Scenario**: You're unsure whether to use module filtering for a new dataset.

**Prompt**:
```
Please read docs/architecture/critical_paths.py and find the decision tree named "should_use_module_filtering".

Based on that decision tree, should I use module filtering for a dataset where:
- I know the data is for Sales and CRM
- Column names are non-standard (business-specific)
- This is the first time mapping this dataset

Provide your recommendation with reasoning.
```

**Expected Output**: AI will recommend using module selection (Sales + CRM modules) to get 10x search space reduction and +15-30% confidence boost, even though it's the first time mapping, because you know which modules are relevant.

---

### Example 4: Adding a New Feature with Context

**Scenario**: You want to add a new matching strategy to the pipeline.

**Prompt**:
```
I want to add a new matching strategy called "AbbreviationMatchStrategy" that matches common abbreviations (e.g., "Qty" → "quantity", "Desc" → "description").

Please:
1. Read docs/architecture/EXECUTION_FLOWS.md (Flow 3, Phase G: 8 strategies)
2. Read docs/architecture/ARCHITECTURE.yaml (field_mapper.matching module)
3. Identify which files I need to modify
4. Generate the new strategy class following the existing pattern
5. Explain where to register the strategy

Use file:line references from the documentation.
```

**Expected Output**: AI will:
- Reference existing strategies in `backend/app/field_mapper/matching/strategies/`
- Show how to inherit from `BaseStrategy`
- Implement the `match()` method
- Register in `matching_pipeline.py:62-71`

---

### Example 5: Performance Optimization

**Scenario**: You need to optimize the profiling performance.

**Prompt**:
```python
from docs.architecture.critical_paths import get_performance_metrics

# Get current performance
metrics = get_performance_metrics("profiling")
print(f"Current: {metrics['rows_per_second']:,} rows/second")
print(f"Bottleneck: {metrics['bottleneck']}")

# Now ask AI:
# "The current profiling bottleneck is file I/O (Excel reading).
# What optimization strategies can I use? Consider:
# - Current engine: Polars with fastexcel
# - Target: 500K+ rows/second
# - Files to modify: backend/app/field_mapper/profiling/column_profiler.py
```

**Use Case**: Get context-aware optimization suggestions based on actual performance data.

---

### Example 6: Troubleshooting Import Errors

**Scenario**: Import fails with foreign key errors.

**Prompt**:
```
I'm getting foreign key constraint violations during import. Please:

1. Read docs/architecture/EXECUTION_FLOWS.md (Flow 5: Two-Phase Odoo Import)
2. Read docs/architecture/critical_paths.py (two_phase_import failure modes)
3. Explain:
   - How KeyMap works
   - Where to add debug logging
   - How to verify the import graph order

Then help me debug by examining:
- backend/app/importers/graph.py (topological order)
- backend/app/importers/executor.py (_resolve_relationships method)
```

**Expected Output**: AI will explain the KeyMap lookup mechanism, show where parent records should be stored, and suggest adding logging at specific file:line locations.

---

## 🎯 Best Practices for AI Agents

### Do's ✅
- **Always read ARCHITECTURE.yaml first** for high-level context
- **Use EXECUTION_FLOWS.md** to understand step-by-step flows before modifying code
- **Query critical_paths.py programmatically** for precise file:line locations
- **Reference decision trees** when making architectural choices
- **Check failure modes** in critical_paths.py before implementing error handling

### Don'ts ❌
- **Don't guess file locations** - use the documentation to find exact paths
- **Don't assume flow order** - verify in EXECUTION_FLOWS.md
- **Don't skip reading entry points** - understand the API surface first
- **Don't ignore performance metrics** - consider documented bottlenecks

---

## 📝 Keeping Documentation Updated

When you make significant architectural changes:

1. **Regenerate diagrams**:
   ```bash
   ./docs/architecture/regenerate_diagrams.sh
   ```

2. **Update ARCHITECTURE.yaml** if you:
   - Add new modules or entry points
   - Change decision criteria
   - Modify integration points

3. **Update EXECUTION_FLOWS.md** if you:
   - Change execution order
   - Add new phases to existing flows
   - Modify critical decision points

4. **Update critical_paths.py** if you:
   - Add new critical paths
   - Change timing characteristics
   - Discover new failure modes

---

## 🔗 Quick Reference Links

- **Entry Points**: See `ARCHITECTURE.yaml` → `modules.<module_name>.entry_points`
- **Call Chains**: See `EXECUTION_FLOWS.md` → Flow sections
- **Performance**: See `critical_paths.py` → `PERFORMANCE` dict
- **Decisions**: See `critical_paths.py` → `DECISION_TREES` dict
- **Failures**: See `critical_paths.py` → `path.failure_modes`

## 🎯 Key Architecture Insights

### Mapping Pipeline Flow
```
1. DeterministicFieldMapper (main.py)
   ↓
2. ColumnProfiler (profiling/)
   ↓
3. MatchingPipeline (matching/)
   ├── BusinessContextAnalyzer
   ├── CellDataAnalyzer
   └── Multiple matching strategies
   ↓
4. MappingExecutor (executor/)
   ↓
5. Output: FieldMapping objects
```

### Module Selection Flow
```
Dataset.selected_modules (JSON)
   ↓
ModuleRegistry.filter_by_modules()
   ↓
Reduced field search space (9,947 → ~500 fields)
   ↓
MatchingPipeline (higher accuracy)
```

### Data Processing Stack
- **Storage**: SQLite (dev) / PostgreSQL (prod)
- **Data Processing**: Polars (primary) + Pandas (legacy, being removed)
- **Graph Analysis**: NetworkX (for model relationships)
- **API**: FastAPI + Celery (async tasks)
- **Frontend**: React + TypeScript + Vite

## 📝 Notes

- These diagrams are **generated artifacts** - do not edit manually
- Regenerate after major refactoring or architectural changes
- The `.dot` files are plain text and can be version controlled
- File sizes: Classes diagram ~36KB, Field mapper deps ~11KB

## 🛠️ Tools Used

- **pyreverse** (part of pylint) - UML diagram generation
- **pydeps** - Python dependency graphing
- **Graphviz** - DOT format rendering (optional for viewing)

---

**Last Updated**: 2025-10-14
**Generated From**: Commit `HEAD` of main branch
