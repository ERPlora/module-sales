"""
Unit tests for Sales models.
"""

import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from sales.models import (
    SalesConfig, Sale, SaleItem, ActiveCart, ParkedTicket,
    CashRegister, CashMovement
)


@pytest.mark.django_db
class TestSalesConfig:
    """Tests for SalesConfig singleton model."""

    def test_get_config_creates_singleton(self):
        """Test get_config creates singleton if not exists."""
        config = SalesConfig.get_config()

        assert config is not None
        assert config.pk == 1

    def test_get_config_returns_existing(self):
        """Test get_config returns existing config."""
        config1 = SalesConfig.get_config()
        config2 = SalesConfig.get_config()

        assert config1.pk == config2.pk

    def test_default_values(self):
        """Test default configuration values."""
        config = SalesConfig.get_config()

        assert config.allow_cash is True
        assert config.allow_card is True
        assert config.allow_transfer is False
        assert config.require_customer is False
        assert config.allow_discounts is True
        assert config.enable_parked_tickets is True

    def test_str_representation(self):
        """Test string representation."""
        config = SalesConfig.get_config()

        assert str(config) == "Sales Configuration"


@pytest.mark.django_db
class TestSale:
    """Tests for Sale model."""

    def test_create_sale_generates_sale_number(self):
        """Test that sale number is auto-generated."""
        sale = Sale.objects.create()

        assert sale.sale_number is not None
        assert sale.sale_number.startswith('SALE-')

    def test_sale_number_format(self):
        """Test sale number format SALE-YYYYMMDD-XXXX."""
        sale = Sale.objects.create()
        today = timezone.now().strftime('%Y%m%d')

        assert f'SALE-{today}-' in sale.sale_number

    def test_sale_number_sequential(self):
        """Test sale numbers are sequential within same day."""
        sale1 = Sale.objects.create()
        sale2 = Sale.objects.create()
        sale3 = Sale.objects.create()

        num1 = int(sale1.sale_number.split('-')[-1])
        num2 = int(sale2.sale_number.split('-')[-1])
        num3 = int(sale3.sale_number.split('-')[-1])

        assert num2 == num1 + 1
        assert num3 == num2 + 1

    def test_default_values(self):
        """Test default sale values."""
        sale = Sale.objects.create()

        assert sale.status == Sale.STATUS_PENDING
        assert sale.subtotal == Decimal('0.00')
        assert sale.tax_amount == Decimal('0.00')
        assert sale.discount_amount == Decimal('0.00')
        assert sale.total == Decimal('0.00')
        assert sale.payment_method == Sale.PAYMENT_CASH
        assert sale.amount_paid == Decimal('0.00')
        assert sale.change_given == Decimal('0.00')

    def test_str_representation(self):
        """Test string representation."""
        sale = Sale.objects.create(total=Decimal('100.00'))

        assert 'Sale' in str(sale)
        assert '100.00' in str(sale)

    def test_payment_methods(self):
        """Test all payment methods are valid."""
        for method, label in Sale.PAYMENT_METHODS:
            sale = Sale.objects.create(payment_method=method)
            assert sale.payment_method == method

    def test_status_choices(self):
        """Test all status choices are valid."""
        for status, label in Sale.STATUS_CHOICES:
            sale = Sale.objects.create(status=status)
            assert sale.status == status

    def test_sale_ordering(self):
        """Test sales are ordered by created_at descending."""
        sale1 = Sale.objects.create()
        sale2 = Sale.objects.create()
        sale3 = Sale.objects.create()

        sales = list(Sale.objects.all())

        assert sales[0] == sale3
        assert sales[1] == sale2
        assert sales[2] == sale1


@pytest.mark.django_db
class TestSaleItem:
    """Tests for SaleItem model."""

    @pytest.fixture
    def sale(self):
        """Create a sale for testing items."""
        return Sale.objects.create()

    def test_create_sale_item(self, sale):
        """Test creating a sale item."""
        item = SaleItem.objects.create(
            sale=sale,
            product_id=1,
            product_name="Test Product",
            product_sku="SKU001",
            quantity=Decimal('2.00'),
            unit_price=Decimal('10.00'),
            tax_rate=Decimal('21.00')
        )

        assert item.id is not None
        assert item.product_name == "Test Product"
        assert item.quantity == Decimal('2.00')

    def test_str_representation(self, sale):
        """Test string representation."""
        item = SaleItem.objects.create(
            sale=sale,
            product_id=1,
            product_name="Test Product",
            quantity=Decimal('3'),
            unit_price=Decimal('10.00')
        )

        assert "Test Product" in str(item)
        assert "3" in str(item)

    def test_is_service_default_false(self, sale):
        """Test is_service defaults to False."""
        item = SaleItem.objects.create(
            sale=sale,
            product_id=1,
            product_name="Product",
            quantity=1,
            unit_price=Decimal('10.00')
        )

        assert item.is_service is False


@pytest.mark.django_db
class TestActiveCart:
    """Tests for ActiveCart model."""

    def test_create_active_cart(self):
        """Test creating an active cart."""
        cart = ActiveCart.objects.create(
            employee_name="John",
            cart_data={'items': [{'id': 1, 'qty': 2}]}
        )

        assert cart.id is not None
        assert cart.employee_name == "John"
        assert len(cart.cart_data['items']) == 1

    def test_default_employee_name(self):
        """Test default employee name."""
        cart = ActiveCart.objects.create()

        assert cart.employee_name == "Unknown"

    def test_item_count_property(self):
        """Test item_count property."""
        cart = ActiveCart.objects.create(
            cart_data={'items': [{'id': 1}, {'id': 2}, {'id': 3}]}
        )

        assert cart.item_count == 3

    def test_item_count_empty_cart(self):
        """Test item_count with empty cart."""
        cart = ActiveCart.objects.create(cart_data={})

        assert cart.item_count == 0

    def test_age_minutes_property(self):
        """Test age_minutes property."""
        cart = ActiveCart.objects.create()

        # Cart just created, age should be very small
        assert cart.age_minutes < 1

    def test_str_representation(self):
        """Test string representation."""
        cart = ActiveCart.objects.create(
            employee_name="Maria",
            cart_data={'items': [{'id': 1}, {'id': 2}]}
        )

        assert "Maria" in str(cart)
        assert "2 items" in str(cart)

    def test_ordering_by_updated_at(self):
        """Test carts are ordered by updated_at descending."""
        cart1 = ActiveCart.objects.create(employee_name="First")
        cart2 = ActiveCart.objects.create(employee_name="Second")

        carts = list(ActiveCart.objects.all())

        assert carts[0] == cart2
        assert carts[1] == cart1


@pytest.mark.django_db
class TestParkedTicket:
    """Tests for ParkedTicket model."""

    def test_create_parked_ticket_generates_number(self):
        """Test ticket number is auto-generated."""
        ticket = ParkedTicket.objects.create(
            cart_data={'items': []},
            employee_name="John"
        )

        assert ticket.ticket_number is not None
        assert ticket.ticket_number.startswith('PARK-')

    def test_ticket_number_format(self):
        """Test ticket number format PARK-YYYYMMDD-XXXX."""
        ticket = ParkedTicket.objects.create(
            cart_data={'items': []},
            employee_name="John"
        )
        today = timezone.now().strftime('%Y%m%d')

        assert f'PARK-{today}-' in ticket.ticket_number

    def test_ticket_number_sequential(self):
        """Test ticket numbers are sequential within same day."""
        ticket1 = ParkedTicket.objects.create(cart_data={}, employee_name="A")
        ticket2 = ParkedTicket.objects.create(cart_data={}, employee_name="B")

        num1 = int(ticket1.ticket_number.split('-')[-1])
        num2 = int(ticket2.ticket_number.split('-')[-1])

        assert num2 == num1 + 1

    def test_default_expires_at(self):
        """Test default expiration is 24 hours from creation."""
        ticket = ParkedTicket.objects.create(
            cart_data={'items': []},
            employee_name="John"
        )

        # Should expire approximately 24 hours from now
        expected = timezone.now() + timedelta(hours=24)
        diff = abs((ticket.expires_at - expected).total_seconds())

        assert diff < 60  # Within 1 minute

    def test_is_expired_property_false(self):
        """Test is_expired returns False for fresh ticket."""
        ticket = ParkedTicket.objects.create(
            cart_data={'items': []},
            employee_name="John"
        )

        assert ticket.is_expired is False

    def test_is_expired_property_true(self):
        """Test is_expired returns True for expired ticket."""
        ticket = ParkedTicket.objects.create(
            cart_data={'items': []},
            employee_name="John",
            expires_at=timezone.now() - timedelta(hours=1)
        )

        assert ticket.is_expired is True

    def test_age_hours_property(self):
        """Test age_hours property."""
        ticket = ParkedTicket.objects.create(
            cart_data={'items': []},
            employee_name="John"
        )

        # Just created, age should be very small
        assert ticket.age_hours < 0.1

    def test_str_representation(self):
        """Test string representation."""
        ticket = ParkedTicket.objects.create(
            cart_data={'items': []},
            employee_name="John"
        )

        assert "Parked" in str(ticket)
        assert "John" in str(ticket)


@pytest.mark.django_db
class TestCashRegister:
    """Tests for CashRegister model."""

    def test_create_cash_register(self):
        """Test creating a cash register."""
        register = CashRegister.objects.create(
            employee_name="John",
            initial_amount=Decimal('100.00')
        )

        assert register.id is not None
        assert register.status == CashRegister.STATUS_OPEN
        assert register.initial_amount == Decimal('100.00')

    def test_default_status_is_open(self):
        """Test default status is open."""
        register = CashRegister.objects.create(
            employee_name="John",
            initial_amount=Decimal('100.00')
        )

        assert register.status == CashRegister.STATUS_OPEN

    def test_close_register(self):
        """Test closing a cash register."""
        register = CashRegister.objects.create(
            employee_name="John",
            initial_amount=Decimal('100.00')
        )

        register.close_register(
            final_amount=Decimal('150.00'),
            closing_notes="End of day"
        )

        register.refresh_from_db()
        assert register.status == CashRegister.STATUS_CLOSED
        assert register.final_amount == Decimal('150.00')
        assert register.closing_notes == "End of day"
        assert register.closed_at is not None

    def test_str_representation(self):
        """Test string representation."""
        register = CashRegister.objects.create(
            employee_name="Maria",
            initial_amount=Decimal('50.00')
        )

        assert "Maria" in str(register)
        assert "Abierta" in str(register)

    def test_ordering_by_opened_at(self):
        """Test registers are ordered by opened_at descending."""
        reg1 = CashRegister.objects.create(employee_name="A", initial_amount=100)
        reg2 = CashRegister.objects.create(employee_name="B", initial_amount=100)

        registers = list(CashRegister.objects.all())

        assert registers[0] == reg2
        assert registers[1] == reg1


@pytest.mark.django_db
class TestCashMovement:
    """Tests for CashMovement model."""

    @pytest.fixture
    def cash_register(self):
        """Create a cash register for testing."""
        return CashRegister.objects.create(
            employee_name="John",
            initial_amount=Decimal('100.00')
        )

    def test_create_cash_movement_in(self, cash_register):
        """Test creating a cash-in movement."""
        movement = CashMovement.objects.create(
            cash_register=cash_register,
            type=CashMovement.TYPE_IN,
            amount=Decimal('50.00'),
            reason="Extra change",
            employee_name="John"
        )

        assert movement.id is not None
        assert movement.type == CashMovement.TYPE_IN
        assert movement.amount == Decimal('50.00')

    def test_create_cash_movement_out(self, cash_register):
        """Test creating a cash-out movement."""
        movement = CashMovement.objects.create(
            cash_register=cash_register,
            type=CashMovement.TYPE_OUT,
            amount=Decimal('25.00'),
            reason="Supplier payment",
            employee_name="John"
        )

        assert movement.type == CashMovement.TYPE_OUT

    def test_str_representation_in(self, cash_register):
        """Test string representation for cash-in."""
        movement = CashMovement.objects.create(
            cash_register=cash_register,
            type=CashMovement.TYPE_IN,
            amount=Decimal('50.00'),
            reason="Test",
            employee_name="John"
        )

        assert "Entrada" in str(movement)
        assert "50.00" in str(movement)

    def test_str_representation_out(self, cash_register):
        """Test string representation for cash-out."""
        movement = CashMovement.objects.create(
            cash_register=cash_register,
            type=CashMovement.TYPE_OUT,
            amount=Decimal('30.00'),
            reason="Test",
            employee_name="John"
        )

        assert "Salida" in str(movement)

    def test_ordering_by_created_at(self, cash_register):
        """Test movements are ordered by created_at descending."""
        mov1 = CashMovement.objects.create(
            cash_register=cash_register,
            type=CashMovement.TYPE_IN,
            amount=10,
            reason="First",
            employee_name="A"
        )
        mov2 = CashMovement.objects.create(
            cash_register=cash_register,
            type=CashMovement.TYPE_OUT,
            amount=20,
            reason="Second",
            employee_name="B"
        )

        movements = list(CashMovement.objects.all())

        assert movements[0] == mov2
        assert movements[1] == mov1


@pytest.mark.django_db
class TestSaleIndexes:
    """Tests for Sale model indexes."""

    def test_created_at_index_exists(self):
        """Test created_at index exists."""
        indexes = Sale._meta.indexes
        index_fields = [idx.fields for idx in indexes]

        assert ['-created_at'] in index_fields

    def test_sale_number_index_exists(self):
        """Test sale_number index exists."""
        indexes = Sale._meta.indexes
        index_fields = [idx.fields for idx in indexes]

        assert ['sale_number'] in index_fields

    def test_status_index_exists(self):
        """Test status index exists."""
        indexes = Sale._meta.indexes
        index_fields = [idx.fields for idx in indexes]

        assert ['status'] in index_fields
