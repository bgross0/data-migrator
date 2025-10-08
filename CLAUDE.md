# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Data Migrator is an intelligent data migration platform for importing messy spreadsheets into Odoo with automated column mapping, relationship resolution, and custom field generation. It uses a FastAPI backend with Celery workers, a React frontend, and integrates with Odoo via JSON-RPC.

**Stack**: FastAPI + Celery + SQLAlchemy + Postgres + Redis + React + Vite + Tailwind CSS

## Development Commands

### Backend Setup & Development

```bash
cd backend
source venv/bin/activate  # Activate virtual environment

# Database migrations
alembic upgrade head                    # Apply all migrations
alembic revision -m "description"       # Create new migration
alembic downgrade -1                    # Rollback one migration

# Run development servers
uvicorn app.main:app --reload --port 8000              # Start API (http://localhost:8000)
celery -A app.core.celery_app worker --loglevel=info   # Start Celery worker (separate terminal)
celery -A app.core.celery_app flower --port=5555       # Start Flower monitoring (optional)

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

Requires PostgreSQL 15+ and Redis 7+. Configure in `backend/.env`:

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/data_migrator
REDIS_URL=redis://localhost:6379/0
```

## Architecture & Data Flow

### Core Import Pipeline

1. **Upload & Profile** → User uploads spreadsheet → Celery task analyzes columns (data types, patterns, quality metrics)
2. **Match & Map** → HeaderMatcher suggests Odoo field mappings using exact/fuzzy/AI matching
3. **Transform** → Apply data cleaning rules (trim, normalize phones/emails, split names, etc.)
4. **Resolve Relationships** → ImportGraph determines topological order (parents before children)
5. **Two-Phase Import** → TwoPhaseImporter executes:
   - Phase A: Import parent entities, build KeyMap (source_value → odoo_id)
   - Phase B: Import children using KeyMap for foreign key resolution
6. **Audit & Rollback** → Run tracking with logs; selective rollback via KeyMap

### Backend Module Organization

```
/backend/app
  /core
    profiler.py        # Column analysis (dtype detection, quality metrics)
    matcher.py         # Header → Odoo field mapping (exact/fuzzy/AI)
    transformer.py     # Data cleaning transform registry
    field_detector.py  # Field type and validation detection
    celery_app.py      # Celery configuration
    config.py          # Settings (loads from .env)
    database.py        # SQLAlchemy session management

  /importers
    graph.py           # Topological sort for entity dependencies
    executor.py        # TwoPhaseImporter - orchestrates import phases

  /connectors
    odoo.py            # OdooConnector - JSON-RPC client for Odoo API
    csv_export.py      # CSV fallback export connector

  /generators
    addon_generator.py # Generates Odoo addon ZIPs for custom fields

  /services              # Business logic layer
    dataset_service.py   # Dataset CRUD
    mapping_service.py   # Mapping CRUD + match suggestions
    transform_service.py # Transform application
    import_service.py    # Import orchestration
    profiler_tasks.py    # Celery tasks for profiling
    import_tasks.py      # Celery tasks for imports

  /api                 # FastAPI route handlers
    datasets.py        # /api/v1/datasets
    sheets.py          # /api/v1/sheets
    mappings.py        # /api/v1/mappings
    transforms.py      # /api/v1/transforms
    imports.py         # /api/v1/imports
    addons.py          # /api/v1/addons
    odoo.py            # /api/v1/odoo

  /models              # SQLAlchemy ORM models
    source.py          # Dataset, Sheet
    profile.py         # SheetProfile, ColumnProfile
    mapping.py         # Mapping, FieldMapping
    run.py             # Run, RunLog, KeyMap, ImportGraph
    odoo_connection.py # OdooConnection

  /schemas             # Pydantic models for API serialization
```

### KeyMap System

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

### Default Import Graph

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

### Celery Task Pattern

Tasks are defined in `/services/*_tasks.py` and registered with Celery:

```python
from app.core.celery_app import celery

@celery.task
def profile_dataset(dataset_id: int):
    # Long-running profiling work
    pass
```

API routes trigger tasks asynchronously:

```python
task = profile_dataset.delay(dataset_id)
return {"task_id": task.id}
```

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
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/data_migrator

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

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

## Frontend Architecture

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

## Development Workflow

1. Make schema changes in `/backend/app/models/*.py`
2. Generate migration: `cd backend && ./venv/bin/alembic revision --autogenerate -m "description"`
3. Review and edit generated migration in `alembic/versions/`
4. Apply migration: `./venv/bin/alembic upgrade head`
5. Update Pydantic schemas in `/backend/app/schemas/*.py` if needed
6. Update API routes in `/backend/app/api/*.py`
7. Update frontend services/types as needed

## Common Gotchas

- **Celery not picking up tasks**: Restart the Celery worker after code changes
- **Alembic can't find models**: Ensure models are imported in `alembic/env.py`
- **KeyMap lookups failing**: Verify parent records were imported in phase A before children in phase B
- **Odoo connection errors**: Check `ODOO_URL`, `ODOO_DB`, credentials in `.env`
- **Frontend API calls failing**: Backend must be running on port 8000, frontend expects `/api/v1` prefix
- **Storage path issues**: Ensure `storage/` directory exists with subdirs: `uploads/`, `profiles/`, `addons/`, `exports/`

## Code Style Notes

- Backend: Follow PEP 8, use type hints
- Frontend: Use TypeScript, no implicit `any` types
- Models: SQLAlchemy ORM classes in `/models`, Pydantic schemas in `/schemas`
- Async: API routes should be `async def` when using `await`
- Database sessions: Use dependency injection pattern with `get_db()` in routes
