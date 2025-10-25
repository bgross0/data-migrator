# Disconnected Backend Features - Frontend Missing

**Date**: 2025-10-13
**Status**: Multiple backend endpoints not exposed in UI

---

## ❌ MISSING: Download Functionality

### Backend Endpoints Available:
1. **`GET /api/v1/datasets/{dataset_id}/download-cleaned`** ✅
   - Downloads cleaned CSV/XLSX file
   - Ready for Odoo import
   - Returns FileResponse with proper filename

2. **`GET /api/v1/datasets/{dataset_id}/export-for-odoo`** ✅
   - Exports JSON with:
     - Cleaned data
     - Field mappings
     - Cleaning report
     - Import instructions
   - Complete metadata package

### Frontend Status:
- ❌ **No download buttons in DatasetDetail.tsx**
- ❌ **No download buttons for split sheets**
- ❌ **No way to access cleaned data files**

---

## ❌ MISSING: Module Selection UI

### Backend Endpoints Available:
1. **`GET /api/v1/modules`** ✅
   - Lists all available Odoo modules
   - Returns name, display_name, description, icon, model_count

2. **`POST /api/v1/datasets/{dataset_id}/modules`** ✅
   - Set selected modules for dataset
   - Validates module names
   - Returns filtered model count

3. **`GET /api/v1/datasets/{dataset_id}/modules`** ✅
   - Get currently selected modules
   - Shows detected domain
   - Lists models

4. **`POST /api/v1/datasets/{dataset_id}/suggest-modules`** ✅
   - AI suggestion based on column names
   - Analyzes dataset content

### Frontend Status:
- ❌ **No module selection interface**
- ❌ **User can't filter 520+ models down to 15-20**
- ❌ **Critical feature for mapping accuracy missing**

---

## ❌ MISSING: Cleaning Report UI

### Backend Endpoints Available:
1. **`GET /api/v1/datasets/{dataset_id}/cleaning-report`** ✅
   - Shows what data was cleaned
   - Column-level transformations
   - Field mappings applied

2. **`GET /api/v1/datasets/{dataset_id}/cleaned-data`** ✅
   - Preview cleaned data
   - Paginated (limit parameter)
   - Shows before/after comparison data

### Frontend Status:
- ❌ **No cleaning report view**
- ❌ **No cleaned data preview**
- ❌ **User can't see what was transformed**

---

## ❌ MISSING: Sheet Download (Split Sheets)

### Backend Capability:
- Split sheets stored in `storage/split_sheets/`
- Files named: `dataset_{id}_{sheet_name}.csv`
- Example: `dataset_6_Contacts.csv`, `dataset_6_Vehicles.csv`

### Frontend Status:
- ❌ **No download button for individual split sheets**
- ❌ **No way to download model-specific data**
- ❌ **Critical for the MAIN USE CASE** (download per-model sheets)

---

## ⚠️ PARTIALLY CONNECTED: Transform System

### Backend Endpoints Available:
1. **`GET /api/v1/transforms/available`** ✅
2. **`POST /api/v1/mappings/{mapping_id}/transforms`** ✅
3. **`PUT /api/v1/transforms/{transform_id}`** ✅
4. **`DELETE /api/v1/transforms/{transform_id}`** ✅
5. **`POST /api/v1/transforms/test`** ✅
6. **`POST /api/v1/transforms/{transform_id}/reorder`** ✅

### Frontend Status:
- ✅ **Has TransformModal.tsx**
- ❓ **Unknown if fully wired** (need to verify)

---

## ⚠️ PARTIALLY CONNECTED: Custom Fields

### Backend Endpoints Available:
1. **`POST /api/v1/datasets/{dataset_id}/create-custom-fields`** ✅
2. **`POST /api/v1/datasets/{dataset_id}/addon/generate`** ✅
3. **`GET /api/v1/datasets/{dataset_id}/addon/instructions`** ✅

### Frontend Status:
- ✅ **Has CustomFieldModal.tsx**
- ❓ **Unknown if fully wired** (need to verify)

---

## ✅ CONNECTED: Import System

### Backend Endpoints:
1. **`POST /api/v1/datasets/{dataset_id}/runs`** ✅
2. **`GET /api/v1/runs`** ✅
3. **`GET /api/v1/runs/{run_id}`** ✅
4. **`POST /api/v1/runs/{run_id}/rollback`** ✅

### Frontend Status:
- ✅ **Has Import.tsx page**
- ✅ **Has Runs.tsx page**
- ✅ **Fully connected**

---

## ✅ CONNECTED: Odoo Connections

### Backend Endpoints:
1. **`POST /api/v1/odoo/connections`** ✅
2. **`GET /api/v1/odoo/connections`** ✅
3. **`GET /api/v1/odoo/connections/{connection_id}`** ✅
4. **`DELETE /api/v1/odoo/connections/{connection_id}`** ✅
5. **`POST /api/v1/odoo/test-connection`** ✅

### Frontend Status:
- ✅ **Has OdooConnectionModal.tsx**
- ✅ **Fully connected**

---

## PRIORITY FIXES NEEDED

### 🔴 CRITICAL (Core Use Case Broken):
1. **Add download button for split sheets**
   - User uploads mixed data
   - System splits by model
   - **User can't download the results!!!**

2. **Add module selection UI**
   - Without this, mapping accuracy is terrible (520 models instead of 15-20)
   - Backend is ready, just needs frontend

### 🟡 HIGH (User Experience):
3. **Add cleaned data download button**
   - `/datasets/{id}/download-cleaned` endpoint exists
   - Just needs a button in DatasetDetail.tsx

4. **Add cleaning report viewer**
   - Show what transformations were applied
   - Transparency for data changes

### 🟢 MEDIUM (Nice to Have):
5. **Verify TransformModal is fully wired**
6. **Verify CustomFieldModal is fully wired**

---

## Recommended Implementation Order

1. **Add Download Buttons** (30 min)
   - Add "Download Cleaned Data" button to DatasetDetail.tsx
   - Add "Download" button to each sheet in sheet list

2. **Add Module Selector** (2 hours)
   - Create ModuleSelector.tsx component (already exists, verify integration)
   - Wire up to datasets/{id}/modules endpoints
   - Show before uploading or right after profiling

3. **Add Cleaning Report Viewer** (1 hour)
   - Create CleaningReport.tsx component
   - Show transformations applied
   - Link from DatasetDetail.tsx

4. **Add Split Sheet Downloads** (1 hour)
   - Modify sheet display to show download icon
   - Handle FileResponse from backend

---

**Total Disconnected Backend Code**: ~8-10 API endpoints not exposed in UI
**Impact**: Major features invisible to users despite being implemented
