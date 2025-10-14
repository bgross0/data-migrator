# Data Migrator - Execution Flows

This document traces critical user workflows through the codebase with file paths, line numbers, and decision points.

**Purpose**: Enable AI agents to understand execution paths and make informed changes.

---

## Table of Contents

1. [Flow 1: Upload → Profile → Map](#flow-1-upload--profile--map)
2. [Flow 2: Module Selection Impact](#flow-2-module-selection-impact)
3. [Flow 3: Deterministic Mapping Generation](#flow-3-deterministic-mapping-generation)
4. [Flow 4: Lambda Transformation Generation](#flow-4-lambda-transformation-generation)
5. [Flow 5: Two-Phase Odoo Import](#flow-5-two-phase-odoo-import)
6. [Common Patterns](#common-patterns)
7. [Troubleshooting](#troubleshooting)

---

## Flow 1: Upload → Profile → Map

**User Action**: Uploads an Excel file, waits for profiling, generates mappings

### Step 1: File Upload
```
📍 frontend/src/pages/Upload.tsx:45
   User clicks "Upload" button

↓  POST /api/v1/datasets (multipart/form-data)

📍 backend/app/api/datasets.py:23
   async def create_dataset(file: UploadFile, name: str, db: Session)

↓  Calls DatasetService

📍 backend/app/services/dataset_service.py:42
   def create_dataset(self, file, name):
       1. Save file to storage/uploads/
       2. Create SourceFile record in DB
       3. Create Dataset record in DB
       4. Detect file type (Excel/CSV)
       5. Read sheet names
       6. Create Sheet records for each sheet
       7. Return Dataset object
```

**Database Writes**:
- `source_files`: New file record
- `datasets`: New dataset record
- `sheets`: One record per sheet in file

### Step 2: Profile Dataset (Async)
```
📍 frontend/src/pages/DatasetDetail.tsx:78
   useEffect() triggers profiling automatically

↓  POST /api/v1/datasets/{id}/profile

📍 backend/app/api/datasets.py:67
   async def profile_dataset(dataset_id: int, db: Session)

↓  Triggers Celery task

📍 backend/app/services/profiler_tasks.py:18
   @celery.task
   def profile_dataset(dataset_id: int):
       1. Load dataset from DB
       2. Read file (Excel/CSV) → Polars DataFrame
       3. For each sheet:
          a. For each column:
             - Detect data type (int, float, string, date, etc.)
             - Calculate statistics (null%, unique%, cardinality)
             - Detect patterns (email, phone, currency, etc.)
             - Extract sample values
             - Create ColumnProfile record
       4. Update dataset.profiling_status = "complete"
       5. Commit to database

```

**Database Writes**:
- `column_profiles`: One record per column (e.g., 16 columns = 16 records)
- `datasets`: Update `profiling_status = "complete"`

**Performance**: 401,330 rows/second (Polars-based)

### Step 3: User Selects Modules (Optional but Recommended)
```
📍 frontend/src/pages/DatasetDetail.tsx:120
   User clicks ModuleSelector component

📍 frontend/src/components/ModuleSelector.tsx:56
   toggleModule(moduleName):
       Updates selectedModules array

↓  PATCH /api/v1/datasets/{id}

📍 backend/app/api/datasets.py:45
   Update dataset.selected_modules = ["sales_crm", "contacts"]
```

**Database Writes**:
- `datasets`: Update `selected_modules` JSON field

**Impact**: Reduces search space from 9,947 fields → ~500 fields (10x improvement)

### Step 4: Generate Mappings
```
📍 frontend/src/pages/Mappings.tsx:93
   User clicks "Generate Mappings" button

↓  POST /api/v1/datasets/{id}/mappings/generate?use_deterministic=true

📍 backend/app/api/mappings.py:54
   async def generate_mappings(dataset_id: int, use_deterministic: bool = True, db: Session)
       Calls MappingService.generate_mappings_v2()

... (See Flow 3 for detailed mapping generation flow)
```

---

## Flow 2: Module Selection Impact

**How module selection constrains field matching for better accuracy**

### Step 1: Module Selection Stored
```
📍 frontend/src/components/ModuleSelector.tsx:56-62
   User toggles module checkboxes
   → Updates Dataset.selected_modules

Example:
  selected_modules = ["sales_crm", "contacts"]
```

### Step 2: Module Filtering in Mapping Generation
```
📍 backend/app/services/mapping_service.py:162-164
   selected_modules = dataset.selected_modules if hasattr(dataset, 'selected_modules') else None
   if selected_modules:
       print(f"🎯 Using selected modules for mapping: {selected_modules}")

↓  Passed to field mapper

📍 backend/app/services/mapping_service.py:211-214
   sheet_mappings = self.deterministic_mapper.map_dataframe(
       df,
       sheet_name=sheet.name,
       selected_modules=selected_modules  # ← Module constraint
   )
```

### Step 3: Module Registry Filtering
```
📍 backend/app/field_mapper/main.py:230-232
   def map_dataframe(self, df: pl.DataFrame, sheet_name: str = "Data",
                     selected_modules: Optional[List[str]] = None):

↓  Passes to matching pipeline

📍 backend/app/field_mapper/matching/matching_pipeline.py:194-200
   def match_sheet(self, column_profiles, sheet_name, selected_modules):
       target_models = None
       if selected_modules:
           logger.info(f"Using pre-selected modules: {selected_modules}")
           from ..core.module_registry import get_module_registry
           registry = get_module_registry()
           target_models = registry.get_models_for_groups(selected_modules)
           logger.info(f"Module selection provides {len(target_models)} models")
```

### Step 4: Model Registry Lookup
```
📍 backend/app/field_mapper/core/module_registry.py:390-402
   def get_models_for_groups(self, group_names: List[str]) -> Set[str]:
       """Get all models for the specified groups."""
       models = set()
       for group_name in group_names:
           group = self.get_group(group_name)
           if group:
               models.update(group.models)
       return models

Example:
  Input: ["sales_crm", "contacts"]
  Output: {
      "sale.order", "sale.order.line", "crm.lead", "crm.team",
      "res.partner", "res.users", ...
  }
  Total: ~36 models (instead of 520)
```

### Step 5: Filtering Applied to Knowledge Base
```
📍 backend/app/field_mapper/matching/matching_pipeline.py:206-210
   if target_models:
       candidate_models = candidate_models & target_models
       logger.info(f"After module filtering: {len(candidate_models)} candidate models")

Result:
  - Knowledge base searches limited to target_models only
  - All 8 strategies work within constrained space
  - Confidence scores improve by 15-30%
```

**Quantitative Impact**:
- Before: 520 models, 9,947 fields
- After (sales_crm + contacts): 36 models, ~480 fields
- **10x reduction in search space**
- **15-30% confidence boost**

---

## Flow 3: Deterministic Mapping Generation

**The main mapping pipeline using odoo-dictionary**

### Phase A: Setup
```
📍 backend/app/api/mappings.py:54-68
   POST /api/v1/datasets/{id}/mappings/generate

   async def generate_mappings(dataset_id, use_deterministic=True, db):
       service = MappingService(db)
       mappings = await service.generate_mappings_v2(dataset_id, use_deterministic)
       return {"mappings": [...]}
```

### Phase B: Load Data
```
📍 backend/app/services/mapping_service.py:137-166
   async def generate_mappings_v2(self, dataset_id, use_deterministic=True):

       # Delete old mappings
       self.db.query(Mapping).filter(Mapping.dataset_id == dataset_id).delete()
       self.db.commit()

       # Load dataset + sheets
       dataset = self.db.query(Dataset).options(
           joinedload(Dataset.source_file),
           joinedload(Dataset.sheets)
       ).filter(Dataset.id == dataset_id).first()

       # Check for module selection
       selected_modules = dataset.selected_modules if hasattr(dataset, 'selected_modules') else None
       if selected_modules:
           print(f"🎯 Using selected modules for mapping: {selected_modules}")
```

### Phase C: Process Each Sheet
```
📍 backend/app/services/mapping_service.py:169-206
   for sheet in dataset.sheets:
       # Prefer cleaned data over raw data
       if dataset.cleaned_file_path and Path(dataset.cleaned_file_path).exists():
           file_path = Path(dataset.cleaned_file_path)
       else:
           file_path = Path(dataset.source_file.path)

       # Read file → Polars DataFrame
       if is_excel:
           df = pl.read_excel(file_path, sheet_name=sheet.name)
       elif is_csv:
           df = pl.read_csv(file_path)

       # Call field mapper
       sheet_mappings = self.deterministic_mapper.map_dataframe(
           df,
           sheet_name=sheet.name,
           selected_modules=selected_modules
       )
```

### Phase D: Field Mapper Entry Point
```
📍 backend/app/field_mapper/main.py:218-249
   def map_dataframe(self, df: pl.DataFrame, sheet_name: str = "Data",
                     selected_modules: Optional[List[str]] = None):

       logger.info(f"Mapping dataframe with {len(df.columns)} columns")

       # Profile all columns
       profiles = self.profiler.profile_dataframe(df, sheet_name=sheet_name)

       logger.info(f"Profiled {len(profiles)} columns")

       # Match columns to fields
       result = self.pipeline.match_sheet(
           column_profiles=profiles,
           sheet_name=sheet_name,
           selected_modules=selected_modules
       )

       return result  # Dict[column_name, List[FieldMapping]]
```

### Phase E: Column Profiling
```
📍 backend/app/field_mapper/profiling/column_profiler.py:103-149
   def profile_dataframe(self, df: pl.DataFrame, sheet_name: str = "Sheet1"):
       """Profile all columns in a Polars DataFrame."""
       profiles = []

       for column_name in df.columns:
           data = df[column_name]
           profile = self.profile_column(column_name, data, sheet_name)
           profiles.append(profile)

       return profiles

   def profile_column(self, column_name: str, data: pl.Series, sheet_name: str):
       """Profile a single column."""
       clean_data = data.drop_nulls()

       # Detect data type
       dtype = self._detect_type(clean_data)

       # Calculate statistics
       null_count = len(data) - len(clean_data)
       null_percentage = (null_count / len(data)) * 100 if len(data) > 0 else 0
       unique_count = clean_data.n_unique()
       cardinality = unique_count / len(data) if len(data) > 0 else 0

       # Detect patterns
       patterns = self._detect_patterns(clean_data, dtype)

       # Extract samples
       samples = self._get_samples(clean_data, n=10)

       return ColumnProfile(
           column_name=column_name,
           sheet_name=sheet_name,
           detected_type=dtype,
           null_percentage=null_percentage,
           unique_count=unique_count,
           cardinality=cardinality,
           patterns=patterns,
           sample_values=samples
       )
```

**Performance**: 401,330 rows/second

### Phase F: Matching Pipeline
```
📍 backend/app/field_mapper/matching/matching_pipeline.py:174-249
   def match_sheet(self, column_profiles, sheet_name, selected_modules):

       # If modules are pre-selected, get the associated models
       target_models = None
       if selected_modules:
           from ..core.module_registry import get_module_registry
           registry = get_module_registry()
           target_models = registry.get_models_for_groups(selected_modules)

       # Detect candidate models from all columns
       candidate_models = self._detect_candidate_models(column_profiles)

       # If we have selected modules, constrain candidate models
       if target_models:
           candidate_models = candidate_models & target_models

       # Match each column
       results = {}
       for col_profile in column_profiles:
           mappings = self.match_column(
               column_profile=col_profile,
               all_column_profiles=column_profiles,
               target_models=target_models,  # ← Module constraint
               candidate_models=candidate_models,
           )
           results[col_profile.column_name] = mappings

       # Generate lambda suggestions (heuristics)
       lambda_mappings = self._generate_lambda_suggestions(column_profiles, results)
       if lambda_mappings:
           results.update(lambda_mappings)

       return results
```

### Phase G: Match Single Column (8 Strategies)
```
📍 backend/app/field_mapper/matching/matching_pipeline.py:77-172
   def match_column(self, column_profile, all_column_profiles, target_models, candidate_models):

       # Create matching context
       context = MatchingContext(
           knowledge_base=self.knowledge_base,
           column_profile=column_profile,
           all_column_profiles=all_column_profiles,
           target_models=target_models,  # ← Used by strategies
           candidate_models=candidate_models,
           sheet_name=column_profile.sheet_name,
       )

       # Run all 8 strategies in parallel
       all_candidates: List[FieldMapping] = []
       for strategy in self.strategies:
           try:
               candidates = strategy.match(context)
               all_candidates.extend(candidates)
           except Exception as e:
               logger.error(f"Error in strategy {strategy.name}: {e}")

       # Merge duplicates (same model+field from multiple strategies)
       merged_candidates = self._merge_duplicates(all_candidates)

       # Apply model priority (boost/penalize based on context)
       merged_candidates = self._apply_model_priority(
           merged_candidates,
           candidate_models,
           column_profile
       )

       # Rank by confidence
       ranked_candidates = self._rank_candidates(merged_candidates)

       # Filter by confidence threshold (default: 0.5)
       filtered_candidates = [
           m for m in ranked_candidates
           if m.confidence >= self.settings.confidence_threshold
       ]

       # Return top N (default: 5)
       return filtered_candidates[:max_results]
```

**8 Strategies**:
1. `ExactNameMatchStrategy`: Exact field name match
2. `LabelMatchStrategy`: Matches field labels
3. `SelectionValueMatchStrategy`: Matches cell values to selection options
4. `DataTypeCompatibilityStrategy`: Type compatibility
5. `PatternMatchStrategy`: Pattern-based (email, phone, etc.)
6. `FuzzyMatchStrategy`: Fuzzy string matching
7. `ContextualMatchStrategy`: Uses context from other columns
8. `StatisticalSimilarityStrategy`: Statistical distribution matching

### Phase H: Store Mappings in Database
```
📍 backend/app/services/mapping_service.py:217-243
   # Create mapping records for each column
   for column_name, field_mappings in sheet_mappings.items():
       if not field_mappings:
           continue

       # Get top suggestion
       top_mapping = field_mappings[0]

       # Create mapping record
       mapping = Mapping(
           dataset_id=dataset_id,
           sheet_id=sheet.id,
           header_name=column_name,
           target_model=top_mapping.target_model,
           target_field=top_mapping.target_field,
           confidence=float(top_mapping.confidence),
           status=MappingStatus.PENDING,  # User hasn't confirmed yet
           chosen=False,
           rationale=top_mapping.rationale,
       )
       self.db.add(mapping)
       self.db.flush()  # Get mapping ID

       # Store alternatives as suggestions (top 5)
       candidates = [
           {
               "model": fm.target_model,
               "field": fm.target_field,
               "confidence": float(fm.confidence),
               "method": fm.matching_strategy,
               "rationale": fm.rationale
           }
           for fm in field_mappings[:5]
       ]

       suggestion = Suggestion(
           mapping_id=mapping.id,
           candidates=candidates
       )
       self.db.add(suggestion)

   self.db.commit()
```

**Database Writes**:
- `mappings`: One record per column (e.g., 16 columns = 16 mappings)
- `suggestions`: One record per mapping (contains top 5 alternatives)

**Result**: User sees suggested mappings in UI for review/confirmation

---

## Flow 4: Lambda Transformation Generation

**Heuristic detection of opportunities to combine columns**

### Detection Trigger
```
📍 backend/app/field_mapper/matching/matching_pipeline.py:238-248
   def match_sheet(self, column_profiles, sheet_name, selected_modules):
       # ... after matching all columns ...

       # Generate lambda suggestions (heuristics)
       lambda_mappings = self._generate_lambda_suggestions(
           column_profiles,
           results
       )
       if lambda_mappings:
           logger.info(f"Generated {len(lambda_mappings)} lambda-based mapping suggestion(s)")
           results.update(lambda_mappings)

       return results
```

### Lambda Detection Logic
```
📍 backend/app/field_mapper/matching/matching_pipeline.py:251-310
   def _generate_lambda_suggestions(self, column_profiles, existing_results):
       """
       Create heuristic lambda mapping suggestions based on available columns.

       Currently supports combining first/last name style columns into res.partner.name.
       """
       suggestions = {}

       # Get column names
       column_names = [profile.column_name for profile in column_profiles]

       # Look for first name columns
       first_name_cols = [
           name for name in column_names
           if self._looks_like_first_name(name)
       ]

       # Look for last name columns
       last_name_cols = [
           name for name in column_names
           if self._looks_like_last_name(name)
       ]

       # If we have both, create lambda suggestion
       if not first_name_cols or not last_name_cols:
           return suggestions

       first_col = first_name_cols[0]
       last_col = last_name_cols[0]
       virtual_column = "lambda_name"

       # Avoid duplicates
       if virtual_column in existing_results or virtual_column in suggestions:
           return suggestions

       # Generate lambda function
       lambda_fn = (
           "lambda self, row, **kwargs: (' '.join("
           f"str(part).strip() for part in (row.get('{first_col}'), row.get('{last_col}')) if part"
           ")) or None"
       )

       # Create FieldMapping with lambda metadata
       mapping = FieldMapping(
           source_column=virtual_column,
           target_model="res.partner",
           target_field="name",
           confidence=0.85,  # Heuristic confidence
           scores={"lambda_heuristic": 0.85},
           rationale=(
               f"[LambdaHeuristics] Combine '{first_col}' and '{last_col}' "
               "into res.partner name"
           ),
           matching_strategy="LambdaHeuristics",
           alternatives=[],
           transformations=[],
           mapping_type="lambda",
           lambda_function=lambda_fn,
           lambda_dependencies=[first_col, last_col],
       )

       suggestions[virtual_column] = [mapping]
       return suggestions
```

### Detection Helpers
```
📍 backend/app/field_mapper/matching/matching_pipeline.py:312-323
   def _normalize_header(value: str) -> str:
       """Normalize a column header for rule-based detection."""
       return value.lower().replace("_", " ").strip()

   def _looks_like_first_name(self, value: str) -> bool:
       normalized = self._normalize_header(value)
       return "first" in normalized and "name" in normalized

   def _looks_like_last_name(self, value: str) -> bool:
       normalized = self._normalize_header(value)
       return "last" in normalized and "name" in normalized
```

**Example**:

Input columns:
- `First Name`: ["John", "Jane", "Bob"]
- `Last Name`: ["Doe", "Smith", "Johnson"]

Detected lambda mapping:
- Virtual column: `lambda_name`
- Target: `res.partner.name`
- Lambda: `lambda self, row, **kwargs: ' '.join([row['First Name'], row['Last Name']])`
- Dependencies: `["First Name", "Last Name"]`

**Result**: Virtual mapping appears in UI, user can confirm to combine columns

---

## Flow 5: Two-Phase Odoo Import

**How parent/child relationships are resolved during import**

### Phase 1: Build Import Graph
```
📍 backend/app/services/import_service.py:45-78
   def execute_import(self, dataset_id: int, connection_id: int):
       # Load import graph (topological sort)
       graph = ImportGraph.from_default()

       # Topological order (parents before children):
       # 1. res.partner (customers/vendors) - NO dependencies
       # 2. crm.lead - depends on res.partner
       # 3. product.product - NO dependencies
       # 4. project.project - depends on res.partner
       # 5. project.task - depends on project.project
       # 6. sale.order - depends on res.partner
       # 7. sale.order.line - depends on sale.order, product.product
       # 8. account.move - accounting entries
```

### Phase 2: Group Mappings by Model
```
📍 backend/app/services/import_service.py:82-95
   # Group mappings by target model
   mappings_by_model = defaultdict(list)

   for sheet in dataset.sheets:
       for mapping in sheet.mappings:
           if mapping.chosen and mapping.status == MappingStatus.CONFIRMED:
               mappings_by_model[mapping.target_model].append(mapping)
```

### Phase 3: Import Each Model in Order
```
📍 backend/app/importers/executor.py:22-50
   def execute(self, graph: List[str], data: Dict[str, List[Dict]]):
       """Execute import according to graph order."""
       stats = {"created": 0, "updated": 0, "errors": 0, "by_model": {}}

       for model in graph:
           if model not in data:
               continue

           model_stats = self._import_model(model, data[model])
           stats["created"] += model_stats["created"]
           stats["updated"] += model_stats["updated"]
           stats["errors"] += model_stats["errors"]
           stats["by_model"][model] = model_stats

       return stats
```

### Phase 4: Import Single Model (with KeyMap)
```
📍 backend/app/importers/executor.py:52-84
   def _import_model(self, model: str, records: List[Dict]):
       """Import records for a single model."""
       stats = {"created": 0, "updated": 0, "errors": 0}

       for record in records:
           try:
               # CRITICAL: Resolve foreign keys using KeyMap
               resolved = self._resolve_relationships(model, record)

               # Upsert to Odoo
               lookup_field = self._get_lookup_field(model, record)
               lookup_value = record.get(lookup_field)

               odoo_id, operation = self.odoo.upsert(
                   model,
                   resolved,
                   lookup_field,
                   lookup_value,
               )

               # CRITICAL: Store in KeyMap for children to lookup
               self._store_keymap(model, record, odoo_id)

               if operation == "create":
                   stats["created"] += 1
               else:
                   stats["updated"] += 1

           except Exception as e:
               stats["errors"] += 1
               # TODO: Log error to RunLog

       return stats
```

### Phase 5: Resolve Foreign Keys via KeyMap
```
📍 backend/app/importers/executor.py:86-142
   def _resolve_relationships(self, model: str, record: Dict) -> Dict:
       """
       Resolve foreign key references using KeyMap.

       For fields ending in '_id', looks up the Odoo ID from KeyMap
       based on the source value and replaces it.
       """
       resolved = record.copy()

       # Common relationship field mappings
       relationship_mappings = {
           "partner_id": "res.partner",
           "user_id": "res.users",
           "product_id": "product.product",
           "project_id": "project.project",
           "order_id": "sale.order",
           # ... etc
       }

       for field_name, value in record.items():
           # Check if this is a relationship field
           if field_name.endswith("_id") and value:
               # Determine parent model
               parent_model = relationship_mappings.get(field_name)

               if not parent_model:
                   continue

               # Look up in KeyMap
               keymap = self.db.query(KeyMap).filter(
                   KeyMap.run_id == self.run.id,
                   KeyMap.model == parent_model,
                   KeyMap.source_key == str(value)
               ).first()

               if keymap and keymap.odoo_id:
                   # REPLACE with Odoo ID
                   resolved[field_name] = keymap.odoo_id
               else:
                   # Parent not found - keep original value
                   pass

       return resolved
```

### Phase 6: Store KeyMap Entry
```
📍 backend/app/importers/executor.py:154-168
   def _store_keymap(self, model: str, record: Dict, odoo_id: int):
       """Store source key -> Odoo ID mapping."""
       source_key = record.get("external_id") or record.get("email") or record.get("name")
       if not source_key:
           return

       keymap = KeyMap(
           run_id=self.run.id,
           model=model,
           source_key=str(source_key),
           odoo_id=odoo_id,
           xml_id=f"axsys.{model.replace('.', '_')}.{source_key}",
       )
       self.db.add(keymap)
       self.db.commit()
```

**Example Scenario**:

**Phase A: Import Parents**
```
Spreadsheet row: {"Customer Name": "Acme Corp", "Email": "info@acme.com"}

1. Import to res.partner
2. Odoo returns: id=42
3. Store KeyMap:
   KeyMap(
       model="res.partner",
       source_key="Acme Corp",
       odoo_id=42
   )
```

**Phase B: Import Children**
```
Spreadsheet row: {"Project Name": "Website Redesign", "Customer Name": "Acme Corp"}

1. Before import, lookup "Acme Corp" in KeyMap
2. KeyMap returns: odoo_id=42
3. Resolve: {"name": "Website Redesign", "partner_id": 42}
4. Import to project.project with partner_id=42
```

**Result**: Relationships correctly established without manual ID management

---

## Common Patterns

### Pattern 1: Database Transaction Pattern
```python
# All service methods use this pattern
def some_service_method(self):
    try:
        # 1. Query data
        record = self.db.query(Model).filter(...).first()

        # 2. Modify data
        record.field = new_value
        self.db.add(record)

        # 3. Commit
        self.db.commit()

        # 4. Refresh (reload from DB)
        self.db.refresh(record)

        return record
    except Exception as e:
        # Rollback on error
        self.db.rollback()
        raise
```

### Pattern 2: Celery Async Task Pattern
```python
# Long operations run as Celery tasks

# Define task
@celery.task
def profile_dataset(dataset_id: int):
    # Long-running work...
    pass

# Trigger task (non-blocking)
task = profile_dataset.delay(dataset_id)

# Return task ID to frontend
return {"task_id": task.id, "status": "processing"}

# Frontend polls for completion
GET /api/v1/tasks/{task_id}/status
```

### Pattern 3: Polars → Pandas Conversion (Legacy)
```python
# Old code (being phased out)
pandas_df = polars_df.to_pandas()

# New code (pure Polars)
result = polars_df.select([...])  # All operations in Polars
```

---

## Troubleshooting

### Issue: "No mappings generated"

**Possible Causes**:
1. Profiling didn't complete → Check `dataset.profiling_status`
2. Module selection too restrictive → Try without modules first
3. Confidence threshold too high → Lower in settings
4. Knowledge base not loaded → Check logs for "Knowledge base loaded"

**Debug Flow**:
```
1. Check dataset.profiling_status in database
2. Check if column_profiles exist for sheets
3. Check mapping generation logs for errors
4. Try without module selection
5. Check field_mapper logs for strategy execution
```

### Issue: "Low confidence mappings"

**Possible Causes**:
1. Column names don't match Odoo field names
2. No module selection (too broad search space)
3. Unusual data patterns

**Solutions**:
1. Use module selection to constrain search space (+15-30% confidence)
2. Rename columns to match Odoo conventions
3. Use custom field generation for truly unique fields

### Issue: "Import fails with foreign key errors"

**Possible Causes**:
1. Import graph order incorrect (children before parents)
2. KeyMap lookup failed (parent not imported)
3. Incorrect relationship field mapping

**Debug Flow**:
```
1. Check ImportGraph topological order
2. Verify parent model imported successfully
3. Check KeyMap table for parent entries
4. Verify relationship_mappings in executor.py
```

### Issue: "FastExcel not found error"

**Solution**:
```bash
# Install fastexcel for Polars Excel reading
pip install fastexcel

# Or use fallback (automatic):
# System will try: fastexcel → openpyxl → pandas
```

---

## Performance Metrics

- **Column Profiling**: 401,330 rows/second (Polars)
- **Module Filtering**: 10x field reduction (9,947 → 500)
- **Confidence Boost**: +15-30% with module selection
- **Matching Time**: ~100ms per column (all 8 strategies)
- **Typical Dataset**: 5-30 seconds for 100 columns

---

**Last Updated**: 2025-10-14
**Generated for**: AI Agent Context
