"""Inventory management and sanctioned infrastructure Excel import routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import require_authenticated_user, require_role
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.inventory import InventoryItem
from backend.app.schemas.inventory import (
    InventoryItemBase,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    InventoryUploadPreviewResponse,
    InventoryConfirmRequest,
    InventoryConfirmResponse,
)
from backend.app.services.excel_parser import parse_and_validate_inventory_excel

router = APIRouter(tags=["Inventory Baseline"])


# ==============================================================
# CENTRE-SCOPED INVENTORY ENDPOINTS
# /api/v1/centres/{centre_id}/inventory
# ==============================================================

@router.post(
    "/centres/{centre_id}/inventory/upload",
    response_model=InventoryUploadPreviewResponse,
    summary="Upload and validate Excel inventory without modifying database (Admin only)",
)
async def upload_inventory_excel(
    centre_id: int,
    file: UploadFile = File(..., description="Sanctioned equipment spreadsheet (.xlsx)"),
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Step 1: Uploads an .xlsx spreadsheet, validates schema and non-negative integers,
    and returns a structured preview. Zero database modifications are performed.
    """
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    # Secure filename and content type checks
    filename = file.filename or "upload.xlsx"
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file extension. Only .xlsx files are supported.",
        )

    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {str(exc)}",
        )

    preview = parse_and_validate_inventory_excel(content, filename)
    return preview


@router.post(
    "/centres/{centre_id}/inventory/confirm",
    response_model=InventoryConfirmResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm validated inventory import into MySQL (Admin only)",
)
def confirm_inventory_import(
    centre_id: int,
    confirm_in: InventoryConfirmRequest,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Step 2: Persists validated inventory rows into MySQL. Supports atomic replacement
    to avoid stale duplicate baselines. Rolls back completely on any database error.
    """
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    if not confirm_in.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation payload contains no inventory items to import.",
        )

    # Check for duplicate item names in confirmation payload
    seen_names = set()
    for it in confirm_in.items:
        low_name = it.item_name.strip().lower()
        if low_name in seen_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payload contains duplicate item name '{it.item_name}'.",
            )
        seen_names.add(low_name)

    try:
        existing_count = (
            db.query(InventoryItem)
            .filter(InventoryItem.centre_id == centre_id)
            .count()
        )

        if confirm_in.replace_existing:
            db.query(InventoryItem).filter(InventoryItem.centre_id == centre_id).delete(
                synchronize_session=False
            )

        new_items = [
            InventoryItem(
                centre_id=centre_id,
                item_name=item.item_name.strip(),
                category=item.category.strip() if item.category else None,
                expected_quantity=item.expected_quantity,
            )
            for item in confirm_in.items
        ]
        db.add_all(new_items)
        db.commit()

        return InventoryConfirmResponse(
            message=f"Successfully imported {len(new_items)} inventory items for centre '{centre.name}'.",
            imported_count=len(new_items),
            replaced_count=existing_count if confirm_in.replace_existing else 0,
            centre_id=centre_id,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction failed during import: {str(exc)}",
        )


@router.get(
    "/centres/{centre_id}/inventory",
    response_model=List[InventoryItemResponse],
    summary="Get sanctioned inventory items for a centre",
)
def get_centre_inventory(
    centre_id: int,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    """Retrieves all sanctioned expected equipment baseline items for a training centre."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    if current_user.role == "CENTRE_USER" and current_user.centre_id is not None:
        if current_user.centre_id != centre_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot view inventory for another centre.",
            )

    items = (
        db.query(InventoryItem)
        .filter(InventoryItem.centre_id == centre_id)
        .order_by(InventoryItem.id.asc())
        .all()
    )
    return items


@router.post(
    "/centres/{centre_id}/inventory",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually add an inventory item (Admin only)",
)
def create_manual_inventory_item(
    centre_id: int,
    item_in: InventoryItemBase,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Allows an administrator to manually record or amend a sanctioned equipment item."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    existing = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.centre_id == centre_id,
            func.lower(InventoryItem.item_name) == item_in.item_name.strip().lower(),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inventory item '{item_in.item_name}' already exists in this centre. Update it instead.",
        )

    item = InventoryItem(
        centre_id=centre_id,
        item_name=item_in.item_name.strip(),
        category=item_in.category.strip() if item_in.category else None,
        expected_quantity=item_in.expected_quantity,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put(
    "/centres/{centre_id}/inventory/{item_id}",
    response_model=InventoryItemResponse,
    summary="Update an inventory item (Admin only)",
)
def update_inventory_item(
    centre_id: int,
    item_id: int,
    item_in: InventoryItemUpdate,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Updates the details or expected quantity of an existing sanctioned asset."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    item = (
        db.query(InventoryItem)
        .filter(InventoryItem.id == item_id, InventoryItem.centre_id == centre_id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with id {item_id} not found in centre {centre_id}.",
        )

    if item_in.item_name is not None:
        new_name = item_in.item_name.strip()
        if new_name.lower() != item.item_name.lower():
            dup = (
                db.query(InventoryItem)
                .filter(
                    InventoryItem.centre_id == centre_id,
                    InventoryItem.id != item_id,
                    func.lower(InventoryItem.item_name) == new_name.lower(),
                )
                .first()
            )
            if dup:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"An item named '{new_name}' already exists in this centre.",
                )
        item.item_name = new_name

    if item_in.category is not None:
        item.category = item_in.category.strip() if item_in.category else None

    if item_in.expected_quantity is not None:
        item.expected_quantity = item_in.expected_quantity

    db.commit()
    db.refresh(item)
    return item


@router.delete(
    "/centres/{centre_id}/inventory/{item_id}",
    summary="Delete an inventory item (Admin only)",
)
def delete_inventory_item(
    centre_id: int,
    item_id: int,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """Removes a sanctioned asset from the centre baseline."""
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centre with id {centre_id} not found.",
        )

    item = (
        db.query(InventoryItem)
        .filter(InventoryItem.id == item_id, InventoryItem.centre_id == centre_id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with id {item_id} not found in centre {centre_id}.",
        )

    db.delete(item)
    db.commit()
    return {
        "message": f"Inventory item '{item.item_name}' (ID: {item_id}) removed successfully.",
        "id": item_id,
        "centre_id": centre_id,
    }


# ==============================================================
# GLOBAL COMPATIBILITY ENDPOINT
# /api/v1/inventory
# ==============================================================

@router.get(
    "/inventory",
    response_model=List[InventoryItemResponse],
    summary="List all inventory items across centres (Filtered by centre_id optional)",
)
def list_global_inventory(
    centre_id: Optional[int] = None,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    """Global lookup endpoint maintaining backward compatibility."""
    query = db.query(InventoryItem)
    if centre_id:
        query = query.filter(InventoryItem.centre_id == centre_id)
    elif current_user.role == "CENTRE_USER" and current_user.centre_id is not None:
        query = query.filter(InventoryItem.centre_id == current_user.centre_id)

    return query.order_by(InventoryItem.id.asc()).all()
