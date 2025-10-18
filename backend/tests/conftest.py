"""
Pytest configuration and shared fixtures for Data Migrator tests.

This file provides common test fixtures and configuration that can be used
across all test modules.
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


# ===========================
# Database Fixtures
# ===========================


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """
    Create a fresh in-memory SQLite database for each test.

    This fixture:
    - Creates an in-memory database
    - Sets up all tables
    - Yields a database session
    - Tears down the database after the test

    Usage:
        def test_something(test_db):
            # Use test_db as a SQLAlchemy session
            user = User(name="Test")
            test_db.add(user)
            test_db.commit()
    """
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """
    Create a FastAPI test client with a test database.

    This fixture:
    - Overrides the database dependency
    - Provides a test client for making API requests

    Usage:
        def test_api_endpoint(client):
            response = client.get("/api/v1/datasets")
            assert response.status_code == 200
    """

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ===========================
# File System Fixtures
# ===========================


@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test files.

    Usage:
        def test_file_operations(temp_dir):
            test_file = temp_dir / "test.csv"
            test_file.write_text("data")
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="function")
def sample_csv_file(temp_dir: Path) -> Path:
    """
    Create a sample CSV file for testing.

    Returns:
        Path to the created CSV file
    """
    csv_path = temp_dir / "sample.csv"
    csv_content = """Name,Email,Phone,Company
John Doe,john@example.com,555-1234,Acme Corp
Jane Smith,jane@example.com,555-5678,Tech Inc
Bob Johnson,bob@example.com,555-9012,Data LLC"""
    csv_path.write_text(csv_content)
    return csv_path


@pytest.fixture(scope="function")
def sample_excel_file(temp_dir: Path) -> Path:
    """
    Create a sample Excel file for testing.

    Returns:
        Path to the created Excel file
    """
    import pandas as pd

    excel_path = temp_dir / "sample.xlsx"
    df = pd.DataFrame(
        {
            "Name": ["John Doe", "Jane Smith", "Bob Johnson"],
            "Email": ["john@example.com", "jane@example.com", "bob@example.com"],
            "Phone": ["555-1234", "555-5678", "555-9012"],
            "Company": ["Acme Corp", "Tech Inc", "Data LLC"],
        }
    )
    df.to_excel(excel_path, index=False)
    return excel_path


# ===========================
# Mock Data Fixtures
# ===========================


@pytest.fixture
def sample_dataset_data() -> dict:
    """
    Sample dataset data for testing.

    Returns:
        Dictionary with dataset fields
    """
    return {
        "name": "Test Dataset",
        "description": "A test dataset",
        "source_type": "csv",
    }


@pytest.fixture
def sample_mapping_data() -> dict:
    """
    Sample field mapping data for testing.

    Returns:
        Dictionary with mapping fields
    """
    return {
        "dataset_id": 1,
        "target_model": "res.partner",
        "field_mappings": [
            {
                "source_column": "Name",
                "target_field": "name",
                "transform": None,
            },
            {
                "source_column": "Email",
                "target_field": "email",
                "transform": "email_normalize",
            },
            {
                "source_column": "Phone",
                "target_field": "phone",
                "transform": "phone_normalize",
            },
        ],
    }


# ===========================
# Environment Fixtures
# ===========================


@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """
    Set environment variables for testing.

    This fixture runs automatically for all tests.
    """
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"


# ===========================
# Marker Configuration
# ===========================


def pytest_configure(config):
    """
    Register custom pytest markers.
    """
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (may require external services)"
    )
    config.addinivalue_line("markers", "slow: Slow tests (> 1 second)")
    config.addinivalue_line("markers", "asyncio: Async tests")


# ===========================
# Async Fixtures
# ===========================


@pytest.fixture
async def async_client(test_db: Session) -> Generator:
    """
    Create an async test client for testing async endpoints.

    Usage:
        @pytest.mark.asyncio
        async def test_async_endpoint(async_client):
            response = await async_client.get("/api/v1/async-endpoint")
            assert response.status_code == 200
    """
    from httpx import AsyncClient

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
