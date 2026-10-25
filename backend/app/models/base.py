"""Base SQLAlchemy ORM model class."""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from backend.app.core.database import Base


class BaseModel(Base):
    """Abstract base model adding common timestamps."""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
