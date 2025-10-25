"""
Import graph - topological sorting for entity dependencies.

Enhanced with:
- 7-batch topology support (System Config → Taxonomies → Partners → Leads → Polymorphic → Sales → Projects)
- Batch-level execution with validation hooks
- Exponential backoff retry logic
"""
from typing import List, Dict, Set, Tuple, Callable, Any, Optional
from collections import defaultdict, deque
import time
import logging

logger = logging.getLogger(__name__)


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

    @classmethod
    def from_seven_batch_topology(cls) -> Tuple["ImportGraph", List[List[str]]]:
        """
        Create import graph with 7-batch topology.

        Batch Order:
        1. System Config (companies, users, currencies, countries)
        2. Taxonomies (product categories, lead stages, tags, industries)
        3. Partners (companies THEN contacts)
        4. Leads (opportunities/leads)
        5. Polymorphic (mail.activity, mail.message, ir.attachment with res_model/res_id)
        6. Sales (products, price lists, sale orders, sale order lines)
        7. Projects (projects, tasks, timesheets)

        Returns:
            Tuple of (ImportGraph, List of batches)
            Each batch is a list of model names that can be imported in parallel within that batch.
        """
        graph = cls()

        # Batch 1: System Config
        batch_1 = [
            "res.company",
            "res.users",
            "res.currency",
            "res.country",
            "res.country.state",
        ]

        # Batch 2: Taxonomies
        batch_2 = [
            "product.category",
            "crm.stage",
            "crm.tag",
            "res.partner.industry",
            "res.partner.category",
            "project.tags",
        ]

        # Batch 3: Partners (companies first, then contacts)
        # Note: Within batch 3, companies must be imported before contacts
        batch_3_companies = ["res.partner"]  # is_company=True
        batch_3_contacts = ["res.partner"]   # is_company=False, parent_id set

        # Batch 4: Leads
        batch_4 = [
            "crm.lead",
        ]

        # Batch 5: Polymorphic (depends on all previous entities)
        batch_5 = [
            "mail.activity",
            "mail.message",
            "ir.attachment",
        ]

        # Batch 6: Sales
        batch_6 = [
            "product.template",
            "product.product",
            "product.pricelist",
            "sale.order",
            "sale.order.line",
        ]

        # Batch 7: Projects
        batch_7 = [
            "project.project",
            "project.task",
            "account.analytic.line",  # timesheets
        ]

        # Define dependencies between batches
        # Batch 1 → Batch 2 (taxonomies need companies)
        for b1_model in batch_1:
            for b2_model in batch_2:
                graph.add_edge(b1_model, b2_model)

        # Batch 2 → Batch 3 (partners need taxonomies)
        for b2_model in batch_2:
            graph.add_edge(b2_model, "res.partner")

        # Batch 3 → Batch 4 (leads need partners)
        graph.add_edge("res.partner", "crm.lead")

        # Batch 4 → Batch 5 (polymorphic depends on leads)
        for b5_model in batch_5:
            graph.add_edge("crm.lead", b5_model)

        # Batch 3 → Batch 6 (sales need partners)
        graph.add_edge("res.partner", "product.template")
        graph.add_edge("product.template", "product.product")
        graph.add_edge("res.partner", "sale.order")
        graph.add_edge("sale.order", "sale.order.line")
        graph.add_edge("product.product", "sale.order.line")

        # Batch 3 → Batch 7 (projects need partners)
        graph.add_edge("res.partner", "project.project")
        graph.add_edge("project.project", "project.task")
        graph.add_edge("project.task", "account.analytic.line")

        # Return graph and batch structure
        batches = [
            batch_1,
            batch_2,
            batch_3_companies,  # Companies
            batch_3_contacts,   # Contacts (note: same model, different filters)
            batch_4,
            batch_5,
            batch_6,
            batch_7,
        ]

        return graph, batches

    def execute_batches_with_retry(
        self,
        batches: List[List[str]],
        batch_executor: Callable[[int, List[str]], Dict[str, Any]],
        pre_batch_hook: Optional[Callable[[int, List[str]], bool]] = None,
        post_batch_hook: Optional[Callable[[int, List[str], str], bool]] = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> Dict[str, Any]:
        """
        Execute batches sequentially with exponential backoff retry.

        Args:
            batches: List of batches (each batch is a list of model names)
            batch_executor: Function that executes a batch, returns stats dict
                           Signature: (batch_num: int, models: List[str]) -> Dict[str, Any]
            pre_batch_hook: Optional validation hook before batch execution
                           Signature: (batch_num: int, models: List[str]) -> bool
                           Returns: True if validation passed, False if failed
            post_batch_hook: Optional validation hook after batch execution
                            Signature: (batch_num: int, models: List[str], batch_id: str) -> bool
                            Returns: True if validation passed, False if failed
            max_retries: Maximum retry attempts per batch (default: 3)
            base_delay: Initial retry delay in seconds (default: 1.0)
            max_delay: Maximum retry delay in seconds (default: 60.0)

        Returns:
            Dict with overall stats:
            {
                "total_batches": int,
                "successful_batches": int,
                "failed_batches": int,
                "batch_stats": List[Dict],  # Per-batch stats
                "total_created": int,
                "total_updated": int,
                "total_errors": int,
            }
        """
        overall_stats = {
            "total_batches": len(batches),
            "successful_batches": 0,
            "failed_batches": 0,
            "batch_stats": [],
            "total_created": 0,
            "total_updated": 0,
            "total_errors": 0,
        }

        for batch_num, models in enumerate(batches, start=1):
            logger.info(f"Starting batch {batch_num}/{len(batches)}: {models}")

            # Pre-batch validation hook
            if pre_batch_hook:
                logger.info(f"Running pre-batch validation for batch {batch_num}")
                try:
                    validation_passed = pre_batch_hook(batch_num, models)
                    if not validation_passed:
                        logger.error(f"Pre-batch validation failed for batch {batch_num}")
                        overall_stats["failed_batches"] += 1
                        overall_stats["batch_stats"].append({
                            "batch_num": batch_num,
                            "models": models,
                            "status": "failed",
                            "reason": "pre_validation_failed",
                        })
                        continue  # Skip this batch
                except Exception as e:
                    logger.error(f"Pre-batch validation error for batch {batch_num}: {e}")
                    overall_stats["failed_batches"] += 1
                    overall_stats["batch_stats"].append({
                        "batch_num": batch_num,
                        "models": models,
                        "status": "failed",
                        "reason": f"pre_validation_error: {str(e)}",
                    })
                    continue

            # Execute batch with retry
            batch_stats = None
            last_error = None
            for attempt in range(max_retries):
                try:
                    logger.info(f"Executing batch {batch_num}, attempt {attempt + 1}/{max_retries}")
                    batch_stats = batch_executor(batch_num, models)

                    # Batch succeeded
                    logger.info(f"Batch {batch_num} completed successfully")
                    break

                except Exception as e:
                    last_error = e
                    logger.warning(f"Batch {batch_num} attempt {attempt + 1} failed: {e}")

                    if attempt < max_retries - 1:
                        # Calculate exponential backoff delay
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.info(f"Retrying batch {batch_num} in {delay:.1f} seconds...")
                        time.sleep(delay)
                    else:
                        logger.error(f"Batch {batch_num} failed after {max_retries} attempts")

            # Check if batch succeeded
            if batch_stats is None:
                overall_stats["failed_batches"] += 1
                overall_stats["batch_stats"].append({
                    "batch_num": batch_num,
                    "models": models,
                    "status": "failed",
                    "reason": f"max_retries_exceeded: {str(last_error)}",
                })
                continue

            # Post-batch validation hook
            if post_batch_hook:
                logger.info(f"Running post-batch validation for batch {batch_num}")
                try:
                    batch_id = batch_stats.get("batch_id", f"batch_{batch_num}")
                    validation_passed = post_batch_hook(batch_num, models, batch_id)
                    if not validation_passed:
                        logger.error(f"Post-batch validation failed for batch {batch_num}")
                        overall_stats["failed_batches"] += 1
                        overall_stats["batch_stats"].append({
                            "batch_num": batch_num,
                            "models": models,
                            "status": "failed",
                            "reason": "post_validation_failed",
                            "stats": batch_stats,
                        })
                        continue
                except Exception as e:
                    logger.error(f"Post-batch validation error for batch {batch_num}: {e}")
                    overall_stats["failed_batches"] += 1
                    overall_stats["batch_stats"].append({
                        "batch_num": batch_num,
                        "models": models,
                        "status": "failed",
                        "reason": f"post_validation_error: {str(e)}",
                        "stats": batch_stats,
                    })
                    continue

            # Batch succeeded with validation
            overall_stats["successful_batches"] += 1
            overall_stats["total_created"] += batch_stats.get("created", 0)
            overall_stats["total_updated"] += batch_stats.get("updated", 0)
            overall_stats["total_errors"] += batch_stats.get("errors", 0)
            overall_stats["batch_stats"].append({
                "batch_num": batch_num,
                "models": models,
                "status": "success",
                "stats": batch_stats,
            })

            logger.info(f"Batch {batch_num} completed: {batch_stats}")

        logger.info(f"All batches completed: {overall_stats['successful_batches']}/{overall_stats['total_batches']} successful")
        return overall_stats
