from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class ColumnProfile(Base):
    __tablename__ = "column_profiles"

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(Integer, ForeignKey("sheets.id"), nullable=False)
    name = Column(String, nullable=False)  # Original header name
    dtype_guess = Column(String, nullable=False)  # e.g., "string", "integer", "float", "date", "boolean"
    null_pct = Column(Float, nullable=False)
    distinct_pct = Column(Float, nullable=False)
    patterns = Column(JSON, nullable=True)  # e.g., {"email": 0.95, "phone": 0.02}
    sample_values = Column(JSON, nullable=True)  # Array of sample values

    # Relationships
    sheet = relationship("Sheet", back_populates="column_profiles")
