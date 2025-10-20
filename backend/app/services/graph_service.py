"""
Service for managing GraphSpec definitions and execution
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.graph import Graph, GraphRun
from app.schemas.graph import GraphSpec, GraphSpecCreate, GraphSpecUpdate, GraphValidation, ValidationError, ValidationWarning


class GraphService:
    def __init__(self, db: Session):
        self.db = db

    def create_graph(self, graph_create: GraphSpecCreate, created_by: Optional[str] = None) -> Graph:
        """Create a new graph definition"""
        graph_id = f"graph-{uuid.uuid4().hex[:12]}"

        spec_dict = {
            "id": graph_id,
            "name": graph_create.name,
            "version": 1,
            "nodes": [node.model_dump() for node in graph_create.nodes],
            "edges": [edge.model_dump() for edge in graph_create.edges],
            "metadata": graph_create.metadata or {}
        }

        graph = Graph(
            id=graph_id,
            name=graph_create.name,
            version=1,
            spec=spec_dict,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=created_by
        )

        self.db.add(graph)
        self.db.commit()
        self.db.refresh(graph)
        return graph

    def get_graph(self, graph_id: str) -> Optional[Graph]:
        """Get a graph by ID"""
        return self.db.query(Graph).filter(Graph.id == graph_id).first()

    def list_graphs(self, limit: int = 100, offset: int = 0) -> List[Graph]:
        """List all graphs"""
        return self.db.query(Graph).order_by(Graph.updated_at.desc()).offset(offset).limit(limit).all()

    def update_graph(self, graph_id: str, graph_update: GraphSpecUpdate) -> Optional[Graph]:
        """Update an existing graph"""
        graph = self.get_graph(graph_id)
        if not graph:
            return None

        # Increment version
        new_version = graph.version + 1

        # Update spec
        spec_dict = graph.spec.copy()

        if graph_update.name:
            graph.name = graph_update.name
            spec_dict["name"] = graph_update.name

        if graph_update.nodes is not None:
            spec_dict["nodes"] = [node.model_dump() for node in graph_update.nodes]

        if graph_update.edges is not None:
            spec_dict["edges"] = [edge.model_dump() for edge in graph_update.edges]

        if graph_update.metadata is not None:
            spec_dict["metadata"] = graph_update.metadata

        spec_dict["version"] = new_version
        graph.spec = spec_dict
        graph.version = new_version
        graph.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(graph)
        return graph

    def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph"""
        graph = self.get_graph(graph_id)
        if not graph:
            return False

        self.db.delete(graph)
        self.db.commit()
        return True

    def validate_graph(self, graph_spec: GraphSpec) -> GraphValidation:
        """
        Validate a graph spec for correctness
        Returns validation result with errors and warnings
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []

        # Check: all nodes have required fields
        for node in graph_spec.nodes:
            if node.kind == 'field':
                if not node.data.fieldName:
                    errors.append(ValidationError(
                        nodeId=node.id,
                        message=f"Field node '{node.label}' missing fieldName",
                        type='missing_field'
                    ))

            elif node.kind == 'model':
                if not node.data.odooModel:
                    errors.append(ValidationError(
                        nodeId=node.id,
                        message=f"Model node '{node.label}' missing odooModel",
                        type='missing_field'
                    ))

            elif node.kind == 'loader':
                if not node.data.odooModel:
                    errors.append(ValidationError(
                        nodeId=node.id,
                        message=f"Loader node '{node.label}' missing odooModel",
                        type='missing_field'
                    ))

            elif node.kind == 'transform':
                if not node.data.transformId:
                    errors.append(ValidationError(
                        nodeId=node.id,
                        message=f"Transform node '{node.label}' missing transformId",
                        type='missing_field'
                    ))

        # Check: all edges connect valid nodes
        node_ids = {node.id for node in graph_spec.nodes}
        for edge in graph_spec.edges:
            if edge.from_ not in node_ids:
                errors.append(ValidationError(
                    edgeId=edge.id,
                    message=f"Edge '{edge.id}' references non-existent source node '{edge.from_}'",
                    type='invalid_config'
                ))
            if edge.to not in node_ids:
                errors.append(ValidationError(
                    edgeId=edge.id,
                    message=f"Edge '{edge.id}' references non-existent target node '{edge.to}'",
                    type='invalid_config'
                ))

        # Check: no circular dependencies (simple cycle detection)
        if self._has_cycles(graph_spec):
            errors.append(ValidationError(
                message="Graph contains circular dependencies",
                type='circular_dependency'
            ))

        # Warnings: check for isolated nodes
        connected_nodes = set()
        for edge in graph_spec.edges:
            connected_nodes.add(edge.from_)
            connected_nodes.add(edge.to)

        for node in graph_spec.nodes:
            if node.id not in connected_nodes:
                warnings.append(ValidationWarning(
                    nodeId=node.id,
                    message=f"Node '{node.label}' is not connected to any other nodes",
                    type='performance'
                ))

        return GraphValidation(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _has_cycles(self, graph_spec: GraphSpec) -> bool:
        """Simple cycle detection using DFS"""
        # Build adjacency list
        adj = {node.id: [] for node in graph_spec.nodes}
        for edge in graph_spec.edges:
            adj[edge.from_].append(edge.to)

        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in adj.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node in graph_spec.nodes:
            if node.id not in visited:
                if dfs(node.id):
                    return True

        return False

    # GraphRun management
    def create_run(self, graph_id: str, dataset_id: Optional[int] = None) -> GraphRun:
        """Create a new run for a graph"""
        run_id = f"run-{uuid.uuid4().hex[:12]}"

        run = GraphRun(
            id=run_id,
            graph_id=graph_id,
            dataset_id=dataset_id,
            status="queued",
            started_at=datetime.utcnow(),
            progress=0,
            logs=[],
            context={}
        )

        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: str) -> Optional[GraphRun]:
        """Get a run by ID"""
        return self.db.query(GraphRun).filter(GraphRun.id == run_id).first()

    def list_runs(self, graph_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[GraphRun]:
        """List runs, optionally filtered by graph_id"""
        query = self.db.query(GraphRun)
        if graph_id:
            query = query.filter(GraphRun.graph_id == graph_id)
        return (
            query.order_by(GraphRun.started_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update_run_status(
        self,
        run_id: str,
        status: str,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
        current_node: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        finished_at: Optional[datetime] = None,
    ) -> Optional[GraphRun]:
        """Update run status"""
        from sqlalchemy.orm.attributes import flag_modified

        run = self.get_run(run_id)
        if not run:
            return None

        run.status = status
        if progress is not None:
            run.progress = progress
        if current_node is not None:
            run.current_node = current_node
        if context is not None:
            run.context = context
            # Mark JSON column as modified
            flag_modified(run, "context")
        if error_message is not None:
            run.error_message = error_message
        if finished_at is not None:
            if isinstance(finished_at, datetime):
                run.finished_at = finished_at
            elif isinstance(finished_at, str):
                try:
                    run.finished_at = datetime.fromisoformat(finished_at)
                except ValueError:
                    run.finished_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            run.finished_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(run)
        return run

    def append_log(self, run_id: str, message: str, level: str = "info") -> Optional[GraphRun]:
        """Append a log entry to the run"""
        from sqlalchemy.orm.attributes import flag_modified

        run = self.get_run(run_id)
        if not run:
            return None

        # Initialize logs if None
        if run.logs is None:
            run.logs = []

        # Append new log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message
        }
        run.logs.append(log_entry)

        # Mark the column as modified so SQLAlchemy persists the change
        flag_modified(run, "logs")

        self.db.commit()
        self.db.refresh(run)
        return run

    # Registry Integration Methods
    def create_from_registry(self, template_type: str, created_by: Optional[str] = None) -> Graph:
        """Generate graph directly from registry template"""
        from app.registry.loader import RegistryLoader

        registry_path = Path(__file__).parent.parent.parent / "registry" / "odoo.yaml"
        loader = RegistryLoader(registry_path)
        
        try:
            graph_spec = loader.create_migration_template(template_type)
            
            graph_id = f"registry-{template_type}-{uuid.uuid4().hex[:8]}"
            
            spec_dict = graph_spec.model_dump()
            
            graph = Graph(
                id=graph_id,
                name=graph_spec.name,
                version=1,
                spec=spec_dict,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=created_by
            )

            self.db.add(graph)
            self.db.commit()
            self.db.refresh(graph)
            return graph
            
        except Exception as e:
            raise ValueError(f"Failed to create graph from registry template {template_type}: {str(e)}")

    def validate_registry_compatibility(self, graph_id: str) -> GraphValidation:
        """Validate graph against current registry"""
        from app.registry.loader import RegistryLoader

        registry_path = Path(__file__).parent.parent.parent / "registry" / "odoo.yaml"
        loader = RegistryLoader(registry_path)
        registry = loader.load()
        
        graph = self.get_graph(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")
            
        graph_spec = GraphSpec(**graph.spec)
        
        errors = []
        warnings = []
        
        # Check if all models in graph exist in registry
        for node in graph_spec.nodes:
            if node.data and node.data.odooModel:
                if node.data.odooModel not in registry.models:
                    errors.append(ValidationError(
                        nodeId=node.id,
                        message=f"Model '{node.data.odooModel}' not found in current registry"
                    ))
        
        # Registry order is already validated during load, skip additional validation here
        
        return GraphValidation(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata={"registry_version": "v1", "models_count": len(registry.models)}
        )

    def list_registry_templates(self) -> List[Dict[str, Any]]:
        """List available registry-based templates"""
        from app.registry.loader import RegistryLoader

        registry_path = Path(__file__).parent.parent.parent / "registry" / "odoo.yaml"
        loader = RegistryLoader(registry_path)
        templates = loader.list_migration_templates()
        
        return [
            {
                "type": key,
                **template,
                "available": True
            }
            for key, template in templates.items()
        ]

    def get_registry_dependencies(self, model_name: str) -> Dict[str, Any]:
        """Get dependency information for a specific model from registry"""
        from app.registry.loader import RegistryLoader

        registry_path = Path(__file__).parent.parent.parent / "registry" / "odoo.yaml"
        loader = RegistryLoader(registry_path)
        
        try:
            dependencies = loader.get_dependencies(model_name)
            
            return {
                "model": model_name,
                "dependencies": dependencies,
                "dependency_count": len(dependencies),
                "available": True
            }
        except ValueError as e:
            return {
                "model": model_name,
                "dependencies": [],
                "dependency_count": 0,
                "error": str(e),
                "available": False
            }
