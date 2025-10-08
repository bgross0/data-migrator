from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class SourceFile(Base):
    __tablename__ = "source_files"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    uploader_id = Column(Integer, nullable=True)  # TODO: Add User model
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    datasets = relationship("Dataset", back_populates="source_file")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    source_file_id = Column(Integer, ForeignKey("source_files.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(Integer, nullable=True)  # TODO: Add User model

    # Relationships
    source_file = relationship("SourceFile", back_populates="datasets")
    sheets = relationship("Sheet", back_populates="dataset", cascade="all, delete-orphan")
    mappings = relationship("Mapping", back_populates="dataset")
    runs = relationship("Run", back_populates="dataset")


class Sheet(Base):
    __tablename__ = "sheets"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    name = Column(String, nullable=False)
    n_rows = Column(Integer, nullable=False)
    n_cols = Column(Integer, nullable=False)

    # Relationships
    dataset = relationship("Dataset", back_populates="sheets")
    column_profiles = relationship("ColumnProfile", back_populates="sheet", cascade="all, delete-orphan")
