"""
API routes for import templates
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.services.template_service import TemplateService
from app.schemas.template import (
    Template,
    TemplateListItem,
    TemplateProgress,
    TemplateInstantiateRequest
)

router = APIRouter()


@router.get("/templates", response_model=List[TemplateListItem])
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    List all available import templates

    Query parameters:
    - category: Optional filter by category (foundation, sales, projects, accounting, complete)
    """
    service = TemplateService(db)
    templates = service.list_templates(category=category)
    return templates


@router.get("/templates/categories")
async def get_template_categories(db: Session = Depends(get_db)):
    """Get all available template categories"""
    service = TemplateService(db)
    return service.get_categories()


@router.get("/templates/{template_id}", response_model=Template)
async def get_template(template_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific template

    Path parameters:
    - template_id: Template identifier (e.g., "template_sales_crm")
    """
    service = TemplateService(db)
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found"
        )

    return template


@router.get("/templates/{template_id}/progress", response_model=TemplateProgress)
async def get_template_progress(template_id: str, db: Session = Depends(get_db)):
    """
    Get progress information for a template based on completed imports

    Path parameters:
    - template_id: Template identifier
    """
    service = TemplateService(db)
    progress = service.get_template_progress(template_id)

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found"
        )

    return progress


@router.post("/templates/{template_id}/instantiate", status_code=status.HTTP_201_CREATED)
async def instantiate_template(
    template_id: str,
    request: TemplateInstantiateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a Graph from a template

    This endpoint creates a new Graph based on a template definition,
    linking it to a dataset if provided.

    Path parameters:
    - template_id: Template identifier

    Body parameters:
    - datasetId: Optional dataset to link to the graph
    - customName: Optional custom name for the created graph
    """
    service = TemplateService(db)
    graph_id = service.instantiate_template(
        template_id=template_id,
        dataset_id=request.datasetId,
        custom_name=request.customName
    )

    if not graph_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to instantiate template '{template_id}'"
        )

    return {
        "graphId": graph_id,
        "templateId": template_id,
        "message": f"Graph created from template '{template_id}'"
    }
