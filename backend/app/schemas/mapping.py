from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.models.mapping import MappingStatus


class TransformBase(BaseModel):
    order: int
    fn: str
    params: Optional[Dict[str, Any]] = None


class TransformResponse(TransformBase):
    id: int
    mapping_id: int

    class Config:
        from_attributes = True


class SuggestionResponse(BaseModel):
    id: int
    mapping_id: int
    candidates: List[Dict[str, Any]]

    class Config:
        from_attributes = True


class SelectionOption(BaseModel):
    value: str
    label: str


class CustomFieldDefinition(BaseModel):
    technical_name: str
    field_label: str
    field_type: str  # Char, Integer, Float, Boolean, Date, Datetime, Text, Html, Selection, Many2one, Monetary
    required: bool = False
    size: Optional[int] = None  # For Char fields
    help_text: Optional[str] = None
    selection_options: Optional[List[SelectionOption]] = None  # For Selection fields
    related_model: Optional[str] = None  # For Many2one fields


class FieldTypeSuggestion(BaseModel):
    field_type: str
    suggested_size: Optional[int] = None
    selection_options: Optional[List[Dict[str, str]]] = None
    required: bool = False
    rationale: str


class MappingBase(BaseModel):
    header_name: str
    target_model: Optional[str] = None
    target_field: Optional[str] = None
    confidence: Optional[float] = None
    status: MappingStatus = MappingStatus.PENDING
    rationale: Optional[str] = None


class MappingUpdate(BaseModel):
    target_model: Optional[str] = None
    target_field: Optional[str] = None
    status: Optional[MappingStatus] = None
    chosen: Optional[bool] = None
    custom_field_definition: Optional[CustomFieldDefinition] = None


class MappingResponse(MappingBase):
    id: int
    dataset_id: int
    sheet_id: int
    chosen: bool
    transforms: List[TransformResponse] = []
    suggestions: List[SuggestionResponse] = []
    custom_field_definition: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class MappingListResponse(BaseModel):
    mappings: List[MappingResponse]
    total: int
