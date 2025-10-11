"""
Performance Monitor for field mapper.

Tracks timing, memory usage, and performance metrics.
"""
import time
import psutil
from typing import Dict, Optional, List
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

from ..config.logging_config import performance_logger as logger


@dataclass
class PerformanceMetrics:
    """Performance metrics for an operation."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    memory_before_mb: Optional[float] = None
    memory_after_mb: Optional[float] = None
    memory_delta_mb: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


class PerformanceMonitor:
    """
    Monitors performance of field mapping operations.

    Tracks:
    - Execution time for operations
    - Memory usage
    - Performance metrics
    - Bottleneck identification
    """

    def __init__(self):
        """Initialize the performance monitor."""
        self.metrics: List[PerformanceMetrics] = []
        self.process = psutil.Process()
        logger.info("PerformanceMonitor initialized")

    @contextmanager
    def measure(self, operation: str, **metadata):
        """
        Context manager to measure operation performance.

        Args:
            operation: Name of the operation
            **metadata: Additional metadata to store

        Yields:
            PerformanceMetrics object

        Example:
            with monitor.measure("load_knowledge_base") as metrics:
                # do work
                pass
        """
        # Start measurement
        metric = PerformanceMetrics(
            operation=operation,
            start_time=time.time(),
            memory_before_mb=self._get_memory_mb(),
            metadata=metadata
        )

        logger.info(f"Starting: {operation}")

        try:
            yield metric
        finally:
            # End measurement
            metric.end_time = time.time()
            metric.duration_ms = (metric.end_time - metric.start_time) * 1000
            metric.memory_after_mb = self._get_memory_mb()
            metric.memory_delta_mb = metric.memory_after_mb - metric.memory_before_mb

            # Store metrics
            self.metrics.append(metric)

            logger.info(
                f"Completed: {operation} | "
                f"Duration: {metric.duration_ms:.2f}ms | "
                f"Memory: {metric.memory_delta_mb:+.2f}MB"
            )

    def _get_memory_mb(self) -> float:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in megabytes
        """
        try:
            mem_info = self.process.memory_info()
            return mem_info.rss / 1024 / 1024  # Convert bytes to MB
        except Exception as e:
            logger.warning(f"Could not get memory info: {e}")
            return 0.0

    def get_summary(self) -> Dict:
        """
        Get performance summary.

        Returns:
            Dictionary with performance statistics
        """
        if not self.metrics:
            return {"total_operations": 0}

        total_duration = sum(m.duration_ms for m in self.metrics if m.duration_ms)
        total_memory = sum(m.memory_delta_mb for m in self.metrics if m.memory_delta_mb)

        # Group by operation
        by_operation = {}
        for metric in self.metrics:
            if metric.operation not in by_operation:
                by_operation[metric.operation] = {
                    "count": 0,
                    "total_duration_ms": 0,
                    "avg_duration_ms": 0,
                    "total_memory_mb": 0,
                }

            by_operation[metric.operation]["count"] += 1
            by_operation[metric.operation]["total_duration_ms"] += metric.duration_ms or 0
            by_operation[metric.operation]["total_memory_mb"] += metric.memory_delta_mb or 0

        # Calculate averages
        for op_stats in by_operation.values():
            if op_stats["count"] > 0:
                op_stats["avg_duration_ms"] = op_stats["total_duration_ms"] / op_stats["count"]

        return {
            "total_operations": len(self.metrics),
            "total_duration_ms": total_duration,
            "total_memory_mb": total_memory,
            "by_operation": by_operation,
            "current_memory_mb": self._get_memory_mb(),
        }

    def get_slowest_operations(self, n: int = 5) -> List[PerformanceMetrics]:
        """
        Get the N slowest operations.

        Args:
            n: Number of operations to return

        Returns:
            List of PerformanceMetrics sorted by duration
        """
        sorted_metrics = sorted(
            [m for m in self.metrics if m.duration_ms],
            key=lambda m: m.duration_ms,
            reverse=True
        )
        return sorted_metrics[:n]

    def get_memory_intensive_operations(self, n: int = 5) -> List[PerformanceMetrics]:
        """
        Get the N most memory-intensive operations.

        Args:
            n: Number of operations to return

        Returns:
            List of PerformanceMetrics sorted by memory usage
        """
        sorted_metrics = sorted(
            [m for m in self.metrics if m.memory_delta_mb],
            key=lambda m: abs(m.memory_delta_mb),
            reverse=True
        )
        return sorted_metrics[:n]

    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
        logger.info("Performance metrics cleared")

    def export_metrics(self) -> List[Dict]:
        """
        Export metrics as list of dictionaries.

        Returns:
            List of metric dictionaries
        """
        return [
            {
                "operation": m.operation,
                "duration_ms": m.duration_ms,
                "memory_delta_mb": m.memory_delta_mb,
                "timestamp": m.start_time,
                "metadata": m.metadata,
            }
            for m in self.metrics
        ]


# Global monitor instance
_monitor_instance: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor()
    return _monitor_instance
