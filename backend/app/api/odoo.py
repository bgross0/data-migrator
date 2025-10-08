from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from app.core.database import get_db
from app.models import OdooConnection
from app.connectors.odoo import OdooConnector
from app.services.odoo_field_service import OdooFieldService

router = APIRouter()


# Schemas
class OdooConnectionCreate(BaseModel):
    name: str
    url: str
    database: str
    username: str
    password: str
    is_default: bool = False


class OdooConnectionResponse(BaseModel):
    id: int
    name: str
    url: str
    database: str
    username: str
    is_default: bool
    is_active: bool
    last_tested_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class OdooConnectionTest(BaseModel):
    url: str
    database: str
    username: str
    password: str


class TestConnectionResponse(BaseModel):
    status: str
    message: str
    user_id: int | None = None


class CreateFieldsResponse(BaseModel):
    success: bool
    created: int
    failed: int
    total: int
    results: List[dict]


# Endpoints
@router.post("/odoo/test-connection", response_model=TestConnectionResponse)
async def test_connection(connection: OdooConnectionTest):
    """Test connection to Odoo instance."""
    try:
        connector = OdooConnector(
            url=connection.url,
            db=connection.database,
            username=connection.username,
            password=connection.password
        )

        result = connector.test_connection()
        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "user_id": None
        }


@router.post("/odoo/connections", response_model=OdooConnectionResponse)
async def create_connection(
    connection: OdooConnectionCreate,
    db: Session = Depends(get_db)
):
    """Create a new Odoo connection configuration."""
    # If setting as default, unset any other default
    if connection.is_default:
        db.query(OdooConnection).update({"is_default": False})

    new_connection = OdooConnection(
        name=connection.name,
        url=connection.url,
        database=connection.database,
        username=connection.username,
        password=connection.password,  # TODO: Encrypt password
        is_default=connection.is_default,
        last_tested_at=datetime.utcnow()  # Set since we just tested it
    )

    db.add(new_connection)
    db.commit()
    db.refresh(new_connection)

    return new_connection


@router.get("/odoo/connections", response_model=List[OdooConnectionResponse])
async def list_connections(
    db: Session = Depends(get_db)
):
    """List all Odoo connection configurations."""
    connections = db.query(OdooConnection).filter(
        OdooConnection.is_active == True
    ).all()

    return connections


@router.get("/odoo/connections/{connection_id}", response_model=OdooConnectionResponse)
async def get_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific Odoo connection configuration."""
    connection = db.query(OdooConnection).filter(
        OdooConnection.id == connection_id
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    return connection


@router.delete("/odoo/connections/{connection_id}")
async def delete_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Delete an Odoo connection configuration."""
    connection = db.query(OdooConnection).filter(
        OdooConnection.id == connection_id
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Soft delete
    connection.is_active = False
    db.commit()

    return {"status": "deleted"}


@router.post("/datasets/{dataset_id}/create-custom-fields", response_model=CreateFieldsResponse)
async def create_custom_fields(
    dataset_id: int,
    connection_id: int | None = None,
    db: Session = Depends(get_db)
):
    """
    Create custom fields in Odoo for a dataset.

    Uses the default connection if connection_id is not provided.
    """
    # Get Odoo connection
    if connection_id:
        connection = db.query(OdooConnection).filter(
            OdooConnection.id == connection_id
        ).first()
    else:
        connection = db.query(OdooConnection).filter(
            OdooConnection.is_default == True
        ).first()

    if not connection:
        raise HTTPException(
            status_code=404,
            detail="No Odoo connection found. Please configure a connection first."
        )

    # Create Odoo connector
    connector = OdooConnector(
        url=connection.url,
        db=connection.database,
        username=connection.username,
        password=connection.password  # TODO: Decrypt password
    )

    # Test connection first
    test_result = connector.test_connection()
    if test_result["status"] != "success":
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to Odoo: {test_result['message']}"
        )

    # Create fields
    field_service = OdooFieldService(db)
    result = field_service.create_custom_fields_for_dataset(dataset_id, connector)

    return result
