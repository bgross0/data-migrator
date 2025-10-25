from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class MappingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IGNORED = "ignored"
    CREATE_FIELD = "create_field"


class MatchStrategy(str, enum.Enum):
    EMAIL = "email"
    XML_ID = "xml_id"
    EXTERNAL_CODE = "external_code"
    NAME = "name"
    NAME_FUZZY = "name_fuzzy"
    PHONE = "phone"


class Mapping(Base):
    __tablename__ = "mappings"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    sheet_id = Column(Integer, ForeignKey("sheets.id"), nullable=False)
    header_name = Column(String, nullable=False)
    target_model = Column(String, nullable=True)  # e.g., "res.partner"
    target_field = Column(String, nullable=True)  # e.g., "email"
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    match_method = Column(String, nullable=True)  # e.g., "exact_pattern", "fuzzy", "kb_label"
    status = Column(SQLEnum(MappingStatus), default=MappingStatus.PENDING, nullable=False)
    chosen = Column(Boolean, default=False, nullable=False)
    rationale = Column(String, nullable=True)  # Why this mapping was suggested
    custom_field_definition = Column(JSON, nullable=True)  # Custom field spec when status=CREATE_FIELD

    # Lambda transformation support
    mapping_type = Column(String, default="direct", nullable=False)  # direct, lambda, join
    lambda_function = Column(Text, nullable=True)  # Lambda function as string
    join_config = Column(JSON, nullable=True)  # Join configuration

    # Relationships
    dataset = relationship("Dataset", back_populates="mappings")
    sheet = relationship("Sheet", back_populates="mappings")
    transforms = relationship("Transform", back_populates="mapping", cascade="all, delete-orphan")
    suggestions = relationship("Suggestion", back_populates="mapping", cascade="all, delete-orphan")


class Transform(Base):
    __tablename__ = "transforms"

    id = Column(Integer, primary_key=True, index=True)
    mapping_id = Column(Integer, ForeignKey("mappings.id"), nullable=False)
    order = Column(Integer, nullable=False)  # Execution order
    fn = Column(String, nullable=False)  # Function name, e.g., "trim", "phone_normalize"
    params = Column(JSON, nullable=True)  # Parameters for the function

    # Relationships
    mapping = relationship("Mapping", back_populates="transforms")


class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, index=True)
    child_model = Column(String, nullable=False)  # e.g., "crm.lead"
    child_field = Column(String, nullable=False)  # e.g., "partner_id"
    parent_model = Column(String, nullable=False)  # e.g., "res.partner"
    match_on = Column(SQLEnum(MatchStrategy), nullable=False)
    fallback_order = Column(JSON, nullable=True)  # Array of MatchStrategy for fallback


class ImportGraph(Base):
    __tablename__ = "import_graphs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    nodes = Column(JSON, nullable=False)  # Array of model names in topological order
    edges = Column(JSON, nullable=False)  # Array of {from, to, via} relationships

    # Relationships
    runs = relationship("Run", back_populates="import_graph")
