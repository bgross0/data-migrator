"""
Odoo connector - JSON-RPC client for Odoo integration.
"""
import requests
from typing import List, Dict, Any, Optional
from app.core.config import settings


class OdooConnector:
    """Client for connecting to Odoo via JSON-RPC."""

    def __init__(
        self,
        url: Optional[str] = None,
        db: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.url = url or settings.ODOO_URL
        self.db = db or settings.ODOO_DB
        self.username = username or settings.ODOO_USERNAME
        self.password = password or settings.ODOO_PASSWORD
        self.uid: Optional[int] = None
        self.session = requests.Session()

    def authenticate(self) -> int:
        """Authenticate with Odoo and return user ID."""
        response = self._call("common", "authenticate", [
            self.db,
            self.username,
            self.password,
            {}
        ])
        self.uid = response
        return self.uid

    def search_read(
        self,
        model: str,
        domain: List = None,
        fields: List[str] = None,
        limit: int = None,
    ) -> List[Dict[str, Any]]:
        """Search and read records from Odoo."""
        if not self.uid:
            self.authenticate()

        params = {
            "domain": domain or [],
            "fields": fields or [],
        }
        if limit:
            params["limit"] = limit

        return self._call("object", "execute_kw", [
            self.db,
            self.uid,
            self.password,
            model,
            "search_read",
            [],
            params,
        ])

    def create(self, model: str, values: Dict[str, Any]) -> int:
        """Create a record in Odoo."""
        if not self.uid:
            self.authenticate()

        return self._call("object", "execute_kw", [
            self.db,
            self.uid,
            self.password,
            model,
            "create",
            [values],
        ])

    def write(self, model: str, record_id: int, values: Dict[str, Any]) -> bool:
        """Update a record in Odoo."""
        if not self.uid:
            self.authenticate()

        return self._call("object", "execute_kw", [
            self.db,
            self.uid,
            self.password,
            model,
            "write",
            [[record_id], values],
        ])

    def upsert(
        self,
        model: str,
        values: Dict[str, Any],
        lookup_field: str,
        lookup_value: Any,
    ) -> tuple[int, str]:
        """
        Create or update a record based on lookup field.

        Returns:
            (record_id, operation) where operation is "create" or "update"
        """
        existing = self.search_read(
            model,
            domain=[(lookup_field, "=", lookup_value)],
            fields=["id"],
            limit=1,
        )

        if existing:
            record_id = existing[0]["id"]
            self.write(model, record_id, values)
            return record_id, "update"
        else:
            record_id = self.create(model, {**values, lookup_field: lookup_value})
            return record_id, "create"

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Odoo.

        Returns:
            Dict with status and message
        """
        try:
            uid = self.authenticate()
            if uid:
                return {
                    "status": "success",
                    "message": f"Connected successfully as user ID {uid}",
                    "user_id": uid
                }
            else:
                return {
                    "status": "error",
                    "message": "Authentication failed - invalid credentials"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get_model_id(self, model_name: str) -> Optional[int]:
        """
        Get the ir.model ID for a given model name.

        Args:
            model_name: Technical name of the model (e.g., 'res.partner')

        Returns:
            Model ID or None if not found
        """
        if not self.uid:
            self.authenticate()

        models = self.search_read(
            "ir.model",
            domain=[("model", "=", model_name)],
            fields=["id"],
            limit=1
        )

        if models:
            return models[0]["id"]
        return None

    def create_custom_field(
        self,
        model_name: str,
        field_name: str,
        field_label: str,
        field_type: str,
        required: bool = False,
        **kwargs
    ) -> int:
        """
        Create a custom field in Odoo via ir.model.fields.

        Args:
            model_name: Target model (e.g., 'res.partner')
            field_name: Technical field name (must start with 'x_')
            field_label: User-friendly label
            field_type: Odoo field type (char, integer, float, etc.)
            required: Whether field is required
            **kwargs: Additional field parameters (size, selection, etc.)

        Returns:
            ID of created field

        Raises:
            Exception: If field creation fails
        """
        if not self.uid:
            self.authenticate()

        # Get model ID
        model_id = self.get_model_id(model_name)
        if not model_id:
            raise Exception(f"Model '{model_name}' not found in Odoo")

        # Check if field already exists
        existing = self.search_read(
            "ir.model.fields",
            domain=[("model", "=", model_name), ("name", "=", field_name)],
            fields=["id"],
            limit=1
        )

        if existing:
            return existing[0]["id"]

        # Prepare field values
        values = {
            "model_id": model_id,
            "model": model_name,
            "name": field_name,
            "field_description": field_label,
            "ttype": field_type,
            "required": required,
            "state": "manual",  # Mark as custom field
        }

        # Add type-specific parameters
        if field_type == "char" and "size" in kwargs:
            values["size"] = kwargs["size"]

        if field_type == "selection" and "selection" in kwargs:
            values["selection"] = str(kwargs["selection"])

        if field_type == "many2one" and "relation" in kwargs:
            values["relation"] = kwargs["relation"]

        if "help" in kwargs:
            values["help"] = kwargs["help"]

        # Create the field
        field_id = self.create("ir.model.fields", values)
        return field_id

    def get_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch Odoo model and field metadata.

        Returns:
            Dict of {model_name: {field_name: field_info}}
        """
        if not self.uid:
            self.authenticate()

        # TODO: Implement metadata fetching
        # 1. Call ir.model to get all models
        # 2. Call ir.model.fields for each model
        # 3. Build and cache metadata structure

        return {}

    def _call(self, service: str, method: str, args: List) -> Any:
        """Make JSON-RPC call to Odoo."""
        endpoint = f"{self.url}/jsonrpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": args,
            },
            "id": 1,
        }

        response = self.session.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            raise Exception(f"Odoo error: {result['error']}")

        return result.get("result")
