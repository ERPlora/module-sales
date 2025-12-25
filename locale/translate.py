#!/usr/bin/env python3
"""
Script to automatically translate sales plugin strings to Spanish
"""

translations = {
    # Sale information
    "Sale": "Venta",
    "Customer": "Cliente",
    "No customer": "Sin cliente",
    "Employee": "Empleado",
    "Payment Method": "Método de Pago",
    "Amount Paid": "Cantidad Pagada",
    "Change Given": "Cambio Dado",
    "Items": "Artículos",
    "Item": "Artículo",

    # Amounts and calculations
    "Qty:": "Cant:",
    "Subtotal:": "Subtotal:",
    "Discount:": "Descuento:",
    "Tax:": "Impuesto:",
    "Total:": "Total:",
    "Subtotal": "Subtotal",
    "Discount": "Descuento",
    "Tax": "Impuesto",
    "Total": "Total",

    # Actions
    "Back to History": "Volver al Historial",
    "Reprint Receipt": "Reimprimir Recibo",
    "Clear": "Limpiar",
    "Clear Cart": "Vaciar Carrito",
    "Cancel": "Cancelar",
    "Complete Sale": "Completar Venta",
    "Print": "Imprimir",
    "Print Receipt": "Imprimir Recibo",
    "Processing...": "Procesando...",

    # Point of Sale
    "Point of Sale": "Punto de Venta",
    "Search products...": "Buscar productos...",
    "Cart": "Carrito",
    "All": "Todos",
    "Out of Stock": "Sin Stock",
    "Add": "Añadir",
    "Remove": "Eliminar",
    "Empty": "Vacío",
    "Your cart is empty": "Tu carrito está vacío",
    "Add products to start a sale": "Añade productos para iniciar una venta",

    # Filters and status
    "All": "Todos",
    "Status": "Estado",
    "From": "Desde",
    "To": "Hasta",
    "Show": "Mostrar",
    "Showing": "Mostrando",
    "of": "de",
    "entries": "registros",

    # Dashboard
    "Dashboard": "Panel de Control",
    "Sales": "Ventas",
    "Sales and point of sale management": "Gestión de ventas y punto de venta",
    "Sales Today": "Ventas Hoy",
    "Revenue Today": "Ingresos Hoy",
    "Sales This Week": "Ventas Semana",
    "Revenue This Week": "Ingresos Semana",
    "Quick Actions": "Acciones Rápidas",
    "Reports": "Reportes",
    "Settings": "Configuración",
    "Configuration": "Configuración",
    "Recent Sales": "Ventas Recientes",
    "View All": "Ver Todas",
    "No recent sales": "No hay ventas recientes",
    "Make first sale": "Hacer primera venta",
    "Payment Methods (Today)": "Métodos de Pago (Hoy)",
    "Method": "Método",
    "Amount": "Cantidad",
    "No sales found": "No se encontraron ventas",

    # Payment methods
    "Cash": "Efectivo",
    "Card": "Tarjeta",
    "Credit Card": "Tarjeta de Crédito",
    "Debit Card": "Tarjeta de Débito",
    "Transfer": "Transferencia",
    "Check": "Cheque",
    "Other": "Otro",

    # Products
    "Product": "Producto",
    "Products": "Productos",
    "Price": "Precio",
    "Stock": "Stock",
    "Category": "Categoría",
    "Categories": "Categorías",
    "Available": "Disponible",
    "Not Available": "No Disponible",

    # Customers
    "Customer Name": "Nombre del Cliente",
    "Customer Optional": "Cliente Opcional",
    "Select Customer": "Seleccionar Cliente",
    "New Customer": "Nuevo Cliente",

    # Receipt
    "Receipt": "Recibo",
    "Receipt Number": "Número de Recibo",
    "Date": "Fecha",
    "Time": "Hora",
    "Thank you for your purchase!": "¡Gracias por su compra!",
    "Come back soon": "Vuelva pronto",

    # Errors and messages
    "Error": "Error",
    "Success": "Éxito",
    "Sale completed successfully": "Venta completada exitosamente",
    "Error completing sale": "Error al completar la venta",
    "Cart is empty": "El carrito está vacío",
    "Please add products to the cart": "Por favor añade productos al carrito",
    "Invalid payment amount": "Cantidad de pago inválida",
    "Payment amount must be greater than or equal to total": "La cantidad de pago debe ser mayor o igual al total",

    # Units and measurements
    "Unit": "Unidad",
    "Units": "Unidades",
    "Each": "Cada uno",
    "Piece": "Pieza",
    "Pieces": "Piezas",

    # Dates and times
    "Today": "Hoy",
    "Yesterday": "Ayer",
    "This Week": "Esta Semana",
    "Last Week": "Última Semana",
    "This Month": "Este Mes",
    "Last Month": "Último Mes",

    # General
    "Yes": "Sí",
    "No": "No",
    "Save": "Guardar",
    "Edit": "Editar",
    "Delete": "Eliminar",
    "Close": "Cerrar",
    "Back": "Volver",
    "Next": "Siguiente",
    "Previous": "Anterior",
    "Search": "Buscar",
    "Filter": "Filtrar",
    "Reset": "Restablecer",
    "Apply": "Aplicar",
    "Actions": "Acciones",
    "View": "Ver",
    "Details": "Detalles",
    "View Details": "Ver Detalles",
}

def update_po_file(po_file):
    """Update .po file with Spanish translations"""
    import re

    with open(po_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update header
    content = content.replace('#, fuzzy', '')
    content = content.replace('YEAR-MO-DA HO:MI+ZONE', '2025-11-24 12:00+0000')
    content = content.replace('FULL NAME <EMAIL@ADDRESS>', 'CPOS Team <info@erplora.com>')
    content = content.replace('Language: \\n', 'Language: es\\n')

    # Update translations
    translated_count = 0
    for english, spanish in translations.items():
        # Escape special characters for regex
        english_escaped = re.escape(english)
        # Find msgid and empty msgstr pattern
        pattern = f'msgid "{english_escaped}"\\nmsgstr ""'
        if re.search(pattern, content):
            replacement = f'msgid "{english}"\\nmsgstr "{spanish}"'
            content = re.sub(pattern, replacement, content)
            translated_count += 1

    with open(po_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Updated {po_file}")
    print(f"✅ Translated {translated_count} strings")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        update_po_file(sys.argv[1])
    else:
        update_po_file('es/LC_MESSAGES/django.po')
