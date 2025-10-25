from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    PROFILING = "profiling"
    MAPPING = "mapping"
    VALIDATING = "validating"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class LogLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    graph_id = Column(Integer, ForeignKey("import_graphs.id"), nullable=True)
    status = Column(SQLEnum(RunStatus), default=RunStatus.PENDING, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    stats = Column(JSON, nullable=True)  # e.g., {"created": 100, "updated": 50, "errors": 2}

    # Relationships
    dataset = relationship("Dataset", back_populates="runs")
    import_graph = relationship("ImportGraph", back_populates="runs")
    logs = relationship("RunLog", back_populates="run", cascade="all, delete-orphan")
    keymaps = relationship("KeyMap", back_populates="run", cascade="all, delete-orphan")
    ledger_entries = relationship("ImportLedger", back_populates="run", cascade="all, delete-orphan")


class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    level = Column(SQLEnum(LogLevel), nullable=False)
    message = Column(String, nullable=False)
    row_ref = Column(JSON, nullable=True)  # Reference to specific row/data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    run = relationship("Run", back_populates="logs")


class KeyMap(Base):
    __tablename__ = "keymaps"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    model = Column(String, nullable=False)  # e.g., "res.partner"
    source_key = Column(String, nullable=False)  # e.g., "buildertrend_customer_123"
    xml_id = Column(String, nullable=True)  # e.g., "axsys.partner.123"
    odoo_id = Column(Integer, nullable=True)  # Odoo internal ID

    # Enhanced identity resolution fields
    natural_key_hash = Column(String, nullable=True)  # MD5 hash of natural key components
    content_hash = Column(String, nullable=True)  # MD5 hash of content for change detection
    match_confidence = Column(Float, nullable=True)  # Match confidence score (0.0-1.0)
    match_method = Column(String, nullable=True)  # How it was matched (exact, fuzzy, manual, etc.)

    # Relationships
    run = relationship("Run", back_populates="keymaps")


class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True, index=True)
    mapping_id = Column(Integer, ForeignKey("mappings.id"), nullable=False)
    candidates = Column(JSON, nullable=False)  # Ranked list of {model, field, confidence, method}

    # Relationships
    mapping = relationship("Mapping", back_populates="suggestions")
