# Order Fulfillment & Distribution Module

## Overview

The Order Fulfillment & Distribution module implements a comprehensive order-to-delivery workflow for an ERP system. It manages the complete lifecycle from order creation through allocation, picking, packing, shipping, and final delivery.

## Architecture

### Models Layer
- **Order**: Main order entity with status workflow
- **OrderItem**: Individual items within orders
- **Allocation**: Inventory reservations for order items
- **PickingTask**: Tasks for warehouse picking operations
- **PickingItem**: Individual items within picking tasks
- **PackingTask**: Tasks for packing operations
- **Package**: Physical packages containing order items
- **PackageItem**: Items within packages
- **Shipment**: Shipments containing packages
- **ShipmentItem**: Packages within shipments
- **AuditLog**: Audit trail for all changes

### Services Layer
All business logic is encapsulated in services:

- **OrderService**: Order creation, approval, updates
- **AllocationService**: Inventory allocation and reservation
- **PickingService**: Picking task management
- **PackingService**: Packing task and package management
- **ShippingService**: Shipment creation and tracking
- **Workflow**: Status transition validation

### Adapters
Clean interface to external modules:

- **InventoryAdapter**: Interface for inventory management
- **MockInventoryAdapter**: Deterministic mock for testing

### Views & Serializers
DRF-based REST API with comprehensive validation and structured responses.

## Order Fulfillment Workflow

```
CREATED → APPROVED → ALLOCATED → PICKING → PACKING → SHIPPED → DELIVERED
   ↓         ↓         ↓           ↓         ↓         ↓         ↓
CANCELLED CANCELLED CANCELLED  CANCELLED CANCELLED CANCELLED
```

### Status Definitions

1. **CREATED**: Order placed by customer
2. **APPROVED**: Order approved for fulfillment
3. **ALLOCATED**: Inventory allocated/reserved
4. **PICKING**: Picking tasks generated and in progress
5. **PACKING**: Packing tasks created and in progress
6. **SHIPPED**: Order shipped via carrier
7. **DELIVERED**: Order delivered to customer
8. **CANCELLED**: Order cancelled

## API Endpoints

Base URL: `/api/order-fulfillment/`

### Orders API (`/api/order-fulfillment/orders/`)

#### Create Order
```http
POST /api/order-fulfillment/orders/
Content-Type: application/json

{
  "warehouse_id": "uuid",
  "priority": "MEDIUM",
  "notes": "Order notes",
  "items": [
    {
      "product_id": "uuid",
      "product_sku": "PROD-001",
      "product_name": "Product Name",
      "quantity": 10.0,
      "unit_price": 25.50,
      "unit_weight": 1.5
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "order-uuid",
    "order_number": "ORD-20241205001",
    "status": "CREATED",
    "total_amount": 255.00
  }
}
```

#### Approve Order
```http
POST /api/order-fulfillment/orders/{order_id}/approve/
```

#### Allocate Inventory
```http
POST /api/order-fulfillment/orders/{order_id}/allocate/
```

#### Generate Picking Tasks
```http
POST /api/order-fulfillment/orders/{order_id}/generate_picking/
```

#### Create Packing Task
```http
POST /api/order-fulfillment/orders/{order_id}/create_packing/
```

#### Create Shipment
```http
POST /api/order-fulfillment/orders/{order_id}/create_shipment/
Content-Type: application/json

{
  "carrier": "FedEx",
  "shipping_cost": 15.99,
  "ship_from_address": {
    "street": "123 Warehouse St",
    "city": "Warehouse City",
    "country": "US"
  },
  "ship_to_address": {
    "street": "456 Customer Ave",
    "city": "Customer City",
    "country": "US"
  },
  "estimated_delivery_date": "2024-12-10T10:00:00Z"
}
```

#### Cancel Order
```http
POST /api/order-fulfillment/orders/{order_id}/cancel/
Content-Type: application/json

{
  "reason": "Customer requested cancellation"
}
```

### Picking API (`/api/order-fulfillment/picking/`)

#### Assign Picker
```http
POST /api/order-fulfillment/picking/{task_id}/assign_picker/
Content-Type: application/json

{
  "picker_id": "user-uuid"
}
```

#### Update Picked Quantities
```http
POST /api/order-fulfillment/picking/{task_id}/update_picked/
Content-Type: application/json

{
  "item_updates": [
    {
      "order_item_id": "item-uuid",
      "quantity_picked": 10.0
    }
  ]
}
```

#### Complete Picking Task
```http
POST /api/order-fulfillment/picking/{task_id}/complete/
```

### Packing API (`/api/order-fulfillment/packing/`)

#### Create Package
```http
POST /api/order-fulfillment/packing/{task_id}/create_package/
Content-Type: application/json

{
  "package_type": "BOX",
  "length": 30.0,
  "width": 20.0,
  "height": 15.0,
  "empty_weight": 0.5,
  "max_weight": 25.0
}
```

#### Add Item to Package
```http
POST /api/order-fulfillment/packing/{task_id}/add_item/
Content-Type: application/json

{
  "package_id": "package-uuid",
  "order_item_id": "item-uuid",
  "quantity": 5.0
}
```

#### Finalize Package
```http
POST /api/order-fulfillment/packing/{task_id}/finalize_package/
Content-Type: application/json

{
  "package_id": "package-uuid"
}
```

#### Complete Packing Task
```http
POST /api/order-fulfillment/packing/{task_id}/complete/
```

### Shipment API (`/api/order-fulfillment/shipments/`)

#### Assign Tracking Number
```http
POST /api/order-fulfillment/shipments/{shipment_id}/assign_tracking/
Content-Type: application/json

{
  "tracking_number": "TRK123456789"
}
```

#### Update Shipment Status
```http
POST /api/order-fulfillment/shipments/{shipment_id}/update_status/
Content-Type: application/json

{
  "status": "IN_TRANSIT",
  "notes": "Package loaded on truck"
}
```

#### Generate Manifest
```http
GET /api/order-fulfillment/shipments/{shipment_id}/manifest/
```

## Inventory Adapter Integration

### Interface Methods

```python
class InventoryAdapterInterface(ABC):
    def check_availability(self, sku: str, qty: Decimal, warehouse_id: UUID) -> List[Dict[str, Any]]:
        """Check product availability in warehouse."""

    def reserve(self, sku: str, qty: Decimal, location: str, reference: str) -> Dict[str, Any]:
        """Reserve inventory at location."""

    def release(self, reservation_id: str) -> bool:
        """Release inventory reservation."""
```

### Switching Adapters

```python
from order_fulfillment.adapters.inventory_adapter import switch_to_real_adapter

# Switch to real inventory system
switch_to_real_adapter(RealInventoryAdapter())
```

## Testing

### Running Tests

```bash
cd logistic
python manage.py test order_fulfillment.tests
```

### Test Coverage

- **test_order_flow.py**: Complete order fulfillment workflow
- **test_allocation.py**: Inventory allocation logic and edge cases

## Security & Permissions

### Permission Classes

- **IsWarehouseStaff**: Access for warehouse staff users
- **IsOrderOwnerOrWarehouseStaff**: Order owners or warehouse staff
- **CanApproveOrders**: Order approval permissions

### User Groups

Configure these groups in your Django admin:
- `warehouse_staff`: Basic warehouse operations
- `warehouse_manager`: Order approval and management
- `order_supervisor`: Order lifecycle oversight

## Data Integrity

### Transactions

All service methods use Django's `transaction.atomic()` to ensure data consistency across related operations.

### Validation

Comprehensive validation at serializer and service levels prevents invalid state transitions and data entry.

### Audit Trail

All status changes and significant operations are logged in the `AuditLog` model for compliance and debugging.

## Performance Considerations

### Database Indexes

Key fields are indexed for optimal query performance:
- Status fields for workflow filtering
- Foreign keys for relationships
- Timestamps for ordering and filtering

### Query Optimization

- Select related objects to minimize database queries
- Prefetch related data for complex operations
- Efficient aggregation for summaries

## Monitoring & Logging

### Logging

All service operations log key events using Python's logging framework.

### Audit Logs

Comprehensive audit trail tracks:
- Entity changes
- User actions
- Status transitions
- Business rule violations

## Integration Points

### External Modules

The module integrates with other ERP modules via adapters:

- **Inventory Management**: Stock checking and reservation
- **Warehouse Management**: Location and zone information
- **Product Management**: Product details and SKUs
- **Customer Management**: Customer information

### API Response Format

All endpoints return structured responses:

**Success:**
```json
{
  "success": true,
  "data": { /* response data */ }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": { /* additional error info */ }
  }
}
```

## Deployment

1. Add `order_fulfillment` to `INSTALLED_APPS`
2. Run migrations: `python manage.py makemigrations order_fulfillment`
3. Configure inventory adapter for production
4. Set up user groups and permissions
5. Configure logging and monitoring

## Future Enhancements

- Batch operations for bulk processing
- Advanced picking algorithms (route optimization)
- Integration with shipping carrier APIs
- Real-time tracking updates
- Mobile app for warehouse operations
- Automated rule-based approvals
