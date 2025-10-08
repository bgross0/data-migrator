# Setup Instructions

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+

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
# Edit .env with your database and Redis URLs

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### Start Celery Worker (in separate terminal)

```bash
cd backend
source venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
```

### Start Celery Flower (monitoring, optional)

```bash
celery -A app.core.celery_app flower --port=5555
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

### Create PostgreSQL Database

```sql
CREATE DATABASE data_migrator;
CREATE USER data_migrator_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE data_migrator TO data_migrator_user;
```

Update your `backend/.env` file:
```
DATABASE_URL=postgresql://data_migrator_user:your_password@localhost:5432/data_migrator
```

### Run Migrations

```bash
cd backend
alembic upgrade head
```

## Redis Setup

If not installed:

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
```

### macOS
```bash
brew install redis
brew services start redis
```

### Verify Redis
```bash
redis-cli ping
# Should return: PONG
```

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
uvicorn app.main:app --reload
```

Terminal 2 - Celery Worker:
```bash
cd backend
source venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
```

Terminal 3 - Frontend:
```bash
cd frontend
npm run dev
```

Visit http://localhost:5173

## Architecture Overview

```
┌─────────────┐          ┌──────────────┐          ┌─────────┐
│   React     │  HTTP    │   FastAPI    │  Tasks   │ Celery  │
│  Frontend   ├─────────>│   Backend    ├─────────>│ Workers │
│             │          │              │          │         │
└─────────────┘          └──────┬───────┘          └────┬────┘
                                │                        │
                                v                        v
                         ┌──────────────┐        ┌──────────┐
                         │  PostgreSQL  │        │  Redis   │
                         │   Database   │        │  Queue   │
                         └──────────────┘        └──────────┘
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
- Ensure PostgreSQL is running: `pg_isready`
- Ensure Redis is running: `redis-cli ping`

### Frontend won't start
- Delete node_modules and run `npm install` again
- Check for port conflicts on 5173

### Celery worker errors
- Ensure Redis is running
- Check REDIS_URL in .env matches your Redis setup
