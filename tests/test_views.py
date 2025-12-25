"""
Integration tests for Sales views.
"""

import pytest
import json
from decimal import Decimal
from django.test import Client
from django.urls import reverse

from sales.models import (
    Sale, SaleItem, SalesConfig, ActiveCart, ParkedTicket,
    CashRegister, CashMovement
)


@pytest.fixture
def client():
    """Create test client."""
    return Client()


@pytest.fixture
def sample_sale():
    """Create a sample completed sale."""
    sale = Sale.objects.create(
        status=Sale.STATUS_COMPLETED,
        subtotal=Decimal('100.00'),
        tax_amount=Decimal('21.00'),
        total=Decimal('121.00'),
        payment_method=Sale.PAYMENT_CASH,
        amount_paid=Decimal('150.00'),
        change_given=Decimal('29.00'),
        customer_name="Test Customer"
    )
    return sale


@pytest.fixture
def sample_cash_register():
    """Create a sample cash register."""
    return CashRegister.objects.create(
        employee_name="Test Employee",
        initial_amount=Decimal('100.00')
    )


@pytest.mark.django_db
class TestSalesHistoryView:
    """Tests for sales history view."""

    def test_sales_history_get(self, client, sample_sale):
        """Test GET sales history."""
        response = client.get('/modules/sales/history/')

        assert response.status_code == 200

    def test_sales_history_htmx(self, client, sample_sale):
        """Test HTMX request returns partial."""
        response = client.get(
            '/modules/sales/history/',
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200

    def test_sales_history_search(self, client, sample_sale):
        """Test sales history with search."""
        response = client.get('/modules/sales/history/?search=Test')

        assert response.status_code == 200


@pytest.mark.django_db
class TestSalesListAjaxView:
    """Tests for sales list AJAX API."""

    def test_list_ajax_empty(self, client):
        """Test AJAX list when empty."""
        response = client.get('/modules/sales/api/list/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['sales'] == []

    def test_list_ajax_with_sales(self, client, sample_sale):
        """Test AJAX list with sales."""
        response = client.get('/modules/sales/api/list/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert len(data['sales']) == 1

    def test_list_ajax_filter_status(self, client, sample_sale):
        """Test AJAX list filter by status."""
        # Create a pending sale
        Sale.objects.create(status=Sale.STATUS_PENDING)

        response = client.get('/modules/sales/api/list/?status=completed')
        data = json.loads(response.content)
        assert len(data['sales']) == 1
        assert data['sales'][0]['status'] == 'completed'


@pytest.mark.django_db
class TestSaleDetailView:
    """Tests for sale detail view."""

    def test_detail_view(self, client, sample_sale):
        """Test GET sale detail."""
        response = client.get(f'/modules/sales/detail/{sample_sale.id}/')

        assert response.status_code == 200

    def test_detail_view_not_found(self, client):
        """Test GET sale not found."""
        response = client.get('/modules/sales/detail/99999/')

        assert response.status_code == 404

    def test_detail_view_htmx(self, client, sample_sale):
        """Test HTMX detail request."""
        response = client.get(
            f'/modules/sales/detail/{sample_sale.id}/',
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200


@pytest.mark.django_db
class TestReportsView:
    """Tests for reports view."""

    def test_reports_get(self, client):
        """Test GET reports page."""
        response = client.get('/modules/sales/reports/')

        assert response.status_code == 200

    def test_reports_htmx(self, client):
        """Test HTMX reports request."""
        response = client.get(
            '/modules/sales/reports/',
            HTTP_HX_REQUEST='true'
        )

        assert response.status_code == 200


@pytest.mark.django_db
class TestReportsStatsAjax:
    """Tests for reports stats AJAX API."""

    def test_stats_ajax_day(self, client, sample_sale):
        """Test stats for day period."""
        response = client.get('/modules/sales/api/reports/stats/?period=day')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'stats' in data

    def test_stats_ajax_week(self, client, sample_sale):
        """Test stats for week period."""
        response = client.get('/modules/sales/api/reports/stats/?period=week')

        data = json.loads(response.content)
        assert data['success'] is True

    def test_stats_ajax_month(self, client):
        """Test stats for month period."""
        response = client.get('/modules/sales/api/reports/stats/?period=month')

        data = json.loads(response.content)
        assert data['success'] is True


@pytest.mark.django_db
class TestActiveCartViews:
    """Tests for active cart API endpoints."""

    def test_save_active_cart(self, client):
        """Test saving active cart."""
        response = client.post(
            '/modules/sales/api/cart/save/',
            data=json.dumps({
                'items': [{'id': 1, 'qty': 2}],
                'employee_name': 'John'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

    def test_load_active_cart_empty(self, client):
        """Test loading non-existent cart."""
        response = client.get('/modules/sales/api/cart/load/?employee_name=Unknown')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert data['cart_data']['items'] == []

    def test_load_active_cart_existing(self, client):
        """Test loading existing cart."""
        # First save a cart
        ActiveCart.objects.create(
            employee_name='Maria',
            cart_data={'items': [{'id': 1}]}
        )

        response = client.get('/modules/sales/api/cart/load/?employee_name=Maria')

        data = json.loads(response.content)
        assert data['success'] is True
        assert len(data['cart_data']['items']) == 1

    def test_clear_active_cart(self, client):
        """Test clearing active cart."""
        # First create a cart
        ActiveCart.objects.create(employee_name='John', cart_data={'items': []})

        response = client.post(
            '/modules/sales/api/cart/clear/',
            data=json.dumps({'employee_name': 'John'}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True

        # Verify cart is deleted
        assert not ActiveCart.objects.filter(employee_name='John').exists()


@pytest.mark.django_db
class TestParkedTicketViews:
    """Tests for parked ticket API endpoints."""

    def test_park_ticket(self, client):
        """Test parking a ticket."""
        response = client.post(
            '/modules/sales/api/tickets/park/',
            data=json.dumps({
                'items': [{'id': 1, 'qty': 2}],
                'employee_name': 'John',
                'notes': 'Customer will return'
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'ticket_number' in data

    def test_park_ticket_no_items(self, client):
        """Test parking empty cart fails."""
        response = client.post(
            '/modules/sales/api/tickets/park/',
            data=json.dumps({
                'items': [],
                'employee_name': 'John'
            }),
            content_type='application/json'
        )

        data = json.loads(response.content)
        assert data['success'] is False
        assert 'error' in data

    def test_parked_tickets_list(self, client):
        """Test listing parked tickets."""
        # Create some parked tickets
        ParkedTicket.objects.create(
            cart_data={'items': []},
            employee_name='John'
        )

        response = client.get('/modules/sales/api/tickets/list/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'tickets' in data

    def test_recover_parked_ticket(self, client):
        """Test recovering a parked ticket."""
        ticket = ParkedTicket.objects.create(
            cart_data={'items': [{'id': 1}]},
            employee_name='John'
        )

        response = client.post(f'/modules/sales/api/tickets/recover/{ticket.id}/')

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['success'] is True
        assert 'cart_data' in data

        # Verify ticket is deleted
        assert not ParkedTicket.objects.filter(id=ticket.id).exists()

    def test_recover_nonexistent_ticket(self, client):
        """Test recovering non-existent ticket."""
        response = client.post('/modules/sales/api/tickets/recover/99999/')

        assert response.status_code == 404


@pytest.mark.django_db
class TestCompleteSaleView:
    """Tests for complete sale API."""

    def test_complete_sale_no_items(self, client):
        """Test completing sale with no items fails."""
        response = client.post(
            '/modules/sales/api/complete/',
            data=json.dumps({
                'items': [],
                'payment_method': 'cash',
                'amount_paid': 100
            }),
            content_type='application/json'
        )

        data = json.loads(response.content)
        assert data['success'] is False
        assert 'error' in data


@pytest.mark.django_db
class TestSettingsView:
    """Tests for sales settings."""

    def test_settings_view_get(self, client):
        """Test GET settings page."""
        # Note: This requires login, so it may redirect
        response = client.get('/modules/sales/settings/')

        # Either 200 (if no login required in test) or redirect
        assert response.status_code in [200, 302]

    def test_settings_save(self, client):
        """Test saving settings."""
        response = client.post(
            '/modules/sales/settings/save/',
            data=json.dumps({
                'allow_cash': True,
                'allow_card': True,
                'allow_transfer': False,
                'require_customer': False,
                'allow_discounts': True,
                'enable_parked_tickets': True
            }),
            content_type='application/json'
        )

        # May require login
        assert response.status_code in [200, 302]
