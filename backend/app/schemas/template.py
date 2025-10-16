"""
Pydantic schemas for import templates
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class TemplateStep(BaseModel):
    """A single step in a template workflow"""
    title: str
    models: List[str]
    description: str
    dependsOn: Optional[List[str]] = None
    optional: Optional[bool] = False
    note: Optional[str] = None
    sampleHeaders: Optional[List[str]] = None


class TemplateMetadata(BaseModel):
    """Additional metadata about a template"""
    recommended_for: Optional[List[str]] = None
    odoo_modules: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    priority: Optional[int] = None


class Template(BaseModel):
    """Import template definition"""
    id: str
    name: str
    description: str
    category: str
    icon: Optional[str] = None
    estimatedTime: str
    difficulty: str
    prerequisites: List[str]
    models: List[str]
    steps: List[TemplateStep]
    metadata: Optional[TemplateMetadata] = None


class TemplateListItem(BaseModel):
    """Simplified template for list view"""
    id: str
    name: str
    description: str
    category: str
    icon: Optional[str] = None
    estimatedTime: str
    difficulty: str
    modelCount: int
    completed: bool = False


class TemplateProgress(BaseModel):
    """Track progress through a template"""
    templateId: str
    completedModels: List[str]
    totalModels: int
    percentComplete: int
    lastUpdated: Optional[str] = None


class TemplateInstantiateRequest(BaseModel):
    """Request to create a Graph from a template"""
    datasetId: Optional[int] = None
    customName: Optional[str] = None
