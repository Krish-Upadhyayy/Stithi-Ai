"""Pydantic schemas for InventoryItem and Excel Upload/Confirmation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class InventoryItemBase(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=100, description="Asset name (e.g. Computer, Chair)")
    category: Optional[str] = Field(None, max_length=100, description="Category (e.g. Equipment, Furniture)")
    expected_quantity: int = Field(..., ge=0, description="Sanctioned expected quantity from Excel baseline")


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(BaseModel):
    item_name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    expected_quantity: Optional[int] = Field(None, ge=0)


class InventoryItemResponse(InventoryItemBase):
    id: int
    centre_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryRowError(BaseModel):
    row: int = Field(..., description="Excel row number (1-indexed)")
    field: Optional[str] = Field(None, description="Column or field name")
    message: str = Field(..., description="Validation failure explanation")


class InventoryParsedItem(BaseModel):
    row: int = Field(..., description="Source row in Excel")
    item_name: str
    category: Optional[str] = None
    expected_quantity: int


class InventoryUploadPreviewResponse(BaseModel):
    is_valid: bool = Field(..., description="True if whole sheet passed validation with 0 errors")
    filename: str
    total_rows: int
    valid_rows_count: int
    error_count: int
    items: List[InventoryParsedItem] = Field(default_factory=list)
    errors: List[InventoryRowError] = Field(default_factory=list)


class InventoryConfirmItem(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    expected_quantity: int = Field(..., ge=0)


class InventoryConfirmRequest(BaseModel):
    items: List[InventoryConfirmItem] = Field(..., min_length=1, description="List of validated items to persist")
    replace_existing: bool = Field(default=True, description="Replace existing sanctioned inventory for this centre")


class InventoryConfirmResponse(BaseModel):
    message: str
    imported_count: int
    replaced_count: int
    centre_id: int
