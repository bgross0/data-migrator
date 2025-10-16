# Data Migrator - Odoo Import Platform

Intelligent data migration tool for importing messy spreadsheets into Odoo with automated column mapping, relationship resolution, and custom field generation.

## 🤖 NEW: AI Assistant

Data Migrator now includes an **AI assistant** powered by Claude Code and MCP! Get context-aware help with:
- Field mapping suggestions based on your actual data
- Odoo model explanations
- Template recommendations
- Data quality insights

**Setup:** See [MCP_ASSISTANT_GUIDE.md](MCP_ASSISTANT_GUIDE.md) for full documentation.

## Architecture

**Backend**: FastAPI + SQLAlchemy + SQLite
**Frontend**: React + Vite + Tailwind CSS
**Data Processing**: Pandas, DuckDB, OpenPyXL
**Matching**: rapidfuzz + optional Claude LLM
**Validation**: Pandera

## Core Features

- **Automated Profiling**: Analyze spreadsheets, detect data types, quality metrics
- **Smart Mapping**: Exact, fuzzy, and AI-powered column-to-field matching
- **Relationship Resolution**: Topological import with foreign key handling via KeyMap
- **Transform Pipeline**: Trim, normalize, parse phone/email/currency, split names, etc.
- **Custom Fields**: Generate Odoo addons for missing fields
- **Odoo Integration**: JSON-RPC (primary) + CSV export (fallback)
- **Audit & Rollback**: Full run tracking with selective rollback support
- **Dry Run**: Preview imports before execution

## Project Structure

```
/backend          # FastAPI application
  /app
    /api          # REST endpoints + WebSocket
    /core         # Profiler, Matcher, Transformer
    /connectors   # Odoo JSON-RPC + CSV
    /importers    # Two-phase executor, import graph
    /generators   # Addon generator (Jinja2)
    /models       # SQLAlchemy ORM
    /schemas      # Pydantic models
    /services     # Business logic
  /tests
  /alembic        # Database migrations

/frontend         # React + Vite SPA
  /src
    /components   # Reusable UI
    /pages        # Route pages
    /services     # API clients
    /hooks        # Custom React hooks
    /utils        # Helpers

/storage          # Local object storage
  /uploads        # Uploaded spreadsheets
  /profiles       # Column profiles (JSON)
  /addons         # Generated Odoo addons (ZIP)
  /exports        # CSV exports for import

/templates        # Jinja2 templates for addon generation
```

## Quick Start

### Backend Setup

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your Postgres/Redis/Odoo credentials

# Run migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8888


```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev  # Starts on http://localhost:5173
```

## Environment Variables

```bash
# Database (SQLite - no server needed)
DATABASE_URL=sqlite:///./data_migrator.db

# Odoo (optional for dev)
ODOO_URL=https://your-odoo.com
ODOO_DB=your_db
ODOO_USERNAME=api_user
ODOO_PASSWORD=api_password

# LLM (optional for AI matching)
ANTHROPIC_API_KEY=sk-ant-...

# Storage
STORAGE_PATH=./storage
```

## Development Workflow

1. **Upload** spreadsheet via UI
2. **Profile** - automatic column analysis
3. **Map** - review/adjust suggested field mappings
4. **Relate** - configure entity relationships
5. **Transform** - apply data cleaning rules
6. **Preview** - dry-run with diff
7. **Execute** - two-phase import (parents → children)
8. **Audit** - review logs, rollback if needed

## Import Graph (Default)

1. `res.partner` (customers/vendors)
2. `crm.lead`
3. `product.template` / `product.product`
4. `project.project`
5. `project.task`
6. `sale.order` → `sale.order.line`
7. `account.move`

## Tech Stack Versions

- Python 3.12+
- Node.js 20+
- FastAPI 0.115+
- React 18+
- Vite 6+

## License

Proprietary - Axsys Engineering
