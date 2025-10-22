"""
Pytest fixtures for API integration tests.

Provides FastAPI test client and database session fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings


# Test database setup (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.

    Creates all tables, yields session, then drops all tables.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    FastAPI test client with database dependency override.

    Uses in-memory database for isolated tests.
    """
    # Override database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up override
    app.dependency_overrides.clear()


@pytest.fixture
def sample_dataset(db_session):
    """
    Create a sample dataset in the test database.

    Returns: Dataset model instance
    """
    from app.models import Dataset, Sheet, SourceFile
    from datetime import datetime

    # Create source file
    source_file = SourceFile(
        filename="test_customers.csv",
        path="/tmp/test_customers.csv",
        size=1024,
        mime_type="text/csv"
    )
    db_session.add(source_file)
    db_session.flush()

    # Create dataset
    dataset = Dataset(
        name="Test Customers",
        source_file_id=source_file.id,
        selected_modules=["sales_crm", "contacts_partners"]
    )
    db_session.add(dataset)
    db_session.flush()

    # Create sheet
    sheet = Sheet(
        dataset_id=dataset.id,
        name="Sheet1",
        row_count=100
    )
    db_session.add(sheet)
    db_session.commit()

    return dataset


@pytest.fixture
def sample_mappings(db_session, sample_dataset):
    """
    Create sample mappings for testing.

    Returns: List of Mapping instances
    """
    from app.models import Mapping
    from app.models.mapping import MappingStatus

    sheet = sample_dataset.sheets[0]

    mappings_data = [
        {
            "header_name": "Customer Name",
            "target_model": "res.partner",
            "target_field": "name",
            "confidence": 1.0,
            "status": MappingStatus.CONFIRMED,
            "chosen": True,
            "rationale": "Exact match"
        },
        {
            "header_name": "Email",
            "target_model": "res.partner",
            "target_field": "email",
            "confidence": 1.0,
            "status": MappingStatus.CONFIRMED,
            "chosen": True,
            "rationale": "Exact match"
        },
        {
            "header_name": "Phone",
            "target_model": "res.partner",
            "target_field": "phone",
            "confidence": 0.95,
            "status": MappingStatus.PENDING,
            "chosen": False,
            "rationale": "High confidence match"
        }
    ]

    mappings = []
    for data in mappings_data:
        mapping = Mapping(
            dataset_id=sample_dataset.id,
            sheet_id=sheet.id,
            **data
        )
        db_session.add(mapping)
        mappings.append(mapping)

    db_session.commit()
    return mappings


@pytest.fixture(scope="session")
def odoo_credentials():
    """
    Odoo credentials from environment.

    NOTE: These must be set in .env or environment variables for tests to work.
    """
    return {
        "url": settings.ODOO_URL,
        "db": settings.ODOO_DB,
        "username": settings.ODOO_USERNAME,
        "password": settings.ODOO_PASSWORD
    }


@pytest.fixture
def skip_if_no_odoo(odoo_credentials):
    """
    Skip test if Odoo credentials are not configured.

    Use with: @pytest.mark.usefixtures("skip_if_no_odoo")
    """
    if not all(odoo_credentials.values()):
        pytest.skip("Odoo credentials not configured. Set ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD in .env")
