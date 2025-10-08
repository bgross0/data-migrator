"""
Two-phase import executor - handles parent/child import ordering with relationship resolution.
"""
from typing import Dict, List, Any
from app.connectors.odoo import OdooConnector
from app.models import KeyMap, Run
from sqlalchemy.orm import Session


class TwoPhaseImporter:
    """
    Executes imports in two phases:
    1. Phase A: Import parent entities, build KeyMap
    2. Phase B: Import child entities using KeyMap for foreign keys
    """

    def __init__(self, db: Session, odoo: OdooConnector, run: Run):
        self.db = db
        self.odoo = odoo
        self.run = run

    def execute(self, graph: List[str], data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Execute import according to graph order.

        Args:
            graph: List of model names in topological order
            data: Dict of {model_name: [records to import]}

        Returns:
            Stats dict with created/updated/error counts
        """
        stats = {
            "created": 0,
            "updated": 0,
            "errors": 0,
            "by_model": {},
        }

        for model in graph:
            if model not in data:
                continue

            model_stats = self._import_model(model, data[model])
            stats["created"] += model_stats["created"]
            stats["updated"] += model_stats["updated"]
            stats["errors"] += model_stats["errors"]
            stats["by_model"][model] = model_stats

        return stats

    def _import_model(self, model: str, records: List[Dict]) -> Dict[str, int]:
        """Import records for a single model."""
        stats = {"created": 0, "updated": 0, "errors": 0}

        for record in records:
            try:
                # Resolve foreign keys using KeyMap
                resolved = self._resolve_relationships(model, record)

                # Upsert to Odoo
                lookup_field = self._get_lookup_field(model, record)
                lookup_value = record.get(lookup_field)

                odoo_id, operation = self.odoo.upsert(
                    model,
                    resolved,
                    lookup_field,
                    lookup_value,
                )

                # Store in KeyMap
                self._store_keymap(model, record, odoo_id)

                if operation == "create":
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

            except Exception as e:
                stats["errors"] += 1
                # TODO: Log error to RunLog

        return stats

    def _resolve_relationships(self, model: str, record: Dict) -> Dict:
        """Resolve foreign key references using KeyMap."""
        # TODO: Implement relationship resolution
        # 1. Identify relationship fields in record
        # 2. Look up parent records in KeyMap
        # 3. Replace external keys with Odoo IDs
        return record

    def _get_lookup_field(self, model: str, record: Dict) -> str:
        """Get the field to use for lookup (external key)."""
        # TODO: Make this configurable per model
        # For now, assume there's an external_id or email field
        if "external_id" in record:
            return "external_id"
        if "email" in record:
            return "email"
        return "name"

    def _store_keymap(self, model: str, record: Dict, odoo_id: int):
        """Store source key -> Odoo ID mapping."""
        source_key = record.get("external_id") or record.get("email") or record.get("name")
        if not source_key:
            return

        keymap = KeyMap(
            run_id=self.run.id,
            model=model,
            source_key=str(source_key),
            odoo_id=odoo_id,
            xml_id=f"axsys.{model.replace('.', '_')}.{source_key}",
        )
        self.db.add(keymap)
        self.db.commit()
