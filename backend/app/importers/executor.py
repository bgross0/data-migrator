"""
Two-phase import executor - handles parent/child import ordering with relationship resolution.

Enhanced with:
- Identity resolution (natural key + content hashing)
- Pre/post-load validation
- Quarantine workflow for failed records
- Collision handling for multi-match scenarios
"""
from typing import Dict, List, Any, Optional
from app.connectors.odoo import OdooConnector
from app.models import KeyMap, Run
from app.models.run import RunLog, LogLevel
from sqlalchemy.orm import Session

# Import enhanced services
from app.services.validator_service import ValidatorService, ValidationResult
from app.services.quarantine_service import QuarantineService, QuarantineReason
from app.services.collision_handler import CollisionHandler
from app.core.normalization import NaturalKeyGenerator, ContentHasher


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

        # Initialize enhanced services
        self.validator = ValidatorService(db)
        self.quarantine = QuarantineService(db)
        self.collision_handler = CollisionHandler(db)

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
                error_message = f"{model}: {e}"

                # Log error to RunLog
                self.db.add(
                    RunLog(
                        run_id=self.run.id,
                        level=LogLevel.ERROR,
                        message=error_message,
                        row_ref={"record": record},
                    )
                )
                self.db.commit()

                # Quarantine failed record for manual review
                try:
                    self.quarantine.quarantine_record(
                        source_record=record,
                        odoo_model=model,
                        run_id=self.run.id,
                        batch_id="batch_default",  # TODO: Use actual batch_id when available
                        reason=QuarantineReason.VALIDATION_FAILED,
                        details={
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    )
                except Exception as qe:
                    # Don't fail entire import if quarantine fails
                    print(f"Failed to quarantine record: {qe}")

        return stats

    def _resolve_relationships(self, model: str, record: Dict) -> Dict:
        """
        Resolve foreign key references using KeyMap.

        For fields ending in '_id', looks up the Odoo ID from KeyMap
        based on the source value and replaces it.

        Args:
            model: Target Odoo model
            record: Record dict with source values

        Returns:
            Record dict with resolved Odoo IDs for relationship fields
        """
        resolved = record.copy()

        # Common relationship field mappings
        relationship_mappings = {
            "partner_id": "res.partner",
            "user_id": "res.users",
            "company_id": "res.company",
            "product_id": "product.product",
            "product_tmpl_id": "product.template",
            "project_id": "project.project",
            "task_id": "project.task",
            "order_id": "sale.order",
            "invoice_id": "account.move",
            "parent_id": model,  # Same model (hierarchical)
        }

        for field_name, value in record.items():
            # Check if this is a relationship field
            if field_name.endswith("_id") and value:
                # Determine parent model
                parent_model = relationship_mappings.get(field_name)

                if not parent_model:
                    # Try to infer from field name (e.g., "customer_id" -> "res.partner")
                    # For now, skip unknown relationship fields
                    continue

                # Look up in KeyMap
                keymap = self.db.query(KeyMap).filter(
                    KeyMap.run_id == self.run.id,
                    KeyMap.model == parent_model,
                    KeyMap.source_key == str(value)
                ).first()

                if keymap and keymap.odoo_id:
                    # Replace with Odoo ID
                    resolved[field_name] = keymap.odoo_id
                else:
                    # Parent not found - remove field or handle error
                    # For now, keep original value and let Odoo handle it
                    pass

        return resolved

    def _get_lookup_field(self, model: str, record: Dict) -> str:
        """Get the field to use for lookup (external key)."""
        # TODO: Make this configurable per model
        # For now, assume there's an external_id or email field
        if "external_id" in record:
            return "external_id"
        if "email" in record:
            return "email"
        return "name"

    def _store_keymap(
        self,
        model: str,
        record: Dict,
        odoo_id: int,
        natural_key_hash: Optional[str] = None,
        content_hash: Optional[str] = None,
        match_confidence: Optional[float] = None,
        match_method: Optional[str] = None
    ):
        """
        Store source key -> Odoo ID mapping with enhanced identity resolution fields.

        Args:
            model: Odoo model name
            record: Source record
            odoo_id: Odoo record ID
            natural_key_hash: MD5 hash of natural key components
            content_hash: MD5 hash of content for change detection
            match_confidence: Match confidence score (0.0-1.0)
            match_method: How it was matched (exact, fuzzy, manual, etc.)
        """
        source_key = record.get("external_id") or record.get("email") or record.get("name")
        if not source_key:
            return

        # Generate natural key hash if not provided
        if not natural_key_hash:
            natural_key_hash = self._generate_natural_key(model, record)

        # Generate content hash if not provided
        if not content_hash:
            content_hash = ContentHasher.hash_record(record)

        keymap = KeyMap(
            run_id=self.run.id,
            model=model,
            source_key=str(source_key),
            odoo_id=odoo_id,
            xml_id=f"axsys.{model.replace('.', '_')}.{source_key}",
            natural_key_hash=natural_key_hash,
            content_hash=content_hash,
            match_confidence=match_confidence or 1.0,  # Default to 1.0 for direct imports
            match_method=match_method or "direct_import",
        )
        self.db.add(keymap)
        self.db.commit()

    def _generate_natural_key(self, model: str, record: Dict) -> str:
        """
        Generate natural key hash for a record based on model type.

        Args:
            model: Odoo model name
            record: Source record

        Returns:
            MD5 hash of natural key components
        """
        if model == "res.partner":
            # Check if company or contact
            is_company = record.get("is_company", True)

            if is_company:
                return NaturalKeyGenerator.generate_partner_company_key(
                    vat=record.get("vat"),
                    name=record.get("name"),
                    street=record.get("street"),
                    city=record.get("city"),
                    state_code=record.get("state_id"),
                    country_code=record.get("country_id"),
                    phone=record.get("phone"),
                    email=record.get("email"),
                )
            else:
                return NaturalKeyGenerator.generate_partner_contact_key(
                    parent_id=record.get("parent_id", 0),
                    full_name=record.get("name", ""),
                    email=record.get("email"),
                    phone=record.get("phone"),
                )

        elif model == "crm.lead":
            return NaturalKeyGenerator.generate_lead_key(
                external_id=record.get("external_id"),
                partner_id=record.get("partner_id"),
                name=record.get("name"),
                email_from=record.get("email_from"),
                create_date=record.get("create_date"),
            )

        # For other models, fallback to content hash
        return ContentHasher.hash_record(record)

    def validate_before_batch(
        self,
        batch_num: int,
        models: List[str]
    ) -> List[ValidationResult]:
        """
        Run pre-load validation before importing a batch.

        Args:
            batch_num: Batch number
            models: Models in this batch

        Returns:
            List of ValidationResult
        """
        results = self.validator.validate_batch_preload(batch_num, models)

        # Log validation results
        summary = self.validator.get_validation_summary(results)
        if not summary['all_passed']:
            self.db.add(
                RunLog(
                    run_id=self.run.id,
                    level=LogLevel.WARNING,
                    message=f"Batch {batch_num} pre-validation: {summary['failed']} checks failed",
                    row_ref={"summary": summary},
                )
            )
            self.db.commit()

        return results

    def validate_after_batch(
        self,
        batch_num: int,
        models: List[str],
        batch_id: str
    ) -> List[ValidationResult]:
        """
        Run post-load validation after importing a batch.

        Args:
            batch_num: Batch number
            models: Models in this batch
            batch_id: Batch ID

        Returns:
            List of ValidationResult
        """
        results = self.validator.validate_batch_postload(batch_num, models, batch_id)

        # Log validation results
        summary = self.validator.get_validation_summary(results)
        if not summary['all_passed']:
            self.db.add(
                RunLog(
                    run_id=self.run.id,
                    level=LogLevel.ERROR,
                    message=f"Batch {batch_num} post-validation: {summary['failed']} checks failed",
                    row_ref={"summary": summary},
                )
            )
            self.db.commit()

        return results
