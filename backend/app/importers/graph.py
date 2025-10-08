"""
Import graph - topological sorting for entity dependencies.
"""
from typing import List, Dict, Set
from collections import defaultdict, deque


class ImportGraph:
    """Manages import order based on entity dependencies."""

    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: Dict[str, List[str]] = defaultdict(list)

    def add_node(self, model: str):
        """Add a model to the graph."""
        self.nodes.add(model)

    def add_edge(self, parent: str, child: str):
        """
        Add a dependency edge (parent must be imported before child).

        Args:
            parent: Parent model (e.g., "res.partner")
            child: Child model (e.g., "crm.lead")
        """
        self.edges[parent].append(child)
        self.nodes.add(parent)
        self.nodes.add(child)

    def topological_sort(self) -> List[str]:
        """
        Return models in topological order (parents before children).

        Returns:
            List of model names in import order

        Raises:
            ValueError: If graph contains cycles
        """
        # Calculate in-degree for each node
        in_degree = {node: 0 for node in self.nodes}
        for parent in self.edges:
            for child in self.edges[parent]:
                in_degree[child] += 1

        # Queue of nodes with no dependencies
        queue = deque([node for node in self.nodes if in_degree[node] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            # Reduce in-degree for children
            for child in self.edges.get(node, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        # Check for cycles
        if len(result) != len(self.nodes):
            raise ValueError("Graph contains cycles")

        return result

    @classmethod
    def from_default(cls) -> "ImportGraph":
        """
        Create default import graph for contractor/Buildertrend data.

        Order:
        1. res.partner (customers/vendors)
        2. crm.lead
        3. product.template / product.product
        4. project.project
        5. project.task
        6. sale.order -> sale.order.line
        """
        graph = cls()

        # Define dependencies
        graph.add_edge("res.partner", "crm.lead")
        graph.add_edge("res.partner", "project.project")
        graph.add_edge("res.partner", "sale.order")
        graph.add_edge("project.project", "project.task")
        graph.add_edge("sale.order", "sale.order.line")
        graph.add_edge("product.product", "sale.order.line")

        return graph
