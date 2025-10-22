"""
Pytest fixtures for matcher validation tests.

Provides shared fixtures for HybridMatcher tests to avoid duplication and fixture errors.
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.hybrid_matcher import HybridMatcher
from ground_truth import GROUND_TRUTH


DICTIONARY_PATH = BACKEND_DIR.parent / "odoo-dictionary"


@pytest.fixture(scope="session")
def dictionary_path():
    """Path to odoo-dictionary folder."""
    return DICTIONARY_PATH


@pytest.fixture(scope="session")
def matcher(dictionary_path):
    """
    Initialize HybridMatcher with knowledge base.

    Session-scoped to avoid reloading knowledge base for every test.
    """
    return HybridMatcher(dictionary_path=dictionary_path)


@pytest.fixture
def customers_df():
    """Sample customer dataframe for testing."""
    return pd.DataFrame({
        "Customer Name": ["Acme Corp", "TechStart Inc"],
        "Contact Email": ["sales@acme.com", "hello@techstart.com"],
        "Phone": ["+1-555-0100", "+1-555-0200"],
        "Street Address": ["123 Main St", "456 Tech Blvd"],
        "City": ["New York", "San Francisco"],
        "State": ["NY", "CA"],
        "Zip Code": ["10001", "94102"],
        "Annual Revenue": [1000000, 500000],
        "Customer ID": ["CUST001", "CUST002"],
    })


@pytest.fixture
def products_df():
    """Sample product dataframe for testing."""
    return pd.DataFrame({
        "Product Name": ["Widget A", "Gadget B"],
        "SKU": ["WID-001", "GAD-002"],
        "Sale Price": [99.99, 149.99],
        "Cost Price": [50.00, 75.00],
        "Category": ["Electronics", "Tools"],
        "Barcode": ["1234567890123", "9876543210987"],
        "Active": [True, True],
    })


@pytest.fixture
def sales_orders_df():
    """Sample sales order dataframe for testing."""
    return pd.DataFrame({
        "Order Number": ["SO001", "SO002"],
        "Customer": ["Acme Corp", "TechStart Inc"],
        "Order Date": ["2024-01-15", "2024-01-20"],
        "Total": [1250.00, 2500.00],
        "Status": ["sale", "draft"],
        "Salesperson": ["John Doe", "Jane Smith"],
    })


@pytest.fixture
def customers_ground_truth():
    """Ground truth mappings for customer data."""
    return GROUND_TRUTH["customers"]


@pytest.fixture
def products_ground_truth():
    """Ground truth mappings for product data."""
    return GROUND_TRUTH["products"]


@pytest.fixture
def sales_orders_ground_truth():
    """Ground truth mappings for sales order data."""
    return GROUND_TRUTH["sales_orders"]


@pytest.fixture(params=[
    ("customers", "customers_df", "customers_ground_truth"),
    ("products", "products_df", "products_ground_truth"),
    ("sales_orders", "sales_orders_df", "sales_orders_ground_truth"),
])
def test_case(request):
    """
    Parametrized fixture providing test cases.

    Returns: (test_name, df_fixture_name, ground_truth_fixture_name)
    """
    return request.param


# Helper fixtures for the test_matcher function parameters
@pytest.fixture
def df(request, customers_df, products_df, sales_orders_df):
    """
    Dynamically provide the correct dataframe based on test name.

    This fixture is used by test_matcher() function.
    """
    test_name = request.node.name
    if "customer" in test_name.lower():
        return customers_df
    elif "product" in test_name.lower():
        return products_df
    elif "order" in test_name.lower() or "sale" in test_name.lower():
        return sales_orders_df
    else:
        # Default fallback
        return customers_df


@pytest.fixture
def ground_truth(request, customers_ground_truth, products_ground_truth, sales_orders_ground_truth):
    """
    Dynamically provide the correct ground truth based on test name.

    This fixture is used by test_matcher() function.
    """
    test_name = request.node.name
    if "customer" in test_name.lower():
        return customers_ground_truth
    elif "product" in test_name.lower():
        return products_ground_truth
    elif "order" in test_name.lower() or "sale" in test_name.lower():
        return sales_orders_ground_truth
    else:
        # Default fallback
        return customers_ground_truth


@pytest.fixture
def test_name(request):
    """Provide test name as a fixture."""
    return request.node.name
