#!/usr/bin/env python3
"""
MCP Server for Data Migrator

Provides read-only tools for Claude Code to assist users with data migration tasks.
All tools are safe - they only READ data, never modify it.
"""
import httpx
import asyncio
from mcp.server import FastMCP

# Initialize MCP server
mcp = FastMCP("Data Migrator Assistant")

# Base URL for Data Migrator API
BASE_URL = "http://localhost:8888/api/v1"


@mcp.tool()
async def list_datasets() -> dict:
    """
    List all uploaded datasets with their basic information.

    Returns:
        List of datasets with id, name, created_at, and sheet count
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/datasets")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_dataset_info(dataset_id: int) -> dict:
    """
    Get detailed information about a specific dataset.

    Args:
        dataset_id: The ID of the dataset to query

    Returns:
        Dataset details including sheets, columns, row counts
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/datasets/{dataset_id}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_dataset_preview(dataset_id: int, limit: int = 10) -> dict:
    """
    Get a preview of dataset rows (limited to prevent overwhelming responses).

    Args:
        dataset_id: The ID of the dataset
        limit: Maximum number of rows to return (default: 10, max: 20)

    Returns:
        Preview data with sample rows
    """
    # Enforce max limit for safety
    limit = min(limit, 20)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/datasets/{dataset_id}/cleaned-data",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def list_templates() -> list:
    """
    List all available import templates (e.g., Sales & CRM, Projects, Accounting).

    Returns:
        List of templates with category, difficulty, and model count
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/templates")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_template_details(template_id: str) -> dict:
    """
    Get detailed information about a specific template including steps and prerequisites.

    Args:
        template_id: Template identifier (e.g., "template_sales_crm")

    Returns:
        Template details with steps, models, and recommendations
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/templates/{template_id}")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_odoo_models(modules: str = None) -> dict:
    """
    Get list of available Odoo models that can be imported.

    Args:
        modules: Optional comma-separated list of modules to filter (e.g., "crm,sale")

    Returns:
        List of Odoo models with descriptions
    """
    async with httpx.AsyncClient() as client:
        params = {"modules": modules} if modules else {}
        response = await client.get(f"{BASE_URL}/odoo/models", params=params)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_odoo_field_info(model: str) -> dict:
    """
    Get field definitions for a specific Odoo model.

    Args:
        model: Odoo model name (e.g., "res.partner", "crm.lead")

    Returns:
        Field definitions including types, requirements, and relationships
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/odoo/models/{model}/fields")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_current_mappings(dataset_id: int) -> list:
    """
    Get current field mappings for a dataset.

    Args:
        dataset_id: The ID of the dataset

    Returns:
        List of current field mappings (source column → Odoo field)
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/datasets/{dataset_id}/mappings")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_available_transforms() -> dict:
    """
    Get catalog of available data transformation functions.

    Returns:
        List of transforms with descriptions and examples
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/transforms/available")
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def check_api_health() -> dict:
    """
    Check if the Data Migrator API is running and accessible.

    Returns:
        Health status and version information
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8888/api/v1/health")
            response.raise_for_status()
            return {"status": "healthy", "details": response.json()}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
