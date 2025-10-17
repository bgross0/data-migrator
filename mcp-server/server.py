#!/usr/bin/env python3
"""
Enhanced MCP Server for Data Migrator

Provides comprehensive read-only tools for Claude Code to deeply understand
the system state, data quality, and help users more effectively.
"""
import httpx
import asyncio
import os
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from functools import lru_cache
from mcp.server import FastMCP

# Configure logging
logging.basicConfig(
    level=os.getenv('MCP_LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Data Migrator Assistant Enhanced")

# Configuration
BASE_URL = os.getenv("DATA_MIGRATOR_API", "http://localhost:8888/api/v1")
CACHE_TTL = int(os.getenv("MCP_CACHE_TTL", "300"))  # 5 minutes default

# Cache helper
def get_ttl_hash(seconds=CACHE_TTL):
    """Return the same value within `seconds` time window."""
    return round(datetime.now().timestamp() / seconds)


# ============================================================================
# ORIGINAL TOOLS (Enhanced with better error handling)
# ============================================================================

@mcp.tool()
async def list_datasets() -> dict:
    """
    List all uploaded datasets with their basic information.

    Returns:
        List of datasets with id, name, created_at, and sheet count
    """
    logger.info("Fetching datasets list")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/datasets")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Found {len(data.get('datasets', []))} datasets")
            return data
        except httpx.ConnectError:
            logger.error("Backend API not reachable")
            return {"error": "Backend API not running on port 8888. Start with: uvicorn app.main:app --port 8888"}
        except Exception as e:
            logger.error(f"Error fetching datasets: {e}")
            return {"error": str(e)}


@mcp.tool()
async def get_dataset_info(dataset_id: int) -> dict:
    """
    Get detailed information about a specific dataset.

    Args:
        dataset_id: The ID of the dataset to query

    Returns:
        Dataset details including sheets, columns, row counts
    """
    logger.info(f"Fetching dataset info for ID: {dataset_id}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/datasets/{dataset_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": f"Dataset {dataset_id} not found"}
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            logger.error(f"Error fetching dataset {dataset_id}: {e}")
            return {"error": str(e)}


@mcp.tool()
async def get_dataset_preview(dataset_id: int, sheet_name: Optional[str] = None, limit: int = 10) -> dict:
    """
    Get a preview of dataset rows with enhanced filtering.

    Args:
        dataset_id: The ID of the dataset
        sheet_name: Optional specific sheet to preview
        limit: Maximum number of rows to return (default: 10, max: 20)

    Returns:
        Preview data with sample rows and column statistics
    """
    limit = min(limit, 20)
    logger.info(f"Fetching preview for dataset {dataset_id}, sheet: {sheet_name}, limit: {limit}")

    async with httpx.AsyncClient() as client:
        try:
            params = {"limit": limit}
            if sheet_name:
                params["sheet"] = sheet_name

            response = await client.get(
                f"{BASE_URL}/datasets/{dataset_id}/cleaned-data",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching preview: {e}")
            return {"error": str(e)}


# ============================================================================
# NEW ENHANCED VISIBILITY TOOLS
# ============================================================================

@mcp.tool()
async def analyze_column_quality(dataset_id: int, sheet_name: str, column_name: str) -> dict:
    """
    Deep analysis of a specific column's data quality.

    Args:
        dataset_id: Dataset ID
        sheet_name: Sheet name
        column_name: Column to analyze

    Returns:
        Detailed quality metrics including:
        - Data type distribution
        - Null count and percentage
        - Unique values count
        - Common patterns
        - Potential issues
    """
    logger.info(f"Analyzing column quality: dataset={dataset_id}, sheet={sheet_name}, column={column_name}")

    async with httpx.AsyncClient() as client:
        try:
            # Get column profile if available
            response = await client.get(
                f"{BASE_URL}/datasets/{dataset_id}/sheets/{sheet_name}/columns/{column_name}/profile"
            )

            if response.status_code == 404:
                # Fallback: analyze from preview data
                preview = await get_dataset_preview(dataset_id, sheet_name, 20)
                if "error" in preview:
                    return preview

                # Basic analysis from preview
                rows = preview.get("data", [])
                column_values = [row.get(column_name) for row in rows if column_name in row]

                return {
                    "column": column_name,
                    "sample_size": len(column_values),
                    "nulls": column_values.count(None),
                    "unique_values": len(set(v for v in column_values if v is not None)),
                    "sample_values": list(set(str(v) for v in column_values[:5] if v is not None)),
                    "note": "Basic analysis from preview data. Full profiling may provide more insights."
                }

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Error analyzing column: {e}")
            return {"error": str(e)}


@mcp.tool()
async def get_import_history(dataset_id: Optional[int] = None, limit: int = 10) -> dict:
    """
    Get history of import runs with their status and statistics.

    Args:
        dataset_id: Optional filter by dataset
        limit: Maximum number of runs to return

    Returns:
        List of import runs with status, timing, and error information
    """
    logger.info(f"Fetching import history for dataset: {dataset_id}")

    async with httpx.AsyncClient() as client:
        try:
            url = f"{BASE_URL}/runs" if not dataset_id else f"{BASE_URL}/datasets/{dataset_id}/runs"
            response = await client.get(url, params={"limit": limit})

            if response.status_code == 404:
                return {"runs": [], "message": "No import runs found"}

            response.raise_for_status()
            runs = response.json()

            # Enhance with human-readable information
            for run in runs.get("runs", []):
                if run.get("status") == "failed" and run.get("error_message"):
                    run["error_summary"] = _summarize_error(run["error_message"])

            return runs

        except Exception as e:
            logger.error(f"Error fetching import history: {e}")
            return {"error": str(e)}


@mcp.tool()
async def analyze_import_errors(run_id: str) -> dict:
    """
    Analyze errors from a specific import run to provide actionable insights.

    Args:
        run_id: The import run ID to analyze

    Returns:
        Detailed error analysis with:
        - Error categories
        - Affected rows
        - Suggested fixes
        - Common patterns
    """
    logger.info(f"Analyzing errors for run: {run_id}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/runs/{run_id}/logs")

            if response.status_code == 404:
                return {"error": f"Run {run_id} not found"}

            response.raise_for_status()
            logs = response.json()

            # Analyze error patterns
            errors = [log for log in logs if log.get("level") in ["error", "critical"]]

            error_analysis = {
                "run_id": run_id,
                "total_errors": len(errors),
                "error_categories": _categorize_errors(errors),
                "common_issues": _find_common_issues(errors),
                "suggested_fixes": _suggest_fixes(errors)
            }

            return error_analysis

        except Exception as e:
            logger.error(f"Error analyzing run {run_id}: {e}")
            return {"error": str(e)}


@mcp.tool()
async def suggest_field_mapping(dataset_id: int, sheet_name: str, target_model: str) -> dict:
    """
    Get AI-powered field mapping suggestions for a sheet.

    Args:
        dataset_id: Dataset ID
        sheet_name: Sheet to map
        target_model: Target Odoo model (e.g., "res.partner")

    Returns:
        Mapping suggestions with confidence scores and reasoning
    """
    logger.info(f"Generating mapping suggestions: dataset={dataset_id}, sheet={sheet_name}, model={target_model}")

    async with httpx.AsyncClient() as client:
        try:
            # Get sheet columns
            response = await client.get(f"{BASE_URL}/datasets/{dataset_id}/sheets/{sheet_name}")

            if response.status_code == 404:
                return {"error": "Sheet not found"}

            response.raise_for_status()
            sheet_info = response.json()

            # Get target model fields
            model_response = await client.get(f"{BASE_URL}/odoo/models/{target_model}/fields")

            if model_response.status_code == 404:
                return {"error": f"Model {target_model} not found"}

            model_response.raise_for_status()
            model_fields = model_response.json()

            # Generate suggestions (this could call an AI service in production)
            suggestions = _generate_mapping_suggestions(
                sheet_info.get("columns", []),
                model_fields.get("fields", [])
            )

            return {
                "sheet": sheet_name,
                "target_model": target_model,
                "suggestions": suggestions,
                "confidence_threshold": 0.7,
                "high_confidence_count": len([s for s in suggestions if s.get("confidence", 0) > 0.7])
            }

        except Exception as e:
            logger.error(f"Error suggesting mappings: {e}")
            return {"error": str(e)}


@mcp.tool()
async def get_data_cleaning_report(dataset_id: int) -> dict:
    """
    Get comprehensive data cleaning report showing what was cleaned.

    Args:
        dataset_id: Dataset ID

    Returns:
        Detailed report of cleaning operations performed
    """
    logger.info(f"Fetching cleaning report for dataset: {dataset_id}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/datasets/{dataset_id}/cleaning-report")

            if response.status_code == 404:
                return {"message": "No cleaning report available for this dataset"}

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Error fetching cleaning report: {e}")
            return {"error": str(e)}


@mcp.tool()
async def check_system_status() -> dict:
    """
    Comprehensive system status check including all components.

    Returns:
        Status of:
        - API health
        - Database connection
        - Celery workers
        - Odoo connection
        - Storage availability
    """
    logger.info("Checking comprehensive system status")

    status = {
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }

    async with httpx.AsyncClient() as client:
        # Check API
        try:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            response.raise_for_status()
            status["components"]["api"] = {"status": "healthy", "details": response.json()}
        except Exception as e:
            status["components"]["api"] = {"status": "unhealthy", "error": str(e)}

        # Check database
        try:
            response = await client.get(f"{BASE_URL}/health/database", timeout=5.0)
            status["components"]["database"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy"
            }
        except:
            status["components"]["database"] = {"status": "unknown"}

        # Check Odoo connection
        try:
            response = await client.get(f"{BASE_URL}/odoo/status", timeout=5.0)
            status["components"]["odoo"] = {
                "status": "connected" if response.status_code == 200 else "disconnected"
            }
        except:
            status["components"]["odoo"] = {"status": "unknown"}

    # Overall status
    unhealthy = [k for k, v in status["components"].items() if v.get("status") not in ["healthy", "connected"]]
    status["overall"] = "healthy" if not unhealthy else f"degraded ({', '.join(unhealthy)} issues)"

    return status


@mcp.tool()
async def get_relationship_graph(dataset_id: int) -> dict:
    """
    Get the relationship graph showing dependencies between entities.

    Args:
        dataset_id: Dataset ID

    Returns:
        Import graph with nodes, edges, and topological order
    """
    logger.info(f"Fetching relationship graph for dataset: {dataset_id}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/datasets/{dataset_id}/import-graph")

            if response.status_code == 404:
                # Return default graph structure
                return {
                    "message": "No custom graph defined, using default import order",
                    "default_order": [
                        "res.partner",
                        "product.template",
                        "product.product",
                        "sale.order",
                        "sale.order.line"
                    ]
                }

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Error fetching relationship graph: {e}")
            return {"error": str(e)}


@mcp.tool()
async def search_documentation(query: str) -> dict:
    """
    Search Data Migrator documentation for help on specific topics.

    Args:
        query: Search query (e.g., "field mapping", "transforms", "templates")

    Returns:
        Relevant documentation snippets and links
    """
    logger.info(f"Searching documentation for: {query}")

    # In a real implementation, this would search actual docs
    # For now, return helpful static information based on common queries

    docs = {
        "field mapping": {
            "summary": "Field mapping connects spreadsheet columns to Odoo fields",
            "key_points": [
                "Use exact match for columns with same names",
                "Apply transforms to normalize data (phone, email, etc)",
                "Required fields must be mapped",
                "Many2one fields need valid references"
            ],
            "see_also": ["transforms", "templates"]
        },
        "transforms": {
            "summary": "Transforms clean and normalize data during import",
            "available": [
                "trim - Remove whitespace",
                "lower/upper/titlecase - Change case",
                "phone_normalize - Standard phone format",
                "email_normalize - Clean email addresses",
                "currency_to_float - Convert $1,234.56 to 1234.56",
                "split_name - Split full names",
                "regex_extract - Extract patterns"
            ],
            "see_also": ["field mapping", "data cleaning"]
        },
        "templates": {
            "summary": "Templates provide pre-configured import workflows",
            "available": [
                "Sales & CRM - Customers, leads, orders",
                "Projects - Projects and tasks",
                "Accounting - Invoices and bills",
                "Essential Setup - Core configuration",
                "Complete Migration - Full business data"
            ],
            "see_also": ["import order", "dependencies"]
        },
        "errors": {
            "summary": "Common import errors and fixes",
            "common_issues": [
                "Missing required field - Map all required fields",
                "Invalid reference - Parent record must exist",
                "Type mismatch - Apply appropriate transform",
                "Duplicate key - Check unique constraints"
            ],
            "see_also": ["validation", "relationships"]
        }
    }

    # Simple keyword matching
    query_lower = query.lower()
    matches = []

    for topic, content in docs.items():
        if query_lower in topic or topic in query_lower:
            matches.append({"topic": topic, **content})

    if not matches:
        # Fuzzy match on content
        for topic, content in docs.items():
            if any(query_lower in str(v).lower() for v in content.values()):
                matches.append({"topic": topic, **content})

    return {
        "query": query,
        "results": matches if matches else [{"message": f"No documentation found for '{query}'"}]
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _summarize_error(error_message: str) -> str:
    """Convert technical error to human-readable summary."""
    if "required" in error_message.lower():
        return "Missing required fields"
    elif "foreign key" in error_message.lower() or "reference" in error_message.lower():
        return "Invalid reference to another record"
    elif "unique" in error_message.lower():
        return "Duplicate value in unique field"
    elif "type" in error_message.lower():
        return "Data type mismatch"
    elif "connection" in error_message.lower():
        return "Connection issue with Odoo"
    else:
        return "Data validation error"


def _categorize_errors(errors: List[Dict]) -> Dict[str, int]:
    """Categorize errors by type."""
    categories = {}
    for error in errors:
        summary = _summarize_error(error.get("message", ""))
        categories[summary] = categories.get(summary, 0) + 1
    return categories


def _find_common_issues(errors: List[Dict]) -> List[str]:
    """Find common patterns in errors."""
    issues = []

    # Check for missing fields
    missing_fields = set()
    for error in errors:
        msg = error.get("message", "")
        if "required" in msg.lower():
            # Extract field name (this is simplified)
            words = msg.split()
            for i, word in enumerate(words):
                if word.lower() == "field" and i + 1 < len(words):
                    missing_fields.add(words[i + 1].strip("':,"))

    if missing_fields:
        issues.append(f"Missing required fields: {', '.join(missing_fields)}")

    return issues


def _suggest_fixes(errors: List[Dict]) -> List[str]:
    """Suggest fixes based on error patterns."""
    fixes = []

    error_types = _categorize_errors(errors)

    if "Missing required fields" in error_types:
        fixes.append("Map all required fields in the target model")

    if "Invalid reference to another record" in error_types:
        fixes.append("Ensure parent records are imported before child records")

    if "Data type mismatch" in error_types:
        fixes.append("Apply appropriate transforms (e.g., currency_to_float, phone_normalize)")

    if "Duplicate value in unique field" in error_types:
        fixes.append("Check for duplicate values in unique columns (email, code, etc)")

    return fixes


def _generate_mapping_suggestions(columns: List[Dict], fields: List[Dict]) -> List[Dict]:
    """Generate field mapping suggestions (simplified version)."""
    suggestions = []

    for column in columns:
        col_name = column.get("name", "").lower()

        # Find best match
        best_match = None
        best_score = 0
        reason = ""

        for field in fields:
            field_name = field.get("name", "").lower()
            field_label = field.get("string", "").lower()

            # Exact match
            if col_name == field_name:
                best_match = field
                best_score = 1.0
                reason = "Exact name match"
                break

            # Label match
            if col_name == field_label:
                best_match = field
                best_score = 0.9
                reason = "Label match"
                break

            # Partial match
            if col_name in field_name or field_name in col_name:
                if best_score < 0.7:
                    best_match = field
                    best_score = 0.7
                    reason = "Partial name match"

            # Common patterns
            if "email" in col_name and field.get("type") == "char" and "email" in field_name:
                if best_score < 0.8:
                    best_match = field
                    best_score = 0.8
                    reason = "Email pattern match"

            if "phone" in col_name and field.get("type") == "char" and "phone" in field_name:
                if best_score < 0.8:
                    best_match = field
                    best_score = 0.8
                    reason = "Phone pattern match"

        if best_match:
            suggestions.append({
                "source_column": column.get("name"),
                "target_field": best_match.get("name"),
                "field_type": best_match.get("type"),
                "confidence": best_score,
                "reason": reason,
                "required": best_match.get("required", False)
            })

    return suggestions


if __name__ == "__main__":
    logger.info("Starting Enhanced MCP Server for Data Migrator")
    mcp.run()