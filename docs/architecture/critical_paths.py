"""
Critical Execution Paths - Machine-Readable Architecture

This module provides structured, queryable execution paths for AI agents
to understand code flow, dependencies, and decision points programmatically.

Usage:
    from docs.architecture.critical_paths import CRITICAL_PATHS, find_path, get_decisions

    # Get path details
    path = CRITICAL_PATHS["mapping_generation_v2"]
    print(path["entry"])
    print(path["calls"])

    # Query helper
    mapping_path = find_path("mapping")
    decisions = get_decisions("module_filtering")
"""

from typing import Dict, List, Any, Optional

# ============================================================================
# CRITICAL EXECUTION PATHS
# ============================================================================

CRITICAL_PATHS: Dict[str, Dict[str, Any]] = {

    # ------------------------------------------------------------------------
    # Path 1: Deterministic Mapping Generation (Primary Mapping Method)
    # ------------------------------------------------------------------------
    "mapping_generation_v2": {
        "description": "Main mapping flow using odoo-dictionary and 8 matching strategies",
        "entry": {
            "module": "api.mappings",
            "file": "backend/app/api/mappings.py",
            "line": 54,
            "function": "generate_mappings",
            "trigger": "POST /api/v1/datasets/{id}/mappings/generate?use_deterministic=true"
        },
        "calls": [
            {
                "step": 1,
                "module": "services.mapping_service",
                "file": "backend/app/services/mapping_service.py",
                "line": 137,
                "function": "generate_mappings_v2",
                "purpose": "Orchestrate mapping generation, load data"
            },
            {
                "step": 2,
                "module": "field_mapper.main",
                "file": "backend/app/field_mapper/main.py",
                "line": 218,
                "function": "DeterministicFieldMapper.map_dataframe",
                "purpose": "Main entry point for field mapping"
            },
            {
                "step": 3,
                "module": "field_mapper.profiling.column_profiler",
                "file": "backend/app/field_mapper/profiling/column_profiler.py",
                "line": 103,
                "function": "ColumnProfiler.profile_dataframe",
                "purpose": "Analyze column data types, patterns, statistics"
            },
            {
                "step": 4,
                "module": "field_mapper.matching.matching_pipeline",
                "file": "backend/app/field_mapper/matching/matching_pipeline.py",
                "line": 174,
                "function": "MatchingPipeline.match_sheet",
                "purpose": "Orchestrate 8 matching strategies for all columns"
            },
            {
                "step": 5,
                "module": "field_mapper.matching.matching_pipeline",
                "file": "backend/app/field_mapper/matching/matching_pipeline.py",
                "line": 77,
                "function": "MatchingPipeline.match_column",
                "purpose": "Match single column using all 8 strategies"
            },
            {
                "step": 6,
                "module": "services.mapping_service",
                "file": "backend/app/services/mapping_service.py",
                "line": 217,
                "function": "generate_mappings_v2 (store results)",
                "purpose": "Store mappings and suggestions in database"
            }
        ],
        "database_ops": [
            {"operation": "DELETE", "table": "mappings", "condition": "dataset_id match"},
            {"operation": "INSERT", "table": "mappings", "count": "one per column"},
            {"operation": "INSERT", "table": "suggestions", "count": "one per mapping (top 5 alternatives)"}
        ],
        "external_deps": [
            "polars (DataFrame processing)",
            "odoo-dictionary (knowledge base)",
            "fastexcel (Excel reading, optional)"
        ],
        "timing": {
            "typical": "5-30 seconds for 100 columns",
            "performance": "401,330 rows/second profiling"
        },
        "failure_modes": [
            {
                "error": "Knowledge base not loaded",
                "cause": "odoo-dictionary files missing or corrupt",
                "solution": "Rebuild knowledge base from odoo-dictionary"
            },
            {
                "error": "Invalid file format",
                "cause": "Unsupported Excel format or corrupt file",
                "solution": "Check file format, try CSV export"
            },
            {
                "error": "Module filtering too restrictive",
                "cause": "Selected modules don't match data content",
                "solution": "Try without module selection or choose broader modules"
            },
            {
                "error": "Low confidence mappings",
                "cause": "Column names don't match Odoo conventions",
                "solution": "Use module selection, rename columns, or generate custom fields"
            }
        ],
        "decision_tree": "should_use_module_filtering"
    },

    # ------------------------------------------------------------------------
    # Path 2: Hybrid Mapping Generation (Combines Deterministic + AI)
    # ------------------------------------------------------------------------
    "mapping_generation_hybrid": {
        "description": "Combines deterministic matching with AI fallback for unmapped columns",
        "entry": {
            "module": "api.mappings",
            "file": "backend/app/api/mappings.py",
            "line": 54,
            "function": "generate_mappings",
            "trigger": "POST /api/v1/datasets/{id}/mappings/generate?use_deterministic=false"
        },
        "calls": [
            {
                "step": 1,
                "module": "services.mapping_service",
                "file": "backend/app/services/mapping_service.py",
                "line": 157,
                "function": "generate_mappings_hybrid",
                "purpose": "Try deterministic first, fall back to AI for low-confidence columns"
            },
            {
                "step": 2,
                "module": "field_mapper.main",
                "file": "backend/app/field_mapper/main.py",
                "line": 218,
                "function": "DeterministicFieldMapper.map_dataframe",
                "purpose": "Primary deterministic matching"
            },
            {
                "step": 3,
                "module": "core.hybrid_matcher",
                "file": "backend/app/core/hybrid_matcher.py",
                "line": 45,
                "function": "HybridMatcher.match_headers",
                "purpose": "AI fallback for unmapped/low-confidence columns"
            }
        ],
        "database_ops": [
            {"operation": "DELETE", "table": "mappings", "condition": "dataset_id match"},
            {"operation": "INSERT", "table": "mappings", "count": "one per column"},
            {"operation": "INSERT", "table": "suggestions", "count": "one per mapping"}
        ],
        "external_deps": [
            "polars",
            "odoo-dictionary",
            "Anthropic API (for AI fallback)"
        ],
        "timing": {
            "typical": "10-60 seconds for 100 columns (depends on AI calls)",
            "ai_calls": "Only for low-confidence columns (< 0.6)"
        },
        "failure_modes": [
            {
                "error": "API key not configured",
                "cause": "ANTHROPIC_API_KEY missing",
                "solution": "Set API key in .env or use deterministic-only mode"
            },
            {
                "error": "Rate limit exceeded",
                "cause": "Too many AI calls in short time",
                "solution": "Use deterministic mode or wait for rate limit reset"
            }
        ],
        "decision_tree": "deterministic_vs_hybrid"
    },

    # ------------------------------------------------------------------------
    # Path 3: Module Selection System
    # ------------------------------------------------------------------------
    "module_filtering": {
        "description": "Constrains field search space by selecting Odoo modules (10x reduction)",
        "entry": {
            "module": "frontend.components.ModuleSelector",
            "file": "frontend/src/components/ModuleSelector.tsx",
            "line": 56,
            "function": "toggleModule",
            "trigger": "User clicks module checkbox"
        },
        "calls": [
            {
                "step": 1,
                "module": "api.datasets",
                "file": "backend/app/api/datasets.py",
                "line": 45,
                "function": "update_dataset",
                "purpose": "Store selected_modules in dataset"
            },
            {
                "step": 2,
                "module": "field_mapper.core.module_registry",
                "file": "backend/app/field_mapper/core/module_registry.py",
                "line": 390,
                "function": "ModuleRegistry.get_models_for_groups",
                "purpose": "Expand module names to model list"
            },
            {
                "step": 3,
                "module": "field_mapper.matching.matching_pipeline",
                "file": "backend/app/field_mapper/matching/matching_pipeline.py",
                "line": 194,
                "function": "MatchingPipeline.match_sheet",
                "purpose": "Apply target_models constraint to all strategies"
            }
        ],
        "database_ops": [
            {"operation": "UPDATE", "table": "datasets", "field": "selected_modules (JSON array)"}
        ],
        "external_deps": [],
        "timing": {
            "typical": "< 100ms (in-memory filtering)"
        },
        "impact": {
            "search_space_reduction": "10x (9,947 fields → ~500 fields)",
            "confidence_boost": "+15-30% average",
            "example": "Sales CRM + Contacts: 520 models → 36 models, 9,947 fields → 480 fields"
        },
        "failure_modes": [
            {
                "error": "No matches after filtering",
                "cause": "Selected modules don't contain relevant fields",
                "solution": "Deselect modules or choose broader module groups"
            }
        ]
    },

    # ------------------------------------------------------------------------
    # Path 4: Polars-based Profiling
    # ------------------------------------------------------------------------
    "polars_profiling": {
        "description": "High-performance column analysis using Polars DataFrames",
        "entry": {
            "module": "api.datasets",
            "file": "backend/app/api/datasets.py",
            "line": 67,
            "function": "profile_dataset",
            "trigger": "POST /api/v1/datasets/{id}/profile"
        },
        "calls": [
            {
                "step": 1,
                "module": "services.profiler_tasks",
                "file": "backend/app/services/profiler_tasks.py",
                "line": 18,
                "function": "profile_dataset (Celery task)",
                "purpose": "Async profiling task"
            },
            {
                "step": 2,
                "module": "field_mapper.profiling.column_profiler",
                "file": "backend/app/field_mapper/profiling/column_profiler.py",
                "line": 103,
                "function": "ColumnProfiler.profile_dataframe",
                "purpose": "Profile all columns in Polars DataFrame"
            },
            {
                "step": 3,
                "module": "field_mapper.profiling.column_profiler",
                "file": "backend/app/field_mapper/profiling/column_profiler.py",
                "line": 115,
                "function": "ColumnProfiler.profile_column",
                "purpose": "Profile single column (dtype, stats, patterns)"
            }
        ],
        "database_ops": [
            {"operation": "INSERT", "table": "column_profiles", "count": "one per column"},
            {"operation": "UPDATE", "table": "datasets", "field": "profiling_status = 'complete'"}
        ],
        "external_deps": [
            "polars (DataFrame engine)",
            "fastexcel (Excel reading, fallback to openpyxl/pandas)"
        ],
        "timing": {
            "performance": "401,330 rows/second",
            "example": "1M rows × 16 columns = ~2.5 seconds"
        },
        "failure_modes": [
            {
                "error": "fastexcel not found",
                "cause": "Optional dependency not installed",
                "solution": "pip install fastexcel (or fallback to openpyxl)"
            },
            {
                "error": "Celery worker not running",
                "cause": "Task never executes",
                "solution": "Start Celery worker: celery -A app.core.celery_app worker"
            }
        ]
    },

    # ------------------------------------------------------------------------
    # Path 5: 8-Strategy Matching Pipeline
    # ------------------------------------------------------------------------
    "matching_pipeline": {
        "description": "Parallel execution of 8 matching strategies per column",
        "entry": {
            "module": "field_mapper.matching.matching_pipeline",
            "file": "backend/app/field_mapper/matching/matching_pipeline.py",
            "line": 77,
            "function": "MatchingPipeline.match_column",
            "trigger": "Called once per column during mapping generation"
        },
        "strategies": [
            {
                "name": "ExactNameMatchStrategy",
                "file": "backend/app/field_mapper/matching/strategies/exact_name_match.py",
                "confidence": "1.0 (perfect match)",
                "purpose": "Match column name exactly to field name"
            },
            {
                "name": "LabelMatchStrategy",
                "file": "backend/app/field_mapper/matching/strategies/label_match.py",
                "confidence": "0.9 (high)",
                "purpose": "Match column name to field label (display name)"
            },
            {
                "name": "SelectionValueMatchStrategy",
                "file": "backend/app/field_mapper/matching/strategies/selection_value_match.py",
                "confidence": "0.85 (high)",
                "purpose": "Match cell values to selection field options"
            },
            {
                "name": "DataTypeCompatibilityStrategy",
                "file": "backend/app/field_mapper/matching/strategies/data_type_compatibility.py",
                "confidence": "0.7 (medium)",
                "purpose": "Match based on data type compatibility"
            },
            {
                "name": "PatternMatchStrategy",
                "file": "backend/app/field_mapper/matching/strategies/pattern_match.py",
                "confidence": "0.8 (high)",
                "purpose": "Match based on patterns (email, phone, URL, etc.)"
            },
            {
                "name": "FuzzyMatchStrategy",
                "file": "backend/app/field_mapper/matching/strategies/fuzzy_match.py",
                "confidence": "0.5-0.8 (variable)",
                "purpose": "Fuzzy string matching for similar names"
            },
            {
                "name": "ContextualMatchStrategy",
                "file": "backend/app/field_mapper/matching/strategies/contextual_match.py",
                "confidence": "0.65 (medium)",
                "purpose": "Use context from other columns in sheet"
            },
            {
                "name": "StatisticalSimilarityStrategy",
                "file": "backend/app/field_mapper/matching/strategies/statistical_similarity.py",
                "confidence": "0.6 (medium)",
                "purpose": "Match based on statistical distribution similarity"
            }
        ],
        "calls": [
            {
                "step": 1,
                "function": "Create MatchingContext",
                "purpose": "Build context object with KB, profiles, target models"
            },
            {
                "step": 2,
                "function": "Execute all strategies",
                "purpose": "Run 8 strategies in parallel, collect candidates"
            },
            {
                "step": 3,
                "function": "_merge_duplicates",
                "line": 130,
                "purpose": "Merge candidates from multiple strategies for same field"
            },
            {
                "step": 4,
                "function": "_apply_model_priority",
                "line": 144,
                "purpose": "Boost/penalize based on candidate model relevance"
            },
            {
                "step": 5,
                "function": "_rank_candidates",
                "line": 156,
                "purpose": "Sort by confidence score"
            },
            {
                "step": 6,
                "function": "Filter by threshold",
                "purpose": "Remove candidates below confidence_threshold (default 0.5)"
            }
        ],
        "timing": {
            "per_column": "~100ms (all 8 strategies)",
            "bottleneck": "Knowledge base lookups (trie-based, optimized)"
        },
        "failure_modes": [
            {
                "error": "No candidates returned",
                "cause": "No strategy matched above threshold",
                "solution": "Lower confidence_threshold or use custom field generation"
            }
        ]
    },

    # ------------------------------------------------------------------------
    # Path 6: Lambda Transformation Detection
    # ------------------------------------------------------------------------
    "lambda_detection": {
        "description": "Heuristic detection of opportunities to combine columns (e.g., first+last name)",
        "entry": {
            "module": "field_mapper.matching.matching_pipeline",
            "file": "backend/app/field_mapper/matching/matching_pipeline.py",
            "line": 251,
            "function": "MatchingPipeline._generate_lambda_suggestions",
            "trigger": "Called after matching all columns in sheet"
        },
        "calls": [
            {
                "step": 1,
                "function": "_looks_like_first_name",
                "line": 312,
                "purpose": "Detect 'First Name' style columns"
            },
            {
                "step": 2,
                "function": "_looks_like_last_name",
                "line": 317,
                "purpose": "Detect 'Last Name' style columns"
            },
            {
                "step": 3,
                "function": "Generate lambda function",
                "purpose": "Create Python lambda to combine columns"
            },
            {
                "step": 4,
                "function": "Create FieldMapping",
                "purpose": "Return virtual column mapping with lambda metadata"
            }
        ],
        "output": {
            "virtual_column": "lambda_name",
            "target": "res.partner.name",
            "lambda_function": "lambda self, row, **kwargs: ' '.join([row['First Name'], row['Last Name']])",
            "dependencies": ["First Name", "Last Name"],
            "confidence": 0.85,
            "mapping_type": "lambda"
        },
        "timing": {
            "overhead": "< 10ms (simple heuristics)"
        },
        "extensibility": "Add new heuristics in _generate_lambda_suggestions for other patterns"
    },

    # ------------------------------------------------------------------------
    # Path 7: Two-Phase Import with KeyMap
    # ------------------------------------------------------------------------
    "two_phase_import": {
        "description": "Import parents first, store KeyMap, then import children with resolved FKs",
        "entry": {
            "module": "api.imports",
            "file": "backend/app/api/imports.py",
            "line": 34,
            "function": "execute_import",
            "trigger": "POST /api/v1/imports/execute"
        },
        "calls": [
            {
                "step": 1,
                "module": "services.import_service",
                "file": "backend/app/services/import_service.py",
                "line": 45,
                "function": "ImportService.execute_import",
                "purpose": "Orchestrate import"
            },
            {
                "step": 2,
                "module": "importers.graph",
                "file": "backend/app/importers/graph.py",
                "line": 23,
                "function": "ImportGraph.from_default",
                "purpose": "Build topological sort of models (parents before children)"
            },
            {
                "step": 3,
                "module": "importers.executor",
                "file": "backend/app/importers/executor.py",
                "line": 22,
                "function": "TwoPhaseImporter.execute",
                "purpose": "Import each model in graph order"
            },
            {
                "step": 4,
                "module": "importers.executor",
                "file": "backend/app/importers/executor.py",
                "line": 52,
                "function": "TwoPhaseImporter._import_model",
                "purpose": "Import all records for one model"
            },
            {
                "step": 5,
                "module": "importers.executor",
                "file": "backend/app/importers/executor.py",
                "line": 86,
                "function": "TwoPhaseImporter._resolve_relationships",
                "purpose": "Lookup parent IDs in KeyMap, replace source values"
            },
            {
                "step": 6,
                "module": "connectors.odoo",
                "file": "backend/app/connectors/odoo.py",
                "line": 78,
                "function": "OdooConnector.upsert",
                "purpose": "Create/update record in Odoo via JSON-RPC"
            },
            {
                "step": 7,
                "module": "importers.executor",
                "file": "backend/app/importers/executor.py",
                "line": 154,
                "function": "TwoPhaseImporter._store_keymap",
                "purpose": "Store source_key → odoo_id mapping for children to lookup"
            }
        ],
        "database_ops": [
            {"operation": "INSERT", "table": "runs", "count": "one per import"},
            {"operation": "INSERT", "table": "run_logs", "count": "one per record"},
            {"operation": "INSERT", "table": "keymaps", "count": "one per parent record"}
        ],
        "external_deps": [
            "Odoo JSON-RPC API"
        ],
        "timing": {
            "depends_on": "Network latency to Odoo, record count, complexity",
            "typical": "10-100 records/second"
        },
        "failure_modes": [
            {
                "error": "Foreign key constraint violation",
                "cause": "Parent not imported yet (graph order incorrect)",
                "solution": "Fix ImportGraph topological order"
            },
            {
                "error": "KeyMap lookup failed",
                "cause": "Parent import failed or source_key mismatch",
                "solution": "Check RunLog for parent errors, verify key field consistency"
            },
            {
                "error": "Odoo authentication failed",
                "cause": "Invalid credentials or permissions",
                "solution": "Check ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD in .env"
            }
        ]
    },

    # ------------------------------------------------------------------------
    # Path 8: Import Graph Topological Sort
    # ------------------------------------------------------------------------
    "import_graph_topo_sort": {
        "description": "Determines import order to satisfy parent/child dependencies",
        "entry": {
            "module": "importers.graph",
            "file": "backend/app/importers/graph.py",
            "line": 23,
            "function": "ImportGraph.from_default",
            "trigger": "Called at start of import"
        },
        "default_order": [
            {"order": 1, "model": "res.partner", "dependencies": []},
            {"order": 2, "model": "res.users", "dependencies": ["res.partner"]},
            {"order": 3, "model": "crm.lead", "dependencies": ["res.partner", "res.users"]},
            {"order": 4, "model": "product.template", "dependencies": []},
            {"order": 5, "model": "product.product", "dependencies": ["product.template"]},
            {"order": 6, "model": "project.project", "dependencies": ["res.partner"]},
            {"order": 7, "model": "project.task", "dependencies": ["project.project", "res.users"]},
            {"order": 8, "model": "sale.order", "dependencies": ["res.partner"]},
            {"order": 9, "model": "sale.order.line", "dependencies": ["sale.order", "product.product"]},
            {"order": 10, "model": "account.move", "dependencies": ["res.partner"]}
        ],
        "algorithm": "Manual topological sort (predefined for common Odoo models)",
        "extensibility": "Add new models and dependencies to ImportGraph class"
    }
}

# ============================================================================
# DECISION TREES
# ============================================================================

DECISION_TREES: Dict[str, Dict[str, Any]] = {

    "should_use_module_filtering": {
        "question": "Should I use module selection to constrain field matching?",
        "decision_criteria": [
            {
                "condition": "User knows which Odoo modules the data belongs to",
                "recommendation": "YES - Use module selection",
                "benefit": "10x search space reduction, +15-30% confidence boost"
            },
            {
                "condition": "Data spans multiple unrelated modules",
                "recommendation": "NO - Skip module selection",
                "benefit": "Avoid missing valid matches from other modules"
            },
            {
                "condition": "First time mapping unknown dataset",
                "recommendation": "TRY BOTH - Generate without modules first to explore, then refine with modules",
                "benefit": "Learn which modules are relevant before constraining"
            }
        ],
        "related_path": "module_filtering"
    },

    "deterministic_vs_hybrid": {
        "question": "Should I use deterministic-only or hybrid (deterministic + AI) mapping?",
        "decision_criteria": [
            {
                "condition": "Column names follow Odoo conventions",
                "recommendation": "Deterministic only (faster, no API costs)",
                "benefit": "5-30 seconds, no external dependencies"
            },
            {
                "condition": "Column names are non-standard or business-specific",
                "recommendation": "Hybrid mode",
                "benefit": "AI fallback for low-confidence columns improves accuracy"
            },
            {
                "condition": "No API key available or offline environment",
                "recommendation": "Deterministic only (required)",
                "benefit": "Works without external API"
            }
        ],
        "related_paths": ["mapping_generation_v2", "mapping_generation_hybrid"]
    },

    "lambda_vs_direct_mapping": {
        "question": "Should I use lambda transformation to combine columns?",
        "decision_criteria": [
            {
                "condition": "Multiple related columns map to single Odoo field (e.g., First Name + Last Name → name)",
                "recommendation": "Use lambda transformation",
                "benefit": "Preserves both source columns, combines at import time"
            },
            {
                "condition": "Single column maps directly to Odoo field",
                "recommendation": "Use direct mapping",
                "benefit": "Simpler, faster, less error-prone"
            },
            {
                "condition": "Complex transformation logic needed (conditional, lookups, etc.)",
                "recommendation": "Use custom Python transform in transform_service.py",
                "benefit": "More powerful than lambda, better error handling"
            }
        ],
        "related_path": "lambda_detection"
    },

    "when_to_generate_custom_fields": {
        "question": "Should I generate custom Odoo fields or map to existing fields?",
        "decision_criteria": [
            {
                "condition": "Source data has columns with no Odoo equivalent",
                "recommendation": "Generate custom fields",
                "benefit": "Preserves all source data, no data loss"
            },
            {
                "condition": "All source columns have reasonable Odoo field matches",
                "recommendation": "Map to existing fields",
                "benefit": "Simpler, no Odoo customization required"
            },
            {
                "condition": "Business-specific fields (industry jargon, internal codes, etc.)",
                "recommendation": "Generate custom fields",
                "benefit": "Maintains business context, easier for users to understand"
            }
        ]
    }
}

# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

PERFORMANCE: Dict[str, Any] = {
    "profiling": {
        "rows_per_second": 401_330,
        "example": "1M rows × 16 columns = ~2.5 seconds",
        "bottleneck": "File I/O (Excel reading)",
        "engine": "Polars"
    },
    "mapping_generation": {
        "typical_time": "5-30 seconds for 100 columns",
        "per_column_time": "~100ms (all 8 strategies)",
        "bottleneck": "Knowledge base lookups (trie-based, optimized)",
        "with_module_filtering": "+15-30% confidence, same speed"
    },
    "module_filtering": {
        "reduction_factor": "10x",
        "example": "9,947 fields → ~500 fields (Sales CRM + Contacts)",
        "overhead": "< 100ms (in-memory filtering)"
    },
    "import": {
        "typical_speed": "10-100 records/second",
        "depends_on": ["Network latency to Odoo", "Record complexity", "Number of relationships"],
        "bottleneck": "Odoo JSON-RPC API calls"
    }
}

# ============================================================================
# HELPER FUNCTIONS FOR AI AGENTS
# ============================================================================

def find_path(query: str) -> Optional[Dict[str, Any]]:
    """
    Find execution path by keyword search.

    Example:
        path = find_path("mapping")
        # Returns CRITICAL_PATHS["mapping_generation_v2"]
    """
    query_lower = query.lower()
    for path_name, path_data in CRITICAL_PATHS.items():
        if query_lower in path_name.lower():
            return path_data
        if query_lower in path_data.get("description", "").lower():
            return path_data
    return None


def get_decisions(path_name: str) -> Optional[str]:
    """
    Get decision tree name for a given path.

    Example:
        decision = get_decisions("module_filtering")
        # Returns "should_use_module_filtering"
    """
    path = CRITICAL_PATHS.get(path_name)
    if path and "decision_tree" in path:
        return path["decision_tree"]
    return None


def get_entry_point(path_name: str) -> Optional[Dict[str, Any]]:
    """
    Get entry point details for a path.

    Example:
        entry = get_entry_point("mapping_generation_v2")
        # Returns {
        #     "module": "api.mappings",
        #     "file": "backend/app/api/mappings.py",
        #     "line": 54,
        #     ...
        # }
    """
    path = CRITICAL_PATHS.get(path_name)
    if path:
        return path.get("entry")
    return None


def get_call_chain(path_name: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get call chain for a path.

    Example:
        calls = get_call_chain("mapping_generation_v2")
        # Returns list of call dictionaries with step, module, file, line, function
    """
    path = CRITICAL_PATHS.get(path_name)
    if path:
        return path.get("calls")
    return None


def get_failure_modes(path_name: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get known failure modes and solutions for a path.

    Example:
        failures = get_failure_modes("mapping_generation_v2")
        # Returns list of {error, cause, solution}
    """
    path = CRITICAL_PATHS.get(path_name)
    if path:
        return path.get("failure_modes")
    return None


def list_all_paths() -> List[str]:
    """
    List all available execution paths.

    Example:
        paths = list_all_paths()
        # Returns ["mapping_generation_v2", "mapping_generation_hybrid", ...]
    """
    return list(CRITICAL_PATHS.keys())


def get_performance_metrics(category: str) -> Optional[Dict[str, Any]]:
    """
    Get performance metrics for a category.

    Example:
        metrics = get_performance_metrics("profiling")
        # Returns {"rows_per_second": 401330, ...}
    """
    return PERFORMANCE.get(category)


# ============================================================================
# EXAMPLE USAGE FOR AI AGENTS
# ============================================================================

if __name__ == "__main__":
    # Example 1: Find path by keyword
    print("=== Example 1: Find path ===")
    path = find_path("mapping")
    if path:
        print(f"Description: {path['description']}")
        print(f"Entry point: {path['entry']['file']}:{path['entry']['line']}")

    # Example 2: Get call chain
    print("\n=== Example 2: Get call chain ===")
    calls = get_call_chain("mapping_generation_v2")
    if calls:
        for call in calls:
            print(f"Step {call['step']}: {call['function']} ({call['file']}:{call['line']})")

    # Example 3: Get failure modes
    print("\n=== Example 3: Get failure modes ===")
    failures = get_failure_modes("mapping_generation_v2")
    if failures:
        for failure in failures:
            print(f"Error: {failure['error']}")
            print(f"  Cause: {failure['cause']}")
            print(f"  Solution: {failure['solution']}")

    # Example 4: Get performance metrics
    print("\n=== Example 4: Performance metrics ===")
    metrics = get_performance_metrics("profiling")
    if metrics:
        print(f"Rows/second: {metrics['rows_per_second']:,}")
        print(f"Example: {metrics['example']}")

    # Example 5: List all paths
    print("\n=== Example 5: All paths ===")
    for path_name in list_all_paths():
        print(f"  - {path_name}")
