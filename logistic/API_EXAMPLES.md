# API Examples

## Authentication

### Get JWT Token
```bash
POST /api/auth/token/
Content-Type: application/json

{
    "username": "admin",
    "password": "password123"
}
```

### Refresh Token
```bash
POST /api/auth/token/refresh/
Content-Type: application/json

{
    "refresh": "your_refresh_token_here"
}
```

---

## 1. Creating a Storage Location

### Create Zone
```bash
POST /api/warehouse/locations/
Authorization: Bearer <token>
Content-Type: application/json

{
    "code": "ZONE-A",
    "name": "Zone A - Main Warehouse",
    "level": "zone",
    "parent": null,
    "storage_type": "pallet",
    "capacity": 1000,
    "capacity_unit": "piece",
    "allowed_categories": [],
    "is_active": true,
    "notes": "Main storage zone for palletized goods"
}
```

### Create Aisle
```bash
POST /api/warehouse/locations/
Authorization: Bearer <token>
Content-Type: application/json

{
    "code": "ZONE-A-AISLE-01",
    "name": "Aisle 01",
    "level": "aisle",
    "parent": 1,
    "storage_type": "pallet",
    "capacity": 200,
    "capacity_unit": "piece",
    "allowed_categories": [1, 2],
    "is_active": true,
    "notes": ""
}
```

### Create Rack
```bash
POST /api/warehouse/locations/
Authorization: Bearer <token>
Content-Type: application/json

{
    "code": "ZONE-A-AISLE-01-RACK-01",
    "name": "Rack 01",
    "level": "rack",
    "parent": 2,
    "storage_type": "pallet",
    "capacity": 50,
    "capacity_unit": "piece",
    "allowed_categories": [1],
    "is_active": true,
    "notes": ""
}
```

### Create Level
```bash
POST /api/warehouse/locations/
Authorization: Bearer <token>
Content-Type: application/json

{
    "code": "ZONE-A-AISLE-01-RACK-01-LEVEL-01",
    "name": "Level 01",
    "level": "level",
    "parent": 3,
    "storage_type": "pallet",
    "capacity": 10,
    "capacity_unit": "piece",
    "allowed_categories": [1],
    "is_active": true,
    "notes": ""
}
```

### Create Bin
```bash
POST /api/warehouse/locations/
Authorization: Bearer <token>
Content-Type: application/json

{
    "code": "ZONE-A-AISLE-01-RACK-01-LEVEL-01-BIN-01",
    "name": "Bin 01",
    "level": "bin",
    "parent": 4,
    "storage_type": "box",
    "capacity": 100,
    "capacity_unit": "piece",
    "allowed_categories": [1],
    "is_active": true,
    "notes": "Small items storage"
}
```

---

## 2. Creating a Putaway Rule

```bash
POST /api/warehouse/putaway-rules/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "Electronics - Pallet Storage",
    "description": "Store electronics in pallet locations",
    "product_category": 1,
    "storage_type": "pallet",
    "priority": 1,
    "is_active": true
}
```

### Priority Levels:
- 1 = Highest
- 2 = High
- 3 = Medium
- 4 = Low
- 5 = Lowest

---

## 3. Getting Best Location Suggestion

```bash
POST /api/warehouse/putaway-rules/get_best_location/
Authorization: Bearer <token>
Content-Type: application/json

{
    "product_id": 1,
    "quantity": 50
}
```

**Response:**
```json
{
    "id": 5,
    "code": "ZONE-A-AISLE-01-RACK-01-LEVEL-01-BIN-01",
    "name": "Bin 01",
    "level": "bin",
    "parent": 4,
    "storage_type": "box",
    "capacity": 100,
    "capacity_unit": "piece",
    "allowed_categories": [1],
    "is_active": true,
    "notes": "Small items storage",
    "full_path": "Zone A - Main Warehouse > Aisle 01 > Rack 01 > Level 01 > Bin 01"
}
```

---

## 4. Moving Stock

### Putaway (New Stock Arrival)
```bash
POST /api/warehouse/movements/
Authorization: Bearer <token>
Content-Type: application/json

{
    "movement_type": "putaway",
    "from_location": null,
    "to_location": 5,
    "product": 1,
    "quantity": 50,
    "notes": "New stock arrival from supplier"
}
```

### Relocation (Move Between Locations)
```bash
POST /api/warehouse/movements/
Authorization: Bearer <token>
Content-Type: application/json

{
    "movement_type": "relocation",
    "from_location": 5,
    "to_location": 6,
    "product": 1,
    "quantity": 25,
    "notes": "Reorganizing warehouse layout"
}
```

### Picking (Remove Stock)
```bash
POST /api/warehouse/movements/
Authorization: Bearer <token>
Content-Type: application/json

{
    "movement_type": "picking",
    "from_location": 5,
    "to_location": null,
    "product": 1,
    "quantity": 10,
    "notes": "Order fulfillment - Order #12345"
}
```

### Adjustment (Stock Correction)
```bash
POST /api/warehouse/movements/
Authorization: Bearer <token>
Content-Type: application/json

{
    "movement_type": "adjustment",
    "from_location": 5,
    "to_location": 5,
    "product": 1,
    "quantity": 5,
    "notes": "Physical count correction"
}
```

---

## 5. Real-time Inventory Overview

### Get Stock by Product
```bash
GET /api/warehouse/stock-items/by_product/?product_id=1
Authorization: Bearer <token>
```

**Response:**
```json
{
    "stock_items": [
        {
            "id": 1,
            "location": 5,
            "location_code": "ZONE-A-AISLE-01-RACK-01-LEVEL-01-BIN-01",
            "location_name": "Bin 01",
            "product": 1,
            "product_detail": {
                "id": 1,
                "name": "Product A",
                "sku": "PROD-A-001",
                "category": 1,
                "unit": "piece"
            },
            "quantity": 50,
            "reserved_quantity": 10,
            "available_quantity": 40,
            "last_movement_date": "2024-01-15T10:30:00Z"
        }
    ],
    "total_quantity": 50,
    "total_reserved": 10,
    "total_available": 40
}
```

### Get Stock by Location
```bash
GET /api/warehouse/stock-items/by_location/?location_id=5
Authorization: Bearer <token>
```

### Get Low Stock Alerts
```bash
GET /api/warehouse/stock-items/low_stock/?threshold=10
Authorization: Bearer <token>
```

---

## 6. Product Management

### Create Product Category
```bash
POST /api/products/categories/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "Electronics",
    "description": "Electronic products and components"
}
```

### Create Product
```bash
POST /api/products/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "Laptop Computer",
    "sku": "LAPTOP-001",
    "category": 1,
    "unit": "piece",
    "description": "High-performance laptop",
    "weight": 2.5,
    "dimensions": "35x25x2",
    "is_active": true
}
```

---

## 7. User Management

### Create User
```bash
POST /api/users/
Authorization: Bearer <token>
Content-Type: application/json

{
    "username": "warehouse_manager",
    "email": "manager@example.com",
    "password": "securepassword123",
    "password_confirm": "securepassword123",
    "first_name": "John",
    "last_name": "Doe",
    "role": "warehouse_manager",
    "phone": "+1234567890"
}
```

### Get Current User
```bash
GET /api/users/me/
Authorization: Bearer <token>
```

---

## Notes

- All endpoints require JWT authentication (except token endpoints)
- Admin role: Full access to all operations
- Warehouse Manager role: Can manage warehouse, stock, and products
- Worker role: Read-only inventory + can execute movements
- All quantity fields use Decimal with 2 decimal places
- All timestamps are in UTC

