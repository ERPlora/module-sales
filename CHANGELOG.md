# Changelog

All notable changes to the Sales module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-25

### Added

- Initial release of Sales module
- **Core Features**
  - Point of Sale (POS) interface
  - Product search and barcode scanning
  - Cart management
  - Multiple payment methods
  - Receipt printing
  - Daily sales summary

- **Models**
  - `Sale`: Sale transactions
  - `SaleItem`: Individual items in a sale
  - `SalesConfig`: Module configuration
  - `ActiveCart`: Current cart in progress
  - `ParkedTicket`: Saved tickets for later
  - `CashRegister`: Cash register management
  - `CashMovement`: Cash in/out movements

- **Views**
  - POS screen (fullscreen mode)
  - Sales history
  - Sales dashboard with statistics
  - Receipt preview

- **Internationalization**
  - English translations (base)
  - Spanish translations

### Technical Details

- Real-time cart updates with HTMX
- Fullscreen POS mode for tablets/touchscreens
- Integration with Inventory module for stock updates
- Integration with Customers module for customer selection
- Integration with Invoicing module for invoice generation

---

## [Unreleased]

### Planned

- Multiple cash registers support
- Offline mode with sync
- Kitchen display integration
- Table management (for restaurants)
- Split payments
- Discounts and promotions
