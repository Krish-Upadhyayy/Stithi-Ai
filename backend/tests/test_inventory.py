"""Inventory Management and Excel Upload Test Suite.
Covers all 15 required scenarios including validation edge-cases, preview isolation,
confirmation atomicity, and authorization guards.
"""

import io
import pytest
import openpyxl
from backend.app.models.user import User
from backend.app.models.centre import Centre
from backend.app.models.inventory import InventoryItem
from backend.app.core.security import get_password_hash, create_access_token


def create_in_memory_excel(headers, rows):
    """Generates an in-memory .xlsx file bytes."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def inventory_test_setup(db_session):
    """Sets up test admin, regular centre user, and a test centre."""
    admin = User(
        name="Inventory Admin",
        email="inv_admin@sih.gov.in",
        password_hash=get_password_hash("AdminPass123!"),
        role="ADMIN",
    )
    user = User(
        name="Centre Operator",
        email="inv_user@sih.gov.in",
        password_hash=get_password_hash("UserPass123!"),
        role="CENTRE_USER",
    )
    centre = Centre(
        centre_code="TC-INV-001",
        name="National Vocational Centre",
        location="Sector 1, Bhopal",
        status="ACTIVE",
    )
    db_session.add_all([admin, user, centre])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(user)
    db_session.refresh(centre)

    admin_token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": "ADMIN"})
    user_token = create_access_token({"sub": str(user.id), "email": user.email, "role": "CENTRE_USER"})

    return {
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "user_headers": {"Authorization": f"Bearer {user_token}"},
        "admin": admin,
        "user": user,
        "centre": centre,
    }


# 1. Valid Excel upload
def test_valid_excel_upload(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    file_bytes = create_in_memory_excel(
        ["Item Name", "Category", "Expected Quantity"],
        [
            ["Computer", "Equipment", 20],
            ["Chair", "Furniture", 25],
            ["Projector", "Equipment", 2],
        ],
    )

    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/upload",
        headers=inventory_test_setup["admin_headers"],
        files={"file": ("sanctioned_inventory.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["valid_rows_count"] == 3
    assert data["error_count"] == 0
    assert len(data["items"]) == 3
    assert data["items"][0]["item_name"] == "Computer"
    assert data["items"][0]["expected_quantity"] == 20


# 2. Missing required column
def test_missing_required_column(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    # Missing 'Expected Quantity'
    file_bytes = create_in_memory_excel(
        ["Item Name", "Category"],
        [["Computer", "Equipment"]],
    )

    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/upload",
        headers=inventory_test_setup["admin_headers"],
        files={"file": ("missing_col.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert data["error_count"] > 0
    assert any("Expected Quantity" in err["message"] for err in data["errors"])


# 3. Empty Excel
def test_empty_excel(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    # 0 bytes file
    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/upload",
        headers=inventory_test_setup["admin_headers"],
        files={"file": ("empty.xlsx", b"", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert any("empty" in err["message"].lower() for err in data["errors"])


# 4. Invalid quantity (string)
def test_invalid_quantity(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    file_bytes = create_in_memory_excel(
        ["Item Name", "Expected Quantity"],
        [["Computer", "twenty"]],
    )

    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/upload",
        headers=inventory_test_setup["admin_headers"],
        files={"file": ("invalid_qty.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert any("Expected Quantity must be numeric" in err["message"] for err in data["errors"])


# 5. Negative quantity
def test_negative_quantity(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    file_bytes = create_in_memory_excel(
        ["Item Name", "Expected Quantity"],
        [["Projector", -3]],
    )

    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/upload",
        headers=inventory_test_setup["admin_headers"],
        files={"file": ("negative_qty.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert any("non-negative integer" in err["message"] for err in data["errors"])


# 6. Missing item name
def test_missing_item_name(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    file_bytes = create_in_memory_excel(
        ["Item Name", "Expected Quantity"],
        [["", 10], [None, 5]],
    )

    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/upload",
        headers=inventory_test_setup["admin_headers"],
        files={"file": ("missing_name.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert any("Item Name is missing or empty" in err["message"] for err in data["errors"])


# 7. Duplicate item
def test_duplicate_item(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    file_bytes = create_in_memory_excel(
        ["Item Name", "Expected Quantity"],
        [
            ["Computer", 10],
            ["computer", 5],  # duplicate case-insensitive
        ],
    )

    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/upload",
        headers=inventory_test_setup["admin_headers"],
        files={"file": ("duplicate_items.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert any("Duplicate item 'computer' detected" in err["message"] for err in data["errors"])


# 8. Preview does not modify database
def test_preview_does_not_modify_database(client, inventory_test_setup, db_session):
    centre = inventory_test_setup["centre"]
    file_bytes = create_in_memory_excel(
        ["Item Name", "Expected Quantity"],
        [["Test Asset", 15]],
    )

    client.post(
        f"/api/v1/centres/{centre.id}/inventory/upload",
        headers=inventory_test_setup["admin_headers"],
        files={"file": ("preview_test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    # Verify no records were added to database
    count = db_session.query(InventoryItem).filter(InventoryItem.centre_id == centre.id).count()
    assert count == 0


# 9. Confirmation saves data
def test_confirmation_saves_data(client, inventory_test_setup, db_session):
    centre = inventory_test_setup["centre"]
    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/confirm",
        headers=inventory_test_setup["admin_headers"],
        json={
            "items": [
                {"item_name": "Desktop PC", "category": "IT", "expected_quantity": 25},
                {"item_name": "Whiteboard", "category": "Classroom", "expected_quantity": 4},
            ],
            "replace_existing": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["imported_count"] == 2

    # Verify persisted in database
    items = db_session.query(InventoryItem).filter(InventoryItem.centre_id == centre.id).all()
    assert len(items) == 2
    item_names = {i.item_name for i in items}
    assert "Desktop PC" in item_names
    assert "Whiteboard" in item_names


# 10. Failed confirmation does not partially save data (transaction rollback)
def test_failed_confirmation_no_partial_save(client, inventory_test_setup, db_session):
    centre = inventory_test_setup["centre"]
    # Payload with duplicate items triggers a rejection
    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/confirm",
        headers=inventory_test_setup["admin_headers"],
        json={
            "items": [
                {"item_name": "Item A", "expected_quantity": 10},
                {"item_name": "Item A", "expected_quantity": 20},  # duplicate
            ],
            "replace_existing": True,
        },
    )
    assert res.status_code == 400
    # Confirm 0 records were saved
    count = db_session.query(InventoryItem).filter(InventoryItem.centre_id == centre.id).count()
    assert count == 0


# 11. Get inventory
def test_get_inventory(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    client.post(
        f"/api/v1/centres/{centre.id}/inventory/confirm",
        headers=inventory_test_setup["admin_headers"],
        json={
            "items": [
                {"item_name": "Microscope", "expected_quantity": 5},
                {"item_name": "Lab Stool", "expected_quantity": 15},
            ],
            "replace_existing": True,
        },
    )

    get_res = client.get(
        f"/api/v1/centres/{centre.id}/inventory",
        headers=inventory_test_setup["admin_headers"],
    )
    assert get_res.status_code == 200
    items = get_res.json()
    assert len(items) == 2


# 12. Update item
def test_update_item(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    client.post(
        f"/api/v1/centres/{centre.id}/inventory/confirm",
        headers=inventory_test_setup["admin_headers"],
        json={"items": [{"item_name": "Laptop", "expected_quantity": 10}], "replace_existing": True},
    )
    items = client.get(f"/api/v1/centres/{centre.id}/inventory", headers=inventory_test_setup["admin_headers"]).json()
    item_id = items[0]["id"]

    upd_res = client.put(
        f"/api/v1/centres/{centre.id}/inventory/{item_id}",
        headers=inventory_test_setup["admin_headers"],
        json={"item_name": "Lenovo Laptop", "expected_quantity": 12},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["item_name"] == "Lenovo Laptop"
    assert upd_res.json()["expected_quantity"] == 12


# 13. Delete item
def test_delete_item(client, inventory_test_setup, db_session):
    centre = inventory_test_setup["centre"]
    client.post(
        f"/api/v1/centres/{centre.id}/inventory/confirm",
        headers=inventory_test_setup["admin_headers"],
        json={"items": [{"item_name": "Printer", "expected_quantity": 2}], "replace_existing": True},
    )
    items = client.get(f"/api/v1/centres/{centre.id}/inventory", headers=inventory_test_setup["admin_headers"]).json()
    item_id = items[0]["id"]

    del_res = client.delete(
        f"/api/v1/centres/{centre.id}/inventory/{item_id}",
        headers=inventory_test_setup["admin_headers"],
    )
    assert del_res.status_code == 200
    assert del_res.json()["id"] == item_id

    # Verify deleted
    remaining = db_session.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    assert remaining is None


# 14. Unauthorized upload
def test_unauthorized_upload(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    file_bytes = create_in_memory_excel(
        ["Item Name", "Expected Quantity"],
        [["Monitor", 10]],
    )

    # Centre operator (non-admin)
    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/upload",
        headers=inventory_test_setup["user_headers"],
        files={"file": ("test.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 403


# 15. Unauthorized confirmation
def test_unauthorized_confirmation(client, inventory_test_setup):
    centre = inventory_test_setup["centre"]
    res = client.post(
        f"/api/v1/centres/{centre.id}/inventory/confirm",
        headers=inventory_test_setup["user_headers"],
        json={"items": [{"item_name": "Server Rack", "expected_quantity": 1}]},
    )
    assert res.status_code == 403
