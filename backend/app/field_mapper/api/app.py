"""
FastAPI application for deterministic field mapper.

Provides REST API endpoints for field mapping operations.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from pathlib import Path
import tempfile
import shutil

from ..main import DeterministicFieldMapper
from ..core.data_structures import MappingStatus
from ..validation.constraint_validator import ConstraintValidator
from ..executor.mapping_executor import MappingExecutor
from ..config.settings import FieldMapperSettings
from ..config.logging_config import api_logger as logger

# Create FastAPI app
app = FastAPI(
    title="Deterministic Field Mapper API",
    description="API for mapping spreadsheet columns to Odoo fields",
    version="1.0.0",
)

# Global field mapper instance
_mapper: Optional[DeterministicFieldMapper] = None


def get_mapper() -> DeterministicFieldMapper:
    """Get or create global field mapper instance."""
    global _mapper
    if _mapper is None:
        settings = FieldMapperSettings()
        _mapper = DeterministicFieldMapper(
            dictionary_path=settings.odoo_dictionary_path,
            settings=settings,
        )
    return _mapper


# ===========================
# Request/Response Models
# ===========================

class MappingRequest(BaseModel):
    """Request model for mapping operations."""
    sheet_name: Optional[str] = Field(None, description="Sheet name (for Excel files)")
    target_model: Optional[str] = Field(None, description="Target Odoo model")
    confidence_threshold: Optional[float] = Field(0.6, ge=0.0, le=1.0)


class FieldMappingResponse(BaseModel):
    """Response model for field mapping."""
    source_column: str
    target_model: str
    target_field: Optional[str]
    confidence: float
    rationale: str
    matching_strategy: str
    scores: Dict[str, float]


class MappingResponse(BaseModel):
    """Response model for mapping operations."""
    status: str
    mappings: Dict[str, List[FieldMappingResponse]]
    statistics: Dict[str, Any]
    errors: List[str] = []
    warnings: List[str] = []


class ValidationRequest(BaseModel):
    """Request model for validation."""
    target_model: str
    strict: bool = Field(False, description="Fail on warnings")


class ValidationResponse(BaseModel):
    """Response model for validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    missing_required_fields: List[str]


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    knowledge_base_loaded: bool
    total_models: int
    total_fields: int
    uptime_seconds: float


# ===========================
# API Endpoints
# ===========================

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "name": "Deterministic Field Mapper API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status and system information
    """
    try:
        mapper = get_mapper()
        stats = mapper.get_statistics()

        return HealthResponse(
            status="healthy",
            knowledge_base_loaded=mapper.knowledge_base.is_loaded,
            total_models=stats["knowledge_base"]["total_models"],
            total_fields=stats["knowledge_base"]["total_fields"],
            uptime_seconds=0.0,  # TODO: Track uptime
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/map", response_model=MappingResponse)
async def map_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    sheet_name: Optional[str] = None,
):
    """
    Map a spreadsheet file to Odoo fields.

    Args:
        file: Uploaded file (Excel or CSV)
        background_tasks: Background tasks for cleanup
        sheet_name: Optional sheet name for Excel files

    Returns:
        Mapping result with field mappings
    """
    logger.info(f"Received file upload: {file.filename}")

    # Save uploaded file to temp location
    temp_dir = tempfile.mkdtemp()
    temp_file = Path(temp_dir) / file.filename

    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Get mapper and process file
        mapper = get_mapper()
        result = mapper.map_file(temp_file, sheet_name=sheet_name)

        # Convert to response model
        response_mappings = {}
        for sheet, sheet_mappings in result.mappings.items():
            response_mappings[sheet] = {}
            for col_name, field_mappings in sheet_mappings.items():
                response_mappings[sheet][col_name] = [
                    FieldMappingResponse(
                        source_column=fm.source_column,
                        target_model=fm.target_model,
                        target_field=fm.target_field,
                        confidence=fm.confidence,
                        rationale=fm.rationale,
                        matching_strategy=fm.matching_strategy,
                        scores=fm.scores,
                    )
                    for fm in field_mappings
                ]

        response = MappingResponse(
            status=result.status.value,
            mappings=response_mappings,
            statistics=result.statistics,
            errors=result.errors,
            warnings=result.warnings,
        )

        # Schedule cleanup
        if background_tasks:
            background_tasks.add_task(shutil.rmtree, temp_dir)

        logger.info(f"Mapping completed: {result.statistics}")

        return response

    except Exception as e:
        logger.error(f"Error mapping file: {e}", exc_info=True)
        # Cleanup on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/validate", response_model=ValidationResponse)
async def validate_mappings(
    mappings: Dict[str, List[FieldMappingResponse]],
    validation_request: ValidationRequest,
):
    """
    Validate field mappings against Odoo constraints.

    Args:
        mappings: Field mappings to validate
        validation_request: Validation parameters

    Returns:
        Validation result
    """
    logger.info(f"Validating mappings for model '{validation_request.target_model}'")

    try:
        mapper = get_mapper()
        validator = ConstraintValidator(mapper.knowledge_base)

        # Convert response models back to FieldMapping
        from ..core.data_structures import FieldMapping

        field_mappings = {}
        for col_name, fm_list in mappings.items():
            field_mappings[col_name] = [
                FieldMapping(
                    source_column=fm.source_column,
                    target_model=fm.target_model,
                    target_field=fm.target_field,
                    confidence=fm.confidence,
                    scores=fm.scores,
                    rationale=fm.rationale,
                    matching_strategy=fm.matching_strategy,
                    alternatives=[],
                    transformations=[],
                )
                for fm in fm_list
            ]

        # Validate
        result = validator.validate_mappings(
            field_mappings,
            validation_request.target_model
        )

        # Check strict mode
        if validation_request.strict and result.warnings:
            result.is_valid = False
            result.errors.extend(result.warnings)

        response = ValidationResponse(
            is_valid=result.is_valid,
            errors=result.errors,
            warnings=result.warnings,
            suggestions=[s.description for s in result.suggestions],
            missing_required_fields=result.missing_required_fields,
        )

        logger.info(f"Validation complete: valid={result.is_valid}")

        return response

    except Exception as e:
        logger.error(f"Error validating mappings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/models", response_model=List[str])
async def get_models():
    """
    Get list of all Odoo models.

    Returns:
        List of model names
    """
    try:
        mapper = get_mapper()
        models = list(mapper.knowledge_base.models.keys())
        return models
    except Exception as e:
        logger.error(f"Error getting models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/models/{model_name}/fields", response_model=List[Dict[str, Any]])
async def get_model_fields(model_name: str):
    """
    Get all fields for a specific model.

    Args:
        model_name: Odoo model name

    Returns:
        List of field definitions
    """
    try:
        mapper = get_mapper()
        fields = mapper.knowledge_base.get_model_fields(model_name)

        return [
            {
                "name": f.name,
                "label": f.label,
                "field_type": f.field_type,
                "is_required": f.is_required,
                "is_readonly": f.is_readonly,
                "related_model": f.related_model,
            }
            for f in fields
        ]
    except Exception as e:
        logger.error(f"Error getting fields: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/statistics", response_model=Dict[str, Any])
async def get_statistics():
    """
    Get system statistics.

    Returns:
        Statistics about the field mapper
    """
    try:
        mapper = get_mapper()
        stats = mapper.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/reload")
async def reload_knowledge_base():
    """
    Reload the knowledge base from dictionary files.

    Returns:
        Success message
    """
    try:
        mapper = get_mapper()
        mapper.reload_knowledge_base()
        return {"status": "success", "message": "Knowledge base reloaded"}
    except Exception as e:
        logger.error(f"Error reloading knowledge base: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Error Handlers
# ===========================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
