"""
Service for managing import templates
"""
import json
from pathlib import Path
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.schemas.template import Template, TemplateListItem, TemplateProgress
from app.services.graph_service import GraphService
from app.schemas.graph import GraphSpecCreate, GraphNode, GraphEdge, GraphNodeData, GraphEdgeData
from app.registry.loader import RegistryLoader


class TemplateService:
    """Service for loading and managing import templates"""

    def __init__(self, db: Session, templates_dir: Optional[Path] = None):
        self.db = db
        self.templates_dir = templates_dir or Path(__file__).parent.parent.parent / "templates"
        self.graph_service = GraphService(db)

        # Initialize registry loader
        registry_path = Path(__file__).parent.parent.parent / "registry" / "odoo.yaml"
        self.registry_loader = RegistryLoader(registry_path)

    def list_templates(self, category: Optional[str] = None) -> List[TemplateListItem]:
        """
        List all available templates

        Args:
            category: Optional filter by category

        Returns:
            List of template summaries
        """
        templates = []

        if not self.templates_dir.exists():
            return templates

        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, "r") as f:
                    data = json.load(f)

                # Filter by category if specified
                if category and data.get("category") != category:
                    continue

                templates.append(TemplateListItem(
                    id=data["id"],
                    name=data["name"],
                    description=data["description"],
                    category=data["category"],
                    icon=data.get("icon"),
                    estimatedTime=data["estimatedTime"],
                    difficulty=data["difficulty"],
                    modelCount=len(data["models"]),
                    completed=False  # TODO: Check against completed runs
                ))
            except Exception as e:
                print(f"Error loading template {template_file}: {e}")
                continue

        # Sort by priority (if available) then by name
        templates.sort(key=lambda t: (
            -1 * self._get_priority(t.id),
            t.name
        ))

        return templates

    def get_template(self, template_id: str) -> Optional[Template]:
        """
        Get a specific template by ID

        Args:
            template_id: Template identifier

        Returns:
            Template object or None
        """
        template_file = self.templates_dir / f"{template_id.replace('template_', '')}.json"

        if not template_file.exists():
            return None

        try:
            with open(template_file, "r") as f:
                data = json.load(f)

            return Template(**data)
        except Exception as e:
            print(f"Error loading template {template_id}: {e}")
            return None

    def get_template_progress(self, template_id: str) -> Optional[TemplateProgress]:
        """
        Get progress for a template based on completed runs

        Args:
            template_id: Template identifier

        Returns:
            Progress information
        """
        template = self.get_template(template_id)
        if not template:
            return None

        # TODO: Query GraphRun table to find completed models
        # For now, return zero progress
        return TemplateProgress(
            templateId=template_id,
            completedModels=[],
            totalModels=len(template.models),
            percentComplete=0
        )

    def instantiate_template(
        self,
        template_id: str,
        dataset_id: Optional[int] = None,
        custom_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a Graph from a template

        Args:
            template_id: Template to instantiate
            dataset_id: Optional dataset to link
            custom_name: Optional custom name for the graph

        Returns:
            Created graph ID or None
        """
        template = self.get_template(template_id)
        if not template:
            return None

        # Load registry to get model specs
        registry = self.registry_loader.load()

        # Build GraphSpec from template
        nodes = []
        edges = []

        # Create nodes for each model in template
        for i, model_name in enumerate(template.models):
            model_spec = registry.models.get(model_name)

            # Create a loader node for each model
            node = GraphNode(
                id=f"loader_{model_name.replace('.', '_')}",
                kind="loader",
                label=f"Import {model_name}",
                data=GraphNodeData(
                    odooModel=model_name,
                    upsertKey=["id"] if model_spec else None
                ),
                position={"x": 100, "y": i * 100}
            )
            nodes.append(node)

            # Create edges based on dependencies
            if model_spec:
                for field_name, field_spec in model_spec.fields.items():
                    if field_spec.type == "m2o" and field_spec.target:
                        # Find the parent node
                        parent_node_id = f"loader_{field_spec.target.replace('.', '_')}"
                        if parent_node_id in [n.id for n in nodes]:
                            edge = GraphEdge(
                                id=f"edge_{parent_node_id}_to_{node.id}",
                                from_=parent_node_id,
                                to=node.id,
                                kind="depends",
                                data=GraphEdgeData()
                            )
                            edges.append(edge)

        # Create the graph
        graph_name = custom_name or f"{template.name} Import"
        graph_create = GraphSpecCreate(
            name=graph_name,
            nodes=nodes,
            edges=edges,
            metadata={
                "template_id": template_id,
                "template_name": template.name,
                "category": template.category,
                "created_from_template": True
            }
        )

        graph = self.graph_service.create_graph(graph_create)

        return graph.id

    def _get_priority(self, template_id: str) -> int:
        """Get priority for a template (higher = more important)"""
        template = self.get_template(template_id)
        if template and template.metadata and template.metadata.priority:
            return template.metadata.priority
        return 0

    def get_categories(self) -> List[Dict[str, str]]:
        """
        Get all available template categories

        Returns:
            List of category dicts with name and description
        """
        categories = [
            {"id": "foundation", "name": "Foundation", "description": "Essential setup and configuration"},
            {"id": "sales", "name": "Sales & CRM", "description": "Customer relationship and sales management"},
            {"id": "projects", "name": "Projects", "description": "Project management and tasks"},
            {"id": "accounting", "name": "Accounting", "description": "Financial data and invoicing"},
            {"id": "complete", "name": "Complete Migration", "description": "Full business data migration"}
        ]
        return categories
