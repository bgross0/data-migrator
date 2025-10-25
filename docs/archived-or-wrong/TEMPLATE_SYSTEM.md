# Template System Implementation

## Overview

A lightweight template system has been added to guide users through Odoo 18 CE setup with pre-configured import roadmaps grouped by business area.

## What Was Built

### Backend

1. **Template JSON Files** (`backend/templates/`)
   - `sales_crm.json` - Sales & CRM workflow (12 models)
   - `projects.json` - Project Management (3 models)
   - `accounting.json` - Accounting & Invoicing (4 models)
   - `essential_setup.json` - Foundation setup (6 models)
   - `complete_migration.json` - Full migration (23 models)

2. **Pydantic Schemas** (`backend/app/schemas/template.py`)
   - `Template` - Full template definition
   - `TemplateListItem` - Summary for list views
   - `TemplateStep` - Individual workflow steps
   - `TemplateProgress` - Progress tracking
   - `TemplateMetadata` - Additional metadata

3. **Service Layer** (`backend/app/services/template_service.py`)
   - `list_templates()` - List all templates with filtering
   - `get_template()` - Get template details
   - `get_template_progress()` - Track completion
   - `instantiate_template()` - Create Graph from template
   - `get_categories()` - List template categories

4. **API Endpoints** (`backend/app/api/templates.py`)
   - `GET /api/v1/templates` - List templates (with category filter)
   - `GET /api/v1/templates/categories` - List categories
   - `GET /api/v1/templates/{id}` - Get template details
   - `GET /api/v1/templates/{id}/progress` - Get completion progress
   - `POST /api/v1/templates/{id}/instantiate` - Create graph from template

### Frontend

1. **API Client** (`frontend/src/services/api.ts`)
   - `templatesApi.list()` - Fetch templates
   - `templatesApi.get()` - Fetch template details
   - `templatesApi.getCategories()` - Fetch categories
   - `templatesApi.getProgress()` - Fetch progress
   - `templatesApi.instantiate()` - Create graph

2. **QuickStart Component** (`frontend/src/components/QuickStart.tsx`)
   - Category filtering
   - Template cards with metadata
   - Difficulty badges
   - One-click instantiation

3. **Dashboard Integration** (`frontend/src/pages/Dashboard.tsx`)
   - QuickStart section added above datasets list

## How It Works

1. **Templates Reference Existing Registry**
   - Templates are lightweight JSON files that reference models in `backend/registry/odoo.yaml`
   - No duplication of model definitions
   - Leverages existing `RegistryLoader` and validation

2. **Graph Creation**
   - When user clicks "Start Import", template is instantiated as a `Graph`
   - Creates nodes for each model in the template
   - Builds dependency edges based on registry field specs
   - Stores as `GraphSpec` in database

3. **Progress Tracking** (Future)
   - Templates can track which models have been imported
   - Dashboard shows checkmarks for completed imports
   - Suggests next logical steps

## Usage

### Starting the System

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8888

# Frontend
cd frontend
npm run dev
```

### Testing API

```bash
# List all templates
curl http://localhost:8888/api/v1/templates

# Get template details
curl http://localhost:8888/api/v1/templates/template_sales_crm

# List categories
curl http://localhost:8888/api/v1/templates/categories
```

### Using in UI

1. Navigate to Dashboard (home page)
2. See "Quick Start: Odoo 18 Setup" section
3. Filter by category or view all templates
4. Click "Start Import" on any template
5. System creates a Graph instance that can be executed

## Template Structure

Each template includes:

```json
{
  "id": "template_sales_crm",
  "name": "Sales & CRM",
  "description": "Import customers, leads...",
  "category": "sales",
  "icon": "📊",
  "estimatedTime": "15-30 minutes",
  "difficulty": "beginner",
  "prerequisites": [],
  "models": ["res.partner", "crm.lead", ...],
  "steps": [
    {
      "title": "Import Customers",
      "models": ["res.partner"],
      "description": "Import your customer database",
      "sampleHeaders": ["name", "email", "phone", ...]
    }
  ],
  "metadata": {
    "recommended_for": ["Small businesses"],
    "odoo_modules": ["crm", "sale"],
    "tags": ["sales", "crm"]
  }
}
```

## Future Enhancements

1. **Progress Tracking**
   - Query `GraphRun` table to show completed models
   - Display checkmarks on completed steps
   - Calculate % complete

2. **Sample Data**
   - Include sample CSV files for each template
   - Allow users to test with sample data

3. **Custom Templates**
   - Allow users to save their own custom templates
   - Template sharing/marketplace

4. **Guided Wizard**
   - Step-by-step wizard instead of one-click
   - Field mapping assistance per step
   - Validation at each step

5. **Dependencies**
   - Smart suggestions: "You've imported customers, ready for sales orders?"
   - Highlight missing prerequisites

## Files Modified

### Backend
- `app/main.py` - Added templates router
- `app/api/graphs.py` - Fixed syntax error

### Backend (New Files)
- `templates/*.json` - 5 template definitions
- `app/schemas/template.py` - Pydantic models
- `app/services/template_service.py` - Business logic
- `app/api/templates.py` - API endpoints

### Frontend
- `src/services/api.ts` - Added templatesApi
- `src/pages/Dashboard.tsx` - Integrated QuickStart

### Frontend (New Files)
- `src/components/QuickStart.tsx` - Template browser UI

## Architecture Benefits

✅ **Leverages Existing System**
- Uses existing `Graph`, `GraphRun`, `GraphSpec` models
- References `backend/registry/odoo.yaml` for model definitions
- No duplication of field specs or relationships

✅ **Minimal Overhead**
- Templates are simple JSON metadata files
- Service layer is ~200 lines
- API is ~100 lines
- Frontend component is ~150 lines

✅ **Extensible**
- Easy to add new templates (just add JSON file)
- Can group templates by industry vertical
- Can create template variants (e.g., "Sales for Retail" vs "Sales for B2B")

✅ **User-Friendly**
- Clear categorization by business function
- Difficulty levels guide users
- Time estimates set expectations
- Sample headers help users prepare data
