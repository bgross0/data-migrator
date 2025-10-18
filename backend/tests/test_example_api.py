"""
Example API tests demonstrating best practices.

This module shows how to write tests for FastAPI endpoints using the test fixtures
from conftest.py.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.source import Dataset


@pytest.mark.unit
class TestDatasetAPI:
    """Tests for Dataset API endpoints."""

    def test_health_check(self, client: TestClient):
        """Test the health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_list_datasets_empty(self, client: TestClient):
        """Test listing datasets when database is empty."""
        response = client.get("/api/v1/datasets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_dataset(self, client: TestClient, sample_dataset_data: dict):
        """Test creating a new dataset."""
        response = client.post("/api/v1/datasets", json=sample_dataset_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_dataset_data["name"]
        assert data["description"] == sample_dataset_data["description"]
        assert "id" in data
        assert "created_at" in data

    def test_create_dataset_validation_error(self, client: TestClient):
        """Test that invalid dataset data returns 422 validation error."""
        invalid_data = {"name": ""}  # Empty name should fail validation
        response = client.post("/api/v1/datasets", json=invalid_data)
        assert response.status_code == 422

    def test_get_dataset_not_found(self, client: TestClient):
        """Test getting a non-existent dataset returns 404."""
        response = client.get("/api/v1/datasets/99999")
        assert response.status_code == 404

    def test_get_dataset_by_id(self, client: TestClient, sample_dataset_data: dict):
        """Test retrieving a dataset by ID."""
        # Create a dataset first
        create_response = client.post("/api/v1/datasets", json=sample_dataset_data)
        dataset_id = create_response.json()["id"]

        # Retrieve it
        response = client.get(f"/api/v1/datasets/{dataset_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == dataset_id
        assert data["name"] == sample_dataset_data["name"]

    def test_update_dataset(self, client: TestClient, sample_dataset_data: dict):
        """Test updating a dataset."""
        # Create a dataset
        create_response = client.post("/api/v1/datasets", json=sample_dataset_data)
        dataset_id = create_response.json()["id"]

        # Update it
        updated_data = {"name": "Updated Name", "description": "Updated description"}
        response = client.put(f"/api/v1/datasets/{dataset_id}", json=updated_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == updated_data["name"]
        assert data["description"] == updated_data["description"]

    def test_delete_dataset(self, client: TestClient, sample_dataset_data: dict):
        """Test deleting a dataset."""
        # Create a dataset
        create_response = client.post("/api/v1/datasets", json=sample_dataset_data)
        dataset_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/v1/datasets/{dataset_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/v1/datasets/{dataset_id}")
        assert get_response.status_code == 404


@pytest.mark.integration
class TestDatasetIntegration:
    """Integration tests for Dataset functionality."""

    def test_dataset_lifecycle(self, client: TestClient):
        """Test the complete lifecycle of a dataset: create, read, update, delete."""
        # Create
        create_data = {
            "name": "Lifecycle Test Dataset",
            "description": "Testing full CRUD lifecycle",
            "source_type": "csv",
        }
        create_response = client.post("/api/v1/datasets", json=create_data)
        assert create_response.status_code == 201
        dataset_id = create_response.json()["id"]

        # Read
        read_response = client.get(f"/api/v1/datasets/{dataset_id}")
        assert read_response.status_code == 200
        assert read_response.json()["name"] == create_data["name"]

        # Update
        update_data = {"name": "Updated Lifecycle Test"}
        update_response = client.put(f"/api/v1/datasets/{dataset_id}", json=update_data)
        assert update_response.status_code == 200
        assert update_response.json()["name"] == update_data["name"]

        # List
        list_response = client.get("/api/v1/datasets")
        assert list_response.status_code == 200
        datasets = list_response.json()
        assert any(d["id"] == dataset_id for d in datasets)

        # Delete
        delete_response = client.delete(f"/api/v1/datasets/{dataset_id}")
        assert delete_response.status_code == 204

        # Verify deletion
        get_after_delete = client.get(f"/api/v1/datasets/{dataset_id}")
        assert get_after_delete.status_code == 404
