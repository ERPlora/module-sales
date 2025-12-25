# Sales & POS Module

Complete Point of Sale system for ERPlora Hub.

## Features

- Full-screen POS interface optimized for touch
- Product search and barcode scanning
- Shopping cart management
- Multiple payment methods
- Sales history and reporting
- Integration with Inventory module
- Real-time stock updates

## Installation

This module is installed automatically via the ERPlora Marketplace.

**Dependencies**: Requires `inventory` module.

## Configuration

Access settings via: **Menu > Ventas > Settings**

## Usage

Access via: **Menu > Ventas**

### POS Screen

Access the full-screen POS via: **Ventas > POS**

Features:
- **Product Grid**: Quick product selection
- **Search**: Find products by name or barcode
- **Cart**: Current transaction items
- **Payment**: Multiple payment methods
- **Fullscreen**: Optimized for kiosk mode

### Sales Dashboard

- **Today's Sales**: Summary of daily transactions
- **Recent Transactions**: List of recent sales
- **Quick Stats**: Revenue, transactions, average ticket

### Sales History

- View all completed sales
- Filter by date, status, payment method
- Export sales data

## Models

| Model | Description |
|-------|-------------|
| `Sale` | Sale header with totals and status |
| `SaleLine` | Individual items in sale |
| `Payment` | Payment records |
| `SalesConfig` | Module settings |

## POS Workflow

```
1. Open POS Screen
2. Add products to cart (click/scan)
3. Adjust quantities if needed
4. Select payment method
5. Complete sale
6. Print receipt (optional)
```

## Keyboard Shortcuts (POS)

| Key | Action |
|-----|--------|
| `F11` | Toggle fullscreen |
| `Enter` | Complete sale |
| `Esc` | Cancel/Clear |

## Permissions

| Permission | Description |
|------------|-------------|
| `sales.view_sale` | View sales |
| `sales.add_sale` | Create sales |
| `sales.change_sale` | Edit sales |
| `sales.delete_sale` | Delete sales |

## Integration with Other Modules

| Module | Integration |
|--------|-------------|
| `inventory` | Stock deduction on sale |
| `customers` | Customer assignment to sales |
| `invoicing` | Invoice generation from sales |
| `cash_register` | Cash session management |

## License

MIT

## Author

ERPlora Team - support@erplora.com
