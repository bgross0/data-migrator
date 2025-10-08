from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.core.database import Base


class OdooConnection(Base):
    __tablename__ = "odoo_connections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Friendly name like "Production" or "Staging"
    url = Column(String, nullable=False)  # Odoo instance URL
    database = Column(String, nullable=False)  # Database name
    username = Column(String, nullable=False)  # Odoo username
    password = Column(String, nullable=False)  # Encrypted password (TODO: implement encryption)
    is_default = Column(Boolean, default=False, nullable=False)  # Default connection
    is_active = Column(Boolean, default=True, nullable=False)  # Active/inactive
    last_tested_at = Column(DateTime, nullable=True)  # Last successful connection test
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
