from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
from datetime import timedelta
import json

from .models import Sale, SaleItem, SalesConfig, ParkedTicket, ActiveCart
from apps.configuration.models import HubConfig, StoreConfig
from apps.accounts.decorators import login_required
from apps.core.htmx import htmx_view

# Import Product model from inventory plugin
try:
    from inventory.models import Product, Category
    INVENTORY_AVAILABLE = True
except ImportError:
    INVENTORY_AVAILABLE = False

# Import Cash Register models
try:
    from cash_register.models import CashMovement, CashSession
    CASH_REGISTER_AVAILABLE = True
except ImportError:
    CASH_REGISTER_AVAILABLE = False


@require_http_methods(["GET"])
@login_required
@htmx_view('sales/index.html', 'sales/partials/content.html')
def dashboard(request):
    """Dashboard principal de ventas con estadísticas"""
    # Obtener configuración global del Hub
    currency = HubConfig.get_value('currency', 'EUR')

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    # Stats de hoy
    sales_today = Sale.objects.filter(
        created_at__date=today,
        status=Sale.STATUS_COMPLETED
    )
    sales_count_today = sales_today.count()
    sales_total_today = sales_today.aggregate(Sum('total'))['total__sum'] or 0

    # Stats de la semana
    sales_week = Sale.objects.filter(
        created_at__date__gte=week_ago,
        status=Sale.STATUS_COMPLETED
    )
    sales_count_week = sales_week.count()
    sales_total_week = sales_week.aggregate(Sum('total'))['total__sum'] or 0

    # Ventas recientes (últimas 5)
    recent_sales = Sale.objects.select_related('user').filter(
        status=Sale.STATUS_COMPLETED
    ).order_by('-created_at')[:5]

    # Métodos de pago (hoy)
    payment_methods_stats = {}
    for method, label in Sale.PAYMENT_METHODS:
        count = sales_today.filter(payment_method=method).count()
        if count > 0:
            total = sales_today.filter(payment_method=method).aggregate(Sum('total'))['total__sum'] or 0
            payment_methods_stats[method] = {
                'label': label,
                'count': count,
                'total': total
            }

    return {
        'sales_count_today': sales_count_today,
        'sales_total_today': sales_total_today,
        'sales_count_week': sales_count_week,
        'sales_total_week': sales_total_week,
        'recent_sales': recent_sales,
        'payment_methods_stats': payment_methods_stats,
        'currency': currency,  # Opcional, ya disponible en templates via context processor
    }


@require_http_methods(["GET"])
@login_required
def pos_screen(request):
    """Pantalla principal del POS"""
    if not INVENTORY_AVAILABLE:
        return render(request, 'sales/error.html', {
            'error': 'Inventory plugin is required for Sales plugin to work'
        })

    config = SalesConfig.get_config()
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')

    context = {
        'config': config,
        'categories': categories,
        'page_title': 'Point of Sale',
    }
    return render(request, 'sales/pos.html', context)


@require_http_methods(["GET"])
def get_products_for_pos(request):
    """API: Obtener productos para el POS con información de impuestos"""
    if not INVENTORY_AVAILABLE:
        return JsonResponse({'success': False, 'error': 'Inventory not available'})

    category_id = request.GET.get('category')
    search = request.GET.get('search', '').strip()

    products = Product.objects.filter(is_active=True).prefetch_related('categories')

    if category_id:
        # Filter by categories (ManyToMany field)
        products = products.filter(categories__id=category_id)

    if search:
        products = products.filter(
            Q(name__icontains=search) | Q(sku__icontains=search)
        )

    products_data = []
    for product in products:
        # Get first category ID if product has categories (ManyToMany field)
        first_category_id = None
        if product.categories.exists():
            first_category_id = product.categories.first().id

        # Get tax info
        tax_class = product.get_effective_tax_class()
        tax_rate = float(product.get_tax_rate())
        tax_class_name = tax_class.name if tax_class else ''

        products_data.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'price': float(product.price),
            'stock': product.stock,
            'category': first_category_id,
            'image': product.image.url if product.image else None,
            # New tax and service fields
            'product_type': product.product_type,
            'is_service': product.is_service,
            'tax_rate': tax_rate,
            'tax_class_name': tax_class_name,
        })

    return JsonResponse({'success': True, 'products': products_data})


@require_http_methods(["POST"])
def complete_sale(request):
    """API: Completar una venta con soporte multi-IVA"""
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        payment_method = data.get('payment_method', 'cash')
        amount_paid = Decimal(str(data.get('amount_paid', 0)))
        customer_name = data.get('customer_name', '')

        if not items:
            return JsonResponse({'success': False, 'error': 'No items in cart'})

        # Create sale
        sale = Sale.objects.create(
            user=request.user,  # Asociar usuario logueado
            payment_method=payment_method,
            amount_paid=amount_paid,
            customer_name=customer_name,
            status=Sale.STATUS_COMPLETED
        )

        # Create sale items with tax info
        for item_data in items:
            product = Product.objects.get(id=item_data['product_id'])

            # Get tax information from product
            tax_class = product.get_effective_tax_class()
            tax_rate = product.get_tax_rate()
            tax_class_name = tax_class.name if tax_class else ''
            is_service = product.is_service

            SaleItem.objects.create(
                sale=sale,
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                is_service=is_service,
                quantity=Decimal(str(item_data['quantity'])),
                unit_price=Decimal(str(item_data['price'])),
                discount_percent=Decimal(str(item_data.get('discount', 0))),
                tax_rate=tax_rate,
                tax_class_name=tax_class_name,
            )

            # Only update stock for physical products (not services)
            if not is_service:
                product.stock -= int(item_data['quantity'])
                product.save()

        # Calculate totals (with multi-tax breakdown)
        sale.calculate_totals()

        # If cash register is available and payment is cash, create cash movement
        if CASH_REGISTER_AVAILABLE and payment_method == 'cash':
            try:
                # Get user's open cash session
                session = CashSession.objects.filter(
                    user=request.user,
                    status='open'
                ).first()

                if session:
                    # Create cash movement for this sale
                    CashMovement.objects.create(
                        session=session,
                        movement_type='sale',
                        amount=sale.total,
                        sale_reference=sale.sale_number,
                        description=f'Venta {sale.sale_number}'
                    )
            except Exception as e:
                # Log error but don't fail the sale
                print(f'[SALES] Error creating cash movement: {e}')

        return JsonResponse({
            'success': True,
            'sale_id': sale.id,
            'sale_number': sale.sale_number,
            'total': float(sale.total),
            'subtotal': float(sale.subtotal),
            'tax_amount': float(sale.tax_amount),
            'tax_breakdown': sale.tax_breakdown,
            'change': float(sale.change_given)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
@htmx_view('sales/history.html', 'sales/partials/history_content.html')
def sales_history(request):
    """Vista de historial de ventas con DataTable"""
    # Filtrar ventas (optimizar con select_related para evitar N+1 queries)
    queryset = Sale.objects.select_related('user').all()

    # Búsqueda
    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(sale_number__icontains=search) |
            Q(customer_name__icontains=search)
        )

    # Filtros de fecha
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    # Filtro de estado
    status = request.GET.get('status')
    if status:
        queryset = queryset.filter(status=status)

    # Filtro de usuario
    user_id = request.GET.get('user_id')
    if user_id:
        queryset = queryset.filter(user_id=user_id)

    # Ordenamiento
    order_by = request.GET.get('order_by', '-created_at')
    queryset = queryset.order_by(order_by)

    # Paginación
    per_page = int(request.GET.get('per_page', 25))
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # Si el target es #sales-table-container, devolver solo la tabla
    if request.headers.get('HX-Request'):
        hx_target = request.headers.get('HX-Target', '')
        if hx_target == 'sales-table-container':
            return render(request, 'sales/partials/sales_table_partial.html', {'page_obj': page_obj})

    return {
        'page_obj': page_obj,
    }


@require_http_methods(["GET"])
def sales_list_ajax(request):
    """API: Lista de ventas para AJAX"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')

    sales = Sale.objects.all()

    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)
    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)
    if status:
        sales = sales.filter(status=status)

    sales_data = []
    for sale in sales[:100]:  # Limit to 100 for performance
        sales_data.append({
            'id': sale.id,
            'sale_number': sale.sale_number,
            'status': sale.status,
            'total': float(sale.total),
            'payment_method': sale.payment_method,
            'customer_name': sale.customer_name,
            'created_at': sale.created_at.strftime('%Y-%m-%d %H:%M'),
        })

    return JsonResponse({'success': True, 'sales': sales_data})


@require_http_methods(["GET"])
@htmx_view('sales/detail.html', 'sales/partials/detail_content.html')
def sale_detail(request, sale_id):
    """Detalle de una venta"""
    sale = get_object_or_404(Sale.objects.select_related('user'), id=sale_id)
    items = sale.items.all()

    return {
        'sale': sale,
        'items': items,
        'page_title': f'Venta {sale.sale_number}',
    }


@require_http_methods(["GET"])
@htmx_view('sales/reports.html', 'sales/partials/reports_content.html')
def reports(request):
    """Vista de reportes"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    sales_week = Sale.objects.filter(
        created_at__date__gte=week_ago,
        status=Sale.STATUS_COMPLETED
    )

    return {
        'sales_count_week': sales_week.count(),
        'sales_total_week': sales_week.aggregate(Sum('total'))['total__sum'] or 0,
        'page_title': 'Sales Reports',
    }


@require_http_methods(["GET"])
def reports_stats_ajax(request):
    """API: Estadísticas para reportes"""
    period = request.GET.get('period', 'week')  # day, week, month, year

    today = timezone.now().date()
    if period == 'day':
        start_date = today
    elif period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    else:  # year
        start_date = today - timedelta(days=365)

    sales = Sale.objects.filter(
        created_at__date__gte=start_date,
        status=Sale.STATUS_COMPLETED
    )

    stats = {
        'total_sales': sales.count(),
        'total_revenue': float(sales.aggregate(Sum('total'))['total__sum'] or 0),
        'avg_sale': float(sales.aggregate(Sum('total'))['total__sum'] or 0) / max(sales.count(), 1),
        'payment_methods': {}
    }

    # Payment methods breakdown
    for method, label in Sale.PAYMENT_METHODS:
        count = sales.filter(payment_method=method).count()
        if count > 0:
            stats['payment_methods'][method] = {
                'label': label,
                'count': count,
                'total': float(sales.filter(payment_method=method).aggregate(Sum('total'))['total__sum'] or 0)
            }

    return JsonResponse({'success': True, 'stats': stats})


@require_http_methods(["GET"])
@login_required
@htmx_view('sales/settings.html', 'sales/partials/settings_content.html')
def settings_view(request):
    """Vista de configuración del módulo de ventas"""
    config = SalesConfig.get_config()

    return {
        'config': config,
        'page_title': 'Sales Settings',
    }


@require_http_methods(["POST"])
@login_required
def settings_save(request):
    """Guardar configuración específica del plugin"""
    try:
        data = json.loads(request.body)
        config = SalesConfig.get_config()

        # Solo guardar configuración específica del plugin Sales
        config.allow_cash = data.get('allow_cash', True)
        config.allow_card = data.get('allow_card', True)
        config.allow_transfer = data.get('allow_transfer', False)
        config.require_customer = data.get('require_customer', False)
        config.allow_discounts = data.get('allow_discounts', True)
        config.enable_parked_tickets = data.get('enable_parked_tickets', True)

        config.save()

        return JsonResponse({'success': True, 'message': 'Configuración guardada correctamente'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================================================
# ACTIVE CART VIEWS (Auto-save cart to survive restarts)
# ============================================================================

@require_http_methods(["POST"])
def save_active_cart(request):
    """API: Guardar carrito activo en BD (auto-save)"""
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        employee_name = data.get('employee_name', 'Unknown')

        # Get or create active cart for this employee (one cart per employee)
        cart, created = ActiveCart.objects.get_or_create(
            employee_name=employee_name,
            defaults={'cart_data': {'items': items}}
        )

        # Update cart data if exists
        if not created:
            cart.cart_data = {'items': items}
            cart.save()

        return JsonResponse({
            'success': True,
            'message': 'Cart saved successfully'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
def load_active_cart(request):
    """API: Cargar carrito activo desde BD"""
    try:
        employee_name = request.GET.get('employee_name', 'Unknown')

        # Get active cart for this employee
        try:
            cart = ActiveCart.objects.get(employee_name=employee_name)
            return JsonResponse({
                'success': True,
                'cart_data': cart.cart_data
            })
        except ActiveCart.DoesNotExist:
            # No active cart found, return empty
            return JsonResponse({
                'success': True,
                'cart_data': {'items': []}
            })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
def clear_active_cart(request):
    """API: Limpiar carrito activo de BD (al completar venta)"""
    try:
        data = json.loads(request.body)
        employee_name = data.get('employee_name', 'Unknown')

        # Delete active cart for this employee
        ActiveCart.objects.filter(employee_name=employee_name).delete()

        return JsonResponse({
            'success': True,
            'message': 'Cart cleared successfully'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================================================
# PARKING TICKETS VIEWS
# ============================================================================

@require_http_methods(["POST"])
def park_ticket(request):
    """API: Aparcar un ticket (guardar carrito temporalmente)"""
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        employee_name = data.get('employee_name', 'Unknown')
        notes = data.get('notes', '')

        if not items:
            return JsonResponse({'success': False, 'error': 'No items in cart to park'})

        # Create parked ticket with auto-generated ticket number
        parked_ticket = ParkedTicket.objects.create(
            cart_data={'items': items},
            employee_name=employee_name,
            notes=notes
        )

        return JsonResponse({
            'success': True,
            'ticket_number': parked_ticket.ticket_number,
            'ticket_id': parked_ticket.id,
            'expires_at': parked_ticket.expires_at.strftime('%Y-%m-%d %H:%M')
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
def parked_tickets_list(request):
    """API: Lista de tickets aparcados (no expirados)"""
    try:
        # Get all non-expired parked tickets
        tickets = ParkedTicket.objects.all().order_by('-created_at')

        # Filter out expired tickets
        active_tickets = []
        for ticket in tickets:
            if not ticket.is_expired:
                active_tickets.append({
                    'id': ticket.id,
                    'ticket_number': ticket.ticket_number,
                    'employee_name': ticket.employee_name,
                    'notes': ticket.notes,
                    'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M'),
                    'expires_at': ticket.expires_at.strftime('%Y-%m-%d %H:%M'),
                    'age_hours': round(ticket.age_hours, 1),
                    'item_count': len(ticket.cart_data.get('items', []))
                })

        return JsonResponse({
            'success': True,
            'tickets': active_tickets,
            'count': len(active_tickets)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
def recover_parked_ticket(request, ticket_id):
    """API: Recuperar un ticket aparcado"""
    try:
        ticket = get_object_or_404(ParkedTicket, id=ticket_id)

        # Check if expired
        if ticket.is_expired:
            return JsonResponse({
                'success': False,
                'error': f'Ticket {ticket.ticket_number} has expired'
            })

        # Get cart data
        cart_data = ticket.cart_data

        # Delete the parked ticket
        ticket.delete()

        return JsonResponse({
            'success': True,
            'cart_data': cart_data,
            'message': f'Ticket {ticket.ticket_number} recovered successfully'
        })

    except ParkedTicket.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Ticket not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
