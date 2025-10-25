# Data Migrator Repository Structure

## Overview
A full-stack data migration platform for importing messy spreadsheets into Odoo with automated field mapping, data cleaning, and deterministic CSV export.

**Stack**: FastAPI + SQLAlchemy + SQLite + React + Vite + Tailwind CSS

---

## Root Structure

```
data-migrator/
├── backend/              # FastAPI backend (Python 3.13)
├── frontend/             # React SPA (TypeScript + Vite)
├── storage/              # File storage (uploads, profiles, exports)
├── docs/                 # Architecture documentation
└── *.md                  # Project documentation files
```

---

## Backend (`backend/`)

### Core Application (`app/`)

#### API Layer (`app/api/`)
REST endpoints for all features:
- `datasets.py` - Dataset CRUD operations
- `sheets.py` - Sheet management and preview
- `mappings.py` - Field mapping suggestions and CRUD
- `transforms.py` - Data transformation rules
- `imports.py` - Import execution and monitoring
- `exports.py` - **NEW: Deterministic CSV export for Odoo**
- `exceptions.py` - **NEW: Exception tracking API**
- `templates.py` - **NEW: Template management**
- `addons.py` - Odoo addon generator
- `odoo.py` - Odoo field introspection
- `graphs.py` - Data flow graph visualization
- `operations.py` - Operation tracking

#### Models (`app/models/`)
SQLAlchemy ORM models:
- `source.py` - Dataset, Sheet
- `profile.py` - SheetProfile, ColumnProfile
- `mapping.py` - Mapping, FieldMapping
- `run.py` - Run, RunLog, KeyMap, ImportGraph
- `odoo_connection.py` - OdooConnection
- `exception.py` - **NEW: Exception tracking**
- `graph.py` - Graph, GraphRun

#### Schemas (`app/schemas/`)
Pydantic models for API serialization:
- `dataset.py`, `mapping.py`, `run.py`, `graph.py`
- `export.py` - **NEW: Export response schemas**
- `exception.py` - **NEW: Exception schemas**
- `template.py` - **NEW: Template schemas**

#### Services (`app/services/`)
Business logic layer:
- `dataset_service.py` - Dataset CRUD
- `mapping_service.py` - Mapping suggestions
- `transform_service.py` - Transform application
- `import_service.py` - Import orchestration
- `export_service.py` - **NEW: Export orchestration with FK cache**
- `template_service.py` - **NEW: Template management**
- `profiler_tasks.py` - Celery profiling tasks
- `import_tasks.py` - Celery import tasks
- `addon_generator.py` - Odoo addon generation
- `graph_service.py` - Graph operations
- `operation_tracker.py` - Operation logging

#### Core Logic (`app/core/`)
Foundational components:
- `profiler.py` - Column analysis (dtype, quality metrics)
- `matcher.py` - Header → Odoo field mapping (exact/fuzzy/AI)
- `hybrid_matcher.py` - Enhanced matching with business context
- `transformer.py` - Data cleaning transform registry
- `field_detector.py` - Field type detection
- `database.py` - SQLAlchemy session management
- `config.py` - Settings (loads from .env)
- `celery_app.py` - Celery configuration
- `ids.py` - ID generation utilities
- `data_cleaner.py` - Initial data cleaning
- `lambda_transformer.py` - Lambda-based transformations

#### Import System (`app/importers/`)
Two-phase import execution:
- `graph.py` - **Topological sort for entity dependencies**
- `executor.py` - **TwoPhaseImporter with KeyMap resolution**

#### **NEW: Deterministic Export System**

##### Registry (`app/registry/`)
YAML-driven configuration:
- `loader.py` - **Registry loader with validation**
- `odoo.yaml` - **Central registry (16 models, 23 import_order)**
- `seeds/*.yaml` - **6 seed files with synonyms**

##### Transform (`app/transform/`)
Idempotent normalizers:
- `normalizers.py` - **Phone, email, date, bool, enum normalizers**
- `rules.py` - **Rules DSL parser (isset, ==, or, ternary)**

##### Validate (`app/validate/`)
Exception-driven validation:
- `validator.py` - **Validation pipeline with FK cache**

##### Export (`app/export/`)
Deterministic CSV emission:
- `csv_emitter.py` - **Deterministic CSV writer with normalization**
- `idgen.py` - **External ID generation (slug, NFKD, dedup)**
- `order.py` - Import order utilities

##### Ports & Adapters (`app/ports/`, `app/adapters/`)
Hexagonal architecture:
- `app/ports/repositories.py` - **Abstract interfaces**
- `app/ports/tasks.py` - **TaskRunner interface**
- `app/adapters/repositories_sqlite.py` - **SQLite implementations**
- `app/adapters/tasks_inline.py` - **Inline task runner**

#### Connectors (`app/connectors/`)
External system integrations:
- `odoo.py` - **Odoo JSON-RPC client with upsert**

#### Generators (`app/generators/`)
Code generation:
- `addon.py` - **Odoo addon ZIP generator**

#### Cleaners (`app/cleaners/`)
Initial data cleaning pipeline:
- `data_cleaner.py` - Main cleaning orchestrator
- `rules/` - Cleaning rule implementations
  - `column_name.py` - Column name normalization
  - `header_detection.py` - Header row detection
  - `html_entity.py` - HTML entity decoding
  - `whitespace.py` - Whitespace normalization

#### Field Mapper (`app/field_mapper/`)
Advanced field mapping system:
- `matching/` - Matching strategies
  - `matching_pipeline.py` - Strategy orchestration
  - `strategies/` - Individual strategies (exact, fuzzy, contextual, etc.)
- `core/` - Knowledge base and module registry
- `profiling/` - Column profiling
- `executor/` - Mapping execution

### Tests (`backend/tests/`)

#### **NEW: Deterministic Export Tests**
- `test_registry_loader.py` - **Registry loading (20 tests)**
- `test_normalizers.py` - **Idempotent normalizers (39 tests, 100% passing)**
- `test_validator.py` - **Validation pipeline (10 tests, 100% passing)**
- `test_csv_emitter.py` - **CSV emission (9 tests, 100% passing)**
- `test_determinism.py` - **SHA256 verification (5 tests, 100% passing)**

#### Matcher Validation (`tests/matcher_validation/`)
- Ground truth datasets
- Comprehensive test harness
- Performance reports

### Database Migrations (`backend/alembic/`)
Alembic migration files:
- `env.py` - Alembic environment config
- `versions/` - Migration files
  - `8204a2bbd178_initial_schema.py`
  - `1760583762_create_exceptions_table.py` - **NEW**
  - `654c378c4698_add_odoo_connections_table.py`
  - `776044534d04_add_cleaned_data_tracking_to_dataset.py`
  - `abc123def456_add_graphs_and_graph_runs_tables.py`
  - And more...

### **NEW: Registry & Seeds (`backend/registry/`)**
YAML configuration files:
- `odoo.yaml` - **Central registry (923 lines)**
  - 16 models defined
  - 23 models in import_order
  - Field specs with types, transforms, FK targets
- `seeds/crm_stages.yaml` - CRM stage seeds with synonyms
- `seeds/crm_lost_reasons.yaml` - Lost reason seeds
- `seeds/teams_users.yaml` - Team and user seeds
- `seeds/utm.yaml` - UTM source/medium/campaign seeds

### **NEW: Sample Data (`backend/samples/`)**
Test data for determinism verification:
- `partners.csv` - 3 partner records
- `leads.csv` - 3 lead records with FK references

### **NEW: Templates (`backend/templates/`)**
Pre-configured migration templates:
- `essential_setup.json`
- `sales_crm.json`
- `projects.json`
- `accounting.json`
- `complete_migration.json`

### Configuration Files
- `Makefile` - **NEW: Build automation (test, determinism, clean)**
- `.env` - Environment variables
- `alembic.ini` - Alembic configuration
- `requirements.txt` - Python dependencies

---

## Frontend (`frontend/`)

### Source (`src/`)

#### Pages (`src/pages/`)
Main application views:
- `Dashboard.tsx` - Dataset list and overview
- `Upload.tsx` - File upload interface
- `DatasetDetail.tsx` - Dataset management
- `Mappings.tsx` - Field mapping interface
- `Import.tsx` - Import execution
- `Runs.tsx` - Import run history
- `FlowView.tsx` - Graph-based data flow visualization

#### Components (`src/components/`)
Reusable UI components:
- `Layout.tsx` - Main layout wrapper
- `SpreadsheetPreview.tsx` - Data preview table
- `CleanedDataPreview.tsx` - Cleaned data view
- `CleaningReport.tsx` - Cleaning report display
- `SheetSplitter.tsx` - Sheet splitting interface
- `TransformModal.tsx` - Transform configuration
- `CustomFieldModal.tsx` - Custom field creation
- `LambdaMappingModal.tsx` - Lambda transformation
- `OdooConnectionModal.tsx` - Odoo connection setup
- `ModuleSelector.tsx` - Module selection
- `StatusOverlay.tsx` - Status indicator
- `QuickStart.tsx` - **NEW: Quick start guide**

#### Visualizer (`src/visualizer/`)
Data flow graph visualization:
- `FlowCanvas.tsx` - Main canvas component
- `InspectorPanel.tsx` - Node inspector
- `NodeToolbar.tsx` - Node actions
- `layout.ts` - Graph layout engine
- `useGraphStore.ts` - Graph state management
- `nodes/` - Node type implementations
  - `BaseNode.tsx`, `SheetNode.tsx`, `FieldNode.tsx`
  - `LoaderNode.tsx`, `TransformNode.tsx`, `ValidatorNode.tsx`
  - `JoinNode.tsx`, `ModelNode.tsx`

#### Services (`src/services/`)
- `api.ts` - **API client (axios)**

#### Types (`src/types/`)
TypeScript definitions:
- `mapping.ts`, `graph.ts`

### Configuration
- `package.json` - NPM dependencies
- `tsconfig.json` - TypeScript config
- `vite.config.ts` - Vite build config

---

## Storage (`storage/`)

Runtime file storage:
```
storage/
├── uploads/          # Uploaded CSV/XLSX files
├── profiles/         # Column profile JSON files
├── addons/           # Generated Odoo addon ZIPs
└── exports/          # Exported Odoo CSV ZIPs
```

---

## Documentation (`docs/`)

### Architecture (`docs/architecture/`)
- `README.md` - Architecture overview
- `ARCHITECTURE.yaml` - System architecture definition
- `EXECUTION_FLOWS.md` - Critical execution paths
- `critical_paths.py` - Path analyzer

---

## Root Documentation Files

### Setup & Guides
- `README.md` - Main project overview
- `SETUP.md` - Installation and setup guide
- `CLAUDE.md` - **Claude Code instructions**

### Architecture & Implementation
- `ARCHITECTURE.md` - System architecture
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `END_TO_END_TEST_GUIDE.md` - Testing guide
- `EXPORT_GUIDE.md` - Export functionality guide

### Status & Issues
- `TODO.md` - Task list
- `DISCONNECTED_FRONTEND_FEATURES.md` - Frontend issues
- `CRITICAL_BUG_FIX.md` - Bug fix log
- `IMPROVEMENTS_SUMMARY.md` - Improvement log
- `SPRINT_FIXES.md` - Sprint fix log

### **NEW: Validation**
- `VALIDATION_REPORT.md` - **Comprehensive validation report**

---

## Key File Counts

| Category | Count |
|----------|-------|
| Python files | ~150 |
| TypeScript/TSX files | ~40 |
| Test files | ~20 |
| YAML config files | 7 |
| Migration files | 8 |
| Documentation files | 15+ |

---

## Import Order (Registry)

The deterministic export follows this import order (23 models):

1. `res.currency` - Currencies
2. `res.country` - Countries
3. `res.country.state` - States/provinces
4. `res.partner.industry` - Industries
5. `product.category` - Product categories
6. `uom.uom` - Units of measure
7. `res.users` - Users
8. `res.company` - Companies
9. `product.template` - Product templates
10. `product.product` - Products
11. `res.partner` - Partners/contacts
12. `crm.team` - CRM teams
13. `utm.source` - UTM sources
14. `utm.medium` - UTM mediums
15. `utm.campaign` - UTM campaigns
16. `crm.lost.reason` - Lost reasons
17. `crm.lead` - Leads/opportunities
18. `mail.activity` - Activities
19. `project.project` - Projects
20. `sale.order` - Sales orders
21. `sale.order.line` - Sales order lines
22. `account.move` - Account moves
23. `account.analytic.line` - Analytic lines

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+
- **Database**: SQLite (production: PostgreSQL ready)
- **Data Processing**: Pandas, Polars
- **Tasks**: Celery (optional)
- **Testing**: pytest 8.3+
- **Python**: 3.11+

### Frontend
- **Framework**: React 18+
- **Language**: TypeScript 5+
- **Build**: Vite 5+
- **Styling**: Tailwind CSS 3+
- **HTTP**: Axios
- **State**: Zustand, React Query

### Infrastructure
- **Web Server**: Uvicorn
- **Storage**: Local filesystem (S3-ready via adapters)
- **Deployment**: Docker-ready

---

## Key Features by Directory

| Directory | Key Features |
|-----------|-------------|
| `app/api/` | REST endpoints, request/response handling |
| `app/services/` | Business logic, orchestration |
| `app/core/` | Profiling, matching, transformation |
| `app/importers/` | Two-phase import, topological sort |
| `app/registry/` | **YAML-driven configuration** |
| `app/transform/` | **Idempotent normalizers** |
| `app/validate/` | **Exception-driven validation** |
| `app/export/` | **Deterministic CSV emission** |
| `app/ports/` | **Abstract interfaces (hexagonal)** |
| `app/adapters/` | **Concrete implementations** |
| `app/connectors/` | Odoo JSON-RPC integration |
| `app/cleaners/` | Initial data cleaning |
| `app/field_mapper/` | Advanced field mapping |
| `frontend/src/pages/` | Main application views |
| `frontend/src/visualizer/` | Graph visualization |
| `tests/` | Comprehensive test suite |

---

## Data Flow

```
1. Upload → storage/uploads/
2. Profile → Column analysis → storage/profiles/
3. Clean → data_cleaner → Dataset.cleaned_data_path
4. Match → Mapping suggestions → database
5. Transform → Apply rules → Mapping.field_mappings
6. **Export** → Registry → Validator → CSVEmitter → storage/exports/
7. Import → TwoPhaseImporter → Odoo via JSON-RPC
```

---

## Recent Additions (Last Session)

### Deterministic Export System (Commits 1-6)
- ✅ Registry loader with YAML schemas
- ✅ Idempotent normalizers (phone, email, date, bool, enum)
- ✅ Validator with exceptions lane
- ✅ CSV emitter with deterministic ID generation
- ✅ Export orchestrator with FK cache
- ✅ Sample data and Makefile
- ✅ 5 determinism tests (SHA256 verification)

### Validation Fixes
- ✅ Circular dependency handling
- ✅ Self-referential FK support
- ✅ Optional FK support
- ✅ External reference support

### Test Suite
- ✅ 83 total tests
- ✅ 79 passing (95%)
- ✅ 5 determinism tests (100%)
- ✅ All critical paths validated

