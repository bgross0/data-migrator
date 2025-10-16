# Setup Instructions

## Prerequisites

- Python 3.12+
- Node.js 20+

## Backend Setup

```bash
cd backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your Odoo settings (database is SQLite - no setup needed)

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8888
```

## Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will run on http://localhost:5173

## Database Setup

The system uses SQLite (no server setup required). The database file is automatically created when you run migrations.

### Run Migrations

```bash
cd backend
alembic upgrade head
```

This will create the `data_migrator.db` file in the backend directory with all required tables.

## Project Status

### ✅ Completed

- Monorepo structure
- FastAPI backend with models, schemas, API routes
- React frontend with Tailwind CSS
- Basic routing and navigation
- Database models for all entities
- Core service stubs (profiler, matcher, transformer, Odoo connector)
- Import executor and graph logic
- Addon generator scaffold
- Celery task definitions

### 🚧 Next Steps

1. **Database Migrations** - Create initial Alembic migration
2. **File Upload** - Implement actual file parsing with pandas/openpyxl
3. **Column Profiling** - Complete profiler.py with dtype detection, pattern matching
4. **Header Matching** - Implement fuzzy matching with rapidfuzz
5. **Transform Library** - Already implemented, needs integration
6. **Mapping UI** - Build interactive mapping interface
7. **Odoo Connector** - Test and complete metadata fetching
8. **Import Execution** - Complete two-phase import logic
9. **Testing** - Add pytest tests for all components

## Quick Start (Development)

Terminal 1 - Backend:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8888
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

Visit http://localhost:5173

## Architecture Overview

```
┌─────────────┐          ┌──────────────┐
│   React     │  HTTP    │   FastAPI    │
│  Frontend   ├─────────>│   Backend    │
│             │          │              │
└─────────────┘          └──────┬───────┘
                                │
                                v
                         ┌──────────────┐
                         │   SQLite     │
                         │   Database   │
                         └──────────────┘
                                │
                                v
                         ┌──────────────┐
                         │     Odoo     │
                         │   Instance   │
                         └──────────────┘
```

## Troubleshooting

### Backend won't start
- Check DATABASE_URL in .env
- Ensure SQLite file path is writable

### Frontend won't start
- Delete node_modules and run `npm install` again
- Check for port conflicts on 5173
