"""
Graph models for storing GraphSpec definitions
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Graph(Base):
    """
    Stores a complete GraphSpec as JSONB
    Represents a reusable ETL workflow definition
    """
    __tablename__ = "graphs"

    id = Column(String, primary_key=True, index=True)  # UUID or custom ID
    name = Column(String, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    spec = Column(JSON, nullable=False)  # Full GraphSpec as JSONB
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String, nullable=True)  # User ID if auth is implemented

    # Relationships
    runs = relationship("GraphRun", back_populates="graph", cascade="all, delete-orphan")


class GraphRun(Base):
    """
    Tracks execution of a graph
    """
    __tablename__ = "graph_runs"

    id = Column(String, primary_key=True, index=True)  # UUID
    graph_id = Column(String, ForeignKey("graphs.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)  # Optional link to dataset
    status = Column(String, default="queued", nullable=False)  # queued, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    current_node = Column(String, nullable=True)
    logs = Column(JSON, nullable=True)  # Array of log entries
    stats = Column(JSON, nullable=True)  # Execution statistics
    context = Column(JSON, nullable=True)  # Arbitrary run metadata
    error_message = Column(Text, nullable=True)

    # Relationships
    graph = relationship("Graph", back_populates="runs")
