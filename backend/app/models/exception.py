"""
Exception model for tracking validation errors during export.

Exceptions are first-class: bad rows never block good rows.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class Exception(Base):
    """
    Exception record for a validation error.

    Tracks rows that fail validation during export pipeline.
    Each exception includes actionable information for correction.
    """

    __tablename__ = "exceptions"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    model = Column(String, nullable=False, index=True)  # e.g., "res.partner"
    row_ptr = Column(String, nullable=False)  # Stable pointer (source_ptr from ingest)
    error_code = Column(
        String, nullable=False, index=True
    )  # REQ_MISSING, ENUM_UNKNOWN, FK_UNRESOLVED, DUP_EXT_ID, etc.
    hint = Column(String, nullable=False)  # Human-readable actionable message
    offending = Column(JSON, nullable=True)  # Dict of problematic field values
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    dataset = relationship("Dataset", back_populates="exceptions")


# Update Dataset model to include exceptions relationship (add this to models/__init__.py or source.py)
