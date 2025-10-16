# Data Migrator Architecture Documentation

## Overview

Data Migrator is an intelligent data migration platform for importing messy spreadsheets into Odoo with automated column mapping, relationship resolution, and custom field generation. It uses a FastAPI backend with synchronous processing, a React frontend, and integrates with Odoo via JSON-RPC.

**Stack**: FastAPI + SQLAlchemy + SQLite + React + Vite + Tailwind CSS + Polars

## Backend Architecture

### **Core System (`/backend/app/core/`)**

- **config.py** - Configuration management, loads from `.env` (database URLs, Odoo settings, API keys)
- **database.py** - SQLAlchemy session management and dependency injection
- **profiler.py** - Column analysis: detects data types, quality metrics, null percentages
- **lambda_transformer.py** - Advanced lambda-based data transformation system
- **matcher.py** & **hybrid_matcher.py** - Header-to-Odoo field mapping using exact/fuzzy matching
- **odoo_field_mappings.py** - Comprehensive Odoo module field definitions

### **Import System Components**

**These components exist as infrastructure but are currently used in test environments:**

- **Field Mapper System (`/backend/app/field_mapper/`)** - Sophisticated deterministic field mapping engine with Polars integration
- **Data Cleaning System (`/backend/app/cleaners/`)** - Rule-based data cleaning with Polars (test-only)

### **Import System (`/backend/app/importers/`)**

**Two-phase import execution:**

- **graph.py** - Topological sorting for entity dependencies (parents before children)
- **executor.py** - `TwoPhaseImporter` orchestrates import phases with KeyMap resolution

### **Services Layer (`/backend/app/services/`)**

**Active business logic orchestration:**

- **dataset_service.py** - Dataset CRUD operations and file management with synchronous profiling
- **mapping_service.py** - Field mapping CRUD with basic matching suggestions
- **import_service.py** - Import orchestration with synchronous execution
- **transform_service.py** - Transform application and chain management
- **odoo_migrate_export.py** - Export bridge to odoo-migrate format (ZIP generation)
- **operation_tracker.py** - Real-time operation tracking with SQLite storage
- **odoo_field_service.py** - Odoo field discovery and metadata
- **graph_service.py** - Graph specification management and visualization

**Supporting Infrastructure (Celery tasks exist but not actively used):**
- **profiler_tasks.py**, **import_tasks.py** - Async task definitions (infrastructure only)

### **API Layer (`/backend/app/api/`)**

**REST endpoints organized by domain:**

- **datasets.py** - Dataset management, file uploads, profiling
- **mappings.py** - Field mapping CRUD with AI suggestions
- **transforms.py** - Transform management and application
- **imports.py** - Import execution and run tracking
- **exports.py** - **NEW**: odoo-migrate export endpoints
- **sheets.py** - Multi-sheet Excel file handling
- **odoo.py** - Odoo connection management and field discovery
- **operations.py** - Operation tracking and status monitoring
- **health.py** - System health checks

### **Models (`/backend/app/models/`)**

**SQLAlchemy ORM models:**

- **source.py** - Dataset, Sheet entities for file storage
- **profile.py** - SheetProfile, ColumnProfile for analysis results
- **mapping.py** - Mapping, FieldMapping for field relationships
- **run.py** - Run, RunLog, KeyMap, ImportGraph for import execution
- **odoo_connection.py** - Odoo connection configuration

### **Connectors (`/backend/app/connectors/`)**

**External system integrations:**

- **odoo.py** - OdooConnector - JSON-RPC client for Odoo API
- **csv_export.py** - CSV fallback export connector

### **Generators (`/backend/app/generators/`)**

**Code generation utilities:**

- **addon_generator.py** - Generates Odoo addon ZIPs for custom fields

## Frontend Architecture

### **Pages (`/frontend/src/pages/`)**

**React SPA with TypeScript for different user workflows:**

- **Dashboard.tsx** - Main dashboard with dataset overview
- **DatasetDetail.tsx** - Detailed dataset view with profiling results
- **Upload.tsx** - File upload interface with multi-format support
- **Mappings.tsx** - Interactive field mapping with AI suggestions
- **Import.tsx** - Import execution with progress tracking
- **Runs.tsx** - Import run results and logging

### **Components (`/frontend/src/components/`)**

**Reusable UI components:**

- **LambdaMappingModal.tsx** - Advanced lambda expression mapping interface
- **SheetSplitter.tsx** - Interactive Excel sheet management
- **ModuleSelector.tsx** - Odoo module selection for constrained mapping
- **TransformModal.tsx** - Data transformation configuration
- **OdooConnectionModal.tsx** - Odoo connection setup
- **CustomFieldModal.tsx** - Custom field creation
- **StatusOverlay.tsx** - Real-time operation status display

## Key Integrations

### **Polars Integration**

- High-performance data processing throughout the backend
- Used in cleaners, field mapper, and profiling systems
- Replaces pandas for better performance with large datasets

### **Synchronous Execution Pipeline**

- Direct service calls for profiling and import
- Real-time progress tracking via OperationTracker polling  
- No background worker processes (simpler deployment)

### **Two-Phase Import Graph**

Topological ordering ensures dependency resolution:
1. **Phase A**: Import parent entities, build KeyMap (source_value → odoo_id)  
2. **Phase B**: Import children using KeyMap for foreign key resolution

### **Export Bridge Architecture**

**NEW feature connecting to odoo-migrate:**
- Transforms interactive cleanup work into deterministic file-based pipeline
- Generates ZIP with YAML configs, cleaned CSVs, and lookup tables
- Applies transforms during export, produces clean data for odoo-migrate

## Actual Data Flow Pipeline

```
Upload → Profile (Sync) → Map (Basic) → Transform (Lambda) → Export/Import (Sync)
      │         │            │               │                   │
  File    Column Profiling  Header Mapping  Lambda Expressions   Final Output
Storage     (Polars)     (Basic/Fuzzy)        (Polars)       (Import/Export)
```

## Core Working Pipeline

1. **Upload & Profile (Synchronous)** → User uploads spreadsheet → Service directly calls ColumnProfiler
2. **Match & Map (Basic)** → HeaderMatcher suggests mappings using exact/fuzzy patterns
3. **Transform (Lambda)** → Apply lambda expressions through LambdaTransformer
4. **Import/Export (Synchronous)** → Direct execution through services
5. **Track (Real-time)** → OperationTracker provides progress updates via polling

## KeyMap System

The KeyMap is critical for relationship resolution:

```python
# Maps source spreadsheet values to Odoo record IDs
KeyMap(
    run_id=1,
    source_model="customer_sheet",
    source_field="customer_name",
    source_value="Acme Corp",
    odoo_model="res.partner",
    odoo_id=42  # Odoo ID of created record
)
```

When importing child records (e.g., projects), the executor looks up parent IDs:
- Spreadsheet has "Customer Name: Acme Corp"
- KeyMap translates "Acme Corp" → `res.partner` ID 42
- Project import sets `partner_id=42`

## Default Import Graph

Standard topological order (defined in `graph.py:from_default()`):

1. `res.partner` (customers/vendors) - no dependencies
2. `crm.lead` - depends on `res.partner`
3. `product.template` / `product.product` - no dependencies
4. `project.project` - depends on `res.partner`
5. `project.task` - depends on `project.project`
6. `sale.order` - depends on `res.partner`
7. `sale.order.line` - depends on `sale.order` and `product.product`
8. `account.move` - accounting entries

## Key Technical Patterns

### Alembic Migrations

- Always use the virtual environment's alembic: `./venv/bin/alembic`
- Migration files live in `backend/alembic/versions/`
- Auto-generate from model changes: `alembic revision --autogenerate -m "description"`
- Models must be imported in `alembic/env.py` for autogenerate to work

### Direct Service Call Pattern

Services are called directly from API routes without background tasks:

```python
@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile, db: Session = Depends(get_db)):
    service = DatasetService(db)
    dataset, operation_id = await service.create_from_upload(file)
    return {"dataset_id": dataset.id, "operation_id": operation_id}
```

Progress tracking happens through OperationTracker with SQLite storage.

### Odoo JSON-RPC Integration

The `OdooConnector` class wraps Odoo's JSON-RPC API:

```python
odoo = OdooConnector(url, db, username, password)
odoo.authenticate()  # Get UID

# Search and read
records = odoo.search_read("res.partner", domain=[["name", "=", "Acme"]], fields=["id", "name"])

# Create/update (upsert pattern)
odoo_id, operation = odoo.upsert("res.partner", {"name": "Acme Corp"}, "name", "Acme Corp")
```

### Transform Registry

Transforms are registered functions that clean/normalize data:

```python
from app.core.transformer import TransformRegistry

registry = TransformRegistry()
clean_phone = registry.get("phone_normalize")
result = clean_phone("+1 (555) 123-4567")  # Returns "+15551234567"
```

Available transforms: `trim`, `lower`, `upper`, `titlecase`, `phone_normalize`, `email_normalize`, `currency_to_float`, `split_name`, `concat`, `regex_extract`

## Environment Configuration

Required variables in `backend/.env`:

```bash
# Database (SQLite - no server needed)
DATABASE_URL=sqlite:///./data_migrator.db

# Odoo (configure for actual imports)
ODOO_URL=https://your-odoo.com
ODOO_DB=your_database
ODOO_USERNAME=api_user
ODOO_PASSWORD=api_password

# LLM (optional - for AI-powered header matching)
ANTHROPIC_API_KEY=sk-ant-...

# Storage
STORAGE_PATH=../storage  # For uploads/profiles/addons/exports

# Auth
SECRET_KEY=random-32-char-secret
```

## Development Commands

### Backend Setup & Development

```bash
cd backend
source venv/bin/activate  # Activate virtual environment

# Database migrations
alembic upgrade head                    # Apply all migrations
alembic revision -m "description"       # Create new migration
alembic downgrade -1                    # Rollback one migration

# Run development server
uvicorn app.main:app --reload --port 8888              # Start API (http://localhost:8888)

# Testing (when tests exist)
pytest                                  # Run all tests
pytest tests/test_file.py              # Run specific test file
pytest -v -s                           # Verbose with print output
pytest --cov=app                       # With coverage
```

### Frontend Development

```bash
cd frontend

npm run dev       # Start dev server (http://localhost:5173)
npm run build     # Build for production (TypeScript + Vite)
npm run preview   # Preview production build
npm run lint      # Run ESLint
```

### Database Setup

Uses SQLite (no server setup needed). Configure in `backend/.env`.

## Common Gotchas

- **Alembic can't find models**: Ensure models are imported in `alembic/env.py`
- **KeyMap lookups failing**: Verify parent records were imported in phase A before children in phase B
- **Odoo connection errors**: Check `ODOO_URL`, `ODOO_DB`, credentials in `.env`
- **Frontend API calls failing**: Backend must be running on port 8888, frontend expects `/api/v1` prefix
- **Storage path issues**: Ensure `storage/` directory exists with subdirs: `uploads/`, `profiles/`, `addons/`, `exports/`

## Code Style Notes

- Backend: Follow PEP 8, use type hints
- Frontend: Use TypeScript, no implicit `any` types
- Models: SQLAlchemy ORM classes in `/models`, Pydantic schemas in `/schemas`
- Async: API routes should be `async def` when using `await`
- Database sessions: Use dependency injection pattern with `get_db()` in routes

## Frontend Technology Stack

React SPA with TypeScript, React Router, Tailwind CSS:

```
/frontend/src
  /pages          # Route pages (Dashboard, DatasetDetail, etc.)
  /components     # Reusable UI components
  /services       # API client functions (axios)
  /hooks          # Custom React hooks
  /utils          # Helper functions
  /types          # TypeScript type definitions
```

State management: Zustand for global state, React Query for server state
