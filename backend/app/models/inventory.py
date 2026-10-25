"""Inventory Item database model for sanctioned infrastructure."""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.base import BaseModel


class InventoryItem(BaseModel):
    __tablename__ = "inventory_items"

    centre_id = Column(Integer, ForeignKey("centres.id", ondelete="CASCADE"), nullable=False)
    item_name = Column(String(100), nullable=False)  # Computer, Chair, Machine, Workbench
    category = Column(String(100), nullable=True)    # Classroom, Workshop, IT
    expected_quantity = Column(Integer, nullable=False, default=0)

    # Relationships
    centre = relationship("Centre", back_populates="inventory_items")
    infrastructure_observations = relationship("InfrastructureObservation", back_populates="inventory_item")
