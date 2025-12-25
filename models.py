from django.db import models
from django.utils import timezone
from decimal import Decimal


class SalesConfig(models.Model):
    """
    Configuración específica del plugin de ventas.

    NOTA: Config global (tax_rate, tax_included, receipt_header, receipt_footer, auto_print)
    se obtiene de HubConfig y StoreConfig. NO duplicar aquí.
    """
    # Payment methods (específico del plugin Sales)
    allow_cash = models.BooleanField(
        default=True,
        verbose_name="Permitir Efectivo",
        help_text="Habilitar efectivo como método de pago"
    )
    allow_card = models.BooleanField(
        default=True,
        verbose_name="Permitir Tarjeta",
        help_text="Habilitar tarjeta como método de pago"
    )
    allow_transfer = models.BooleanField(
        default=False,
        verbose_name="Permitir Transferencia",
        help_text="Habilitar transferencia bancaria como método de pago"
    )

    # Sales-specific settings
    require_customer = models.BooleanField(
        default=False,
        verbose_name="Requiere Cliente",
        help_text="Obligatorio seleccionar cliente para cada venta"
    )
    allow_discounts = models.BooleanField(
        default=True,
        verbose_name="Permitir Descuentos",
        help_text="Permitir aplicar descuentos en el POS"
    )
    enable_parked_tickets = models.BooleanField(
        default=True,
        verbose_name="Habilitar Tickets Aparcados",
        help_text="Permitir aparcar tickets (guardar carrito temporalmente)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'sales'
        db_table = 'sales_config'
        verbose_name = 'Sales Configuration'
        verbose_name_plural = 'Sales Configuration'

    def __str__(self):
        return "Sales Configuration"

    @classmethod
    def get_config(cls):
        """Get or create singleton config"""
        config, created = cls.objects.get_or_create(pk=1)
        return config


class Sale(models.Model):
    """Modelo de Venta"""
    PAYMENT_CASH = 'cash'
    PAYMENT_CARD = 'card'
    PAYMENT_TRANSFER = 'transfer'
    PAYMENT_MIXED = 'mixed'

    PAYMENT_METHODS = [
        (PAYMENT_CASH, 'Efectivo'),
        (PAYMENT_CARD, 'Tarjeta'),
        (PAYMENT_TRANSFER, 'Transferencia'),
        (PAYMENT_MIXED, 'Mixto'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendiente'),
        (STATUS_COMPLETED, 'Completada'),
        (STATUS_CANCELLED, 'Cancelada'),
    ]

    # Sale info
    sale_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Número de Venta"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="Estado"
    )

    # Amounts
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Subtotal"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Impuesto"
    )
    # Tax breakdown by rate (for multi-tax receipts)
    # Format: {"21.00": {"base": 82.64, "tax": 17.36}, "10.00": {"base": 45.45, "tax": 4.55}}
    tax_breakdown = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Desglose de Impuestos",
        help_text="Breakdown by tax rate for multi-tax invoicing"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Descuento"
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total"
    )

    # Payment
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default=PAYMENT_CASH,
        verbose_name="Método de Pago"
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Monto Pagado"
    )
    change_given = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Cambio"
    )

    # Customer (optional)
    customer_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Cliente"
    )
    customer_email = models.EmailField(blank=True, verbose_name="Email Cliente")
    customer_phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono Cliente")

    # Notes
    notes = models.TextField(blank=True, verbose_name="Notas")

    # Cash register (optional - link sale to register shift)
    cash_register = models.ForeignKey(
        'CashRegister',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name="Caja"
    )

    # User who made the sale
    user = models.ForeignKey(
        'accounts.LocalUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name="Empleado"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Venta")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'sales'
        db_table = 'sales_sale'
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['sale_number']),
            models.Index(fields=['status']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Sale {self.sale_number} - ${self.total}"

    def save(self, *args, **kwargs):
        if not self.sale_number:
            # Generate sale number: SALE-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            last_sale = Sale.objects.filter(
                sale_number__startswith=f'SALE-{today}'
            ).order_by('-sale_number').first()

            if last_sale:
                last_num = int(last_sale.sale_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            self.sale_number = f'SALE-{today}-{new_num:04d}'

        super().save(*args, **kwargs)

    def calculate_totals(self):
        """
        Calculate sale totals based on items with multi-tax support.
        Aggregates tax by rate for tax_breakdown field.
        """
        from collections import defaultdict

        total_net = Decimal('0.00')
        total_tax = Decimal('0.00')
        total_gross = Decimal('0.00')
        tax_breakdown = defaultdict(lambda: {'base': Decimal('0.00'), 'tax': Decimal('0.00')})

        for item in self.items.all():
            total_net += item.net_amount
            total_tax += item.tax_amount
            total_gross += item.line_total

            # Aggregate by tax rate
            rate_key = str(item.tax_rate)
            tax_breakdown[rate_key]['base'] += item.net_amount
            tax_breakdown[rate_key]['tax'] += item.tax_amount

        self.subtotal = total_net
        self.tax_amount = total_tax

        # Convert tax_breakdown to serializable format
        self.tax_breakdown = {
            k: {'base': float(v['base']), 'tax': float(v['tax'])}
            for k, v in tax_breakdown.items()
        }

        # Calculate total (gross - discount)
        self.total = total_gross - self.discount_amount

        # Calculate change
        if self.amount_paid > self.total:
            self.change_given = self.amount_paid - self.total
        else:
            self.change_given = Decimal('0.00')

        self.save()


class SaleItem(models.Model):
    """Ítem de venta (línea de factura)"""
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Venta"
    )

    # Product reference (from inventory plugin)
    product_id = models.IntegerField(verbose_name="ID del Producto")
    product_name = models.CharField(max_length=255, verbose_name="Nombre del Producto")
    product_sku = models.CharField(max_length=100, blank=True, verbose_name="SKU")

    # Product type (for services that don't affect stock)
    is_service = models.BooleanField(
        default=False,
        verbose_name="Es Servicio",
        help_text="Services don't affect stock"
    )

    # Item details
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        verbose_name="Cantidad"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Precio Unitario"
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Descuento (%)"
    )

    # Tax fields per item
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tasa de Impuesto (%)",
        help_text="Tax rate applied to this item"
    )
    tax_class_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nombre del Tipo de Impuesto",
        help_text="Tax class name for historical reference"
    )
    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Importe Neto",
        help_text="Amount before tax"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Impuesto",
        help_text="Tax amount for this item"
    )

    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Total Línea"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'sales'
        db_table = 'sales_saleitem'
        verbose_name = "Ítem de Venta"
        verbose_name_plural = "Ítems de Venta"
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        """
        Calculate line totals including per-item tax.
        Respects StoreConfig.tax_included setting.
        """
        from apps.configuration.models import StoreConfig
        store_config = StoreConfig.get_solo()
        tax_included = store_config.tax_included

        # Calculate discount
        discount_amount = self.unit_price * (self.discount_percent / Decimal('100'))
        discounted_price = self.unit_price - discount_amount

        if tax_included:
            # Tax is already included in price - extract it
            tax_divisor = Decimal('1') + (self.tax_rate / Decimal('100'))
            net_unit = discounted_price / tax_divisor
            self.net_amount = (net_unit * self.quantity).quantize(Decimal('0.01'))
            self.line_total = (discounted_price * self.quantity).quantize(Decimal('0.01'))
            self.tax_amount = (self.line_total - self.net_amount).quantize(Decimal('0.01'))
        else:
            # Tax needs to be added to price
            self.net_amount = (discounted_price * self.quantity).quantize(Decimal('0.01'))
            self.tax_amount = (self.net_amount * (self.tax_rate / Decimal('100'))).quantize(Decimal('0.01'))
            self.line_total = (self.net_amount + self.tax_amount).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)


class ActiveCart(models.Model):
    """
    Carrito activo del POS (persistido en BD para sobrevivir reinicios).
    Solo hay un carrito activo por empleado/sesión.
    """
    employee_name = models.CharField(
        max_length=255,
        default='Unknown',
        verbose_name='Empleado',
        help_text='Nombre del empleado que tiene el carrito activo'
    )

    cart_data = models.JSONField(
        default=dict,
        verbose_name='Datos del Carrito',
        help_text='Items del carrito en formato JSON'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')

    class Meta:
        app_label = 'sales'
        db_table = 'sales_active_cart'
        verbose_name = 'Carrito Activo'
        verbose_name_plural = 'Carritos Activos'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['employee_name']),
            models.Index(fields=['-updated_at']),
        ]

    def __str__(self):
        item_count = len(self.cart_data.get('items', []))
        return f"Carrito de {self.employee_name} ({item_count} items)"

    @property
    def item_count(self):
        """Retorna el número de items en el carrito"""
        return len(self.cart_data.get('items', []))

    @property
    def age_minutes(self):
        """Retorna la edad del carrito en minutos"""
        from django.utils import timezone
        delta = timezone.now() - self.updated_at
        return delta.total_seconds() / 60


class ParkedTicket(models.Model):
    """Ticket aparcado temporalmente"""
    ticket_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Número de Ticket"
    )
    cart_data = models.JSONField(
        verbose_name="Datos del Carrito",
        help_text="Carrito serializado: {items: [...], payment_method: '', notes: ''}"
    )

    # Reference to employee who parked the ticket
    employee_name = models.CharField(
        max_length=255,
        verbose_name="Empleado"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        verbose_name="Notas",
        help_text="Notas adicionales sobre el ticket (ej: 'Cliente volvió por más productos')"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Parking"
    )
    expires_at = models.DateTimeField(
        verbose_name="Expira el",
        help_text="Tickets expirados se eliminan automáticamente"
    )

    class Meta:
        app_label = 'sales'
        db_table = 'sales_parkedticket'
        verbose_name = "Ticket Aparcado"
        verbose_name_plural = "Tickets Aparcados"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Parked {self.ticket_number} by {self.employee_name}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            # Generate ticket number: PARK-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            last_ticket = ParkedTicket.objects.filter(
                ticket_number__startswith=f'PARK-{today}'
            ).order_by('-ticket_number').first()

            if last_ticket:
                last_num = int(last_ticket.ticket_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            self.ticket_number = f'PARK-{today}-{new_num:04d}'

        # Set expiration if not set (24 hours from now)
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(hours=24)

        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if ticket has expired"""
        return timezone.now() > self.expires_at

    @property
    def age_hours(self):
        """Get ticket age in hours"""
        delta = timezone.now() - self.created_at
        return delta.total_seconds() / 3600


class CashRegister(models.Model):
    """Caja registradora (turno de trabajo)"""
    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = [
        (STATUS_OPEN, 'Abierta'),
        (STATUS_CLOSED, 'Cerrada'),
    ]

    # Employee who opened the register
    employee_name = models.CharField(
        max_length=255,
        verbose_name="Empleado"
    )

    # Register status
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
        verbose_name="Estado"
    )

    # Amounts
    initial_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto Inicial",
        help_text="Fondo de caja al abrir"
    )
    final_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto Final",
        help_text="Efectivo contado al cerrar"
    )
    expected_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto Esperado",
        help_text="Calculado: inicial + ventas + entradas - salidas"
    )
    difference = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Diferencia",
        help_text="Final - Esperado (positivo = sobrante, negativo = faltante)"
    )

    # Notes
    opening_notes = models.TextField(
        blank=True,
        verbose_name="Notas de Apertura"
    )
    closing_notes = models.TextField(
        blank=True,
        verbose_name="Notas de Cierre"
    )

    # Timestamps
    opened_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Apertura"
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Cierre"
    )

    class Meta:
        app_label = 'sales'
        db_table = 'sales_cashregister'
        verbose_name = "Caja Registradora"
        verbose_name_plural = "Cajas Registradoras"
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['-opened_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        status_display = "Abierta" if self.status == self.STATUS_OPEN else "Cerrada"
        return f"Caja {self.employee_name} - {status_display} ({self.opened_at.strftime('%Y-%m-%d %H:%M')})"

    def calculate_expected_amount(self):
        """Calculate expected amount based on movements and sales"""
        # Get all cash movements
        movements_in = self.movements.filter(type=CashMovement.TYPE_IN).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        movements_out = self.movements.filter(type=CashMovement.TYPE_OUT).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        # Get all cash sales in this register
        cash_sales = self.sales.filter(
            payment_method=Sale.PAYMENT_CASH
        ).aggregate(total=models.Sum('total'))['total'] or Decimal('0.00')

        self.expected_amount = self.initial_amount + cash_sales + movements_in - movements_out
        return self.expected_amount

    def close_register(self, final_amount, closing_notes=''):
        """Close the cash register"""
        self.final_amount = final_amount
        self.closing_notes = closing_notes
        self.closed_at = timezone.now()
        self.status = self.STATUS_CLOSED

        # Calculate expected and difference
        self.calculate_expected_amount()
        if self.expected_amount is not None:
            self.difference = self.final_amount - self.expected_amount

        self.save()


class CashMovement(models.Model):
    """Movimiento de caja (entrada/salida de efectivo)"""
    TYPE_IN = 'in'
    TYPE_OUT = 'out'

    TYPE_CHOICES = [
        (TYPE_IN, 'Entrada'),
        (TYPE_OUT, 'Salida'),
    ]

    # Related cash register
    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.CASCADE,
        related_name='movements',
        verbose_name="Caja"
    )

    # Movement details
    type = models.CharField(
        max_length=3,
        choices=TYPE_CHOICES,
        verbose_name="Tipo"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto"
    )
    reason = models.CharField(
        max_length=255,
        verbose_name="Motivo",
        help_text="Razón del movimiento (ej: 'Pago a proveedor', 'Reposición fondo')"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )

    # Who made the movement
    employee_name = models.CharField(
        max_length=255,
        verbose_name="Empleado"
    )

    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha"
    )

    class Meta:
        app_label = 'sales'
        db_table = 'sales_cashmovement'
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        type_display = "Entrada" if self.type == self.TYPE_IN else "Salida"
        return f"{type_display} ${self.amount} - {self.reason}"
