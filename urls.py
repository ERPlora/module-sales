from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),  # Main sales dashboard

    # POS Screen
    path('pos/', views.pos_screen, name='pos'),
    path('pos/api/products/', views.get_products_for_pos, name='pos_products_api'),
    path('pos/api/complete-sale/', views.complete_sale, name='complete_sale_api'),

    # Active Cart (auto-save)
    path('pos/api/cart/save/', views.save_active_cart, name='save_cart_api'),
    path('pos/api/cart/load/', views.load_active_cart, name='load_cart_api'),
    path('pos/api/cart/clear/', views.clear_active_cart, name='clear_cart_api'),

    # Parking Tickets
    path('pos/api/park/', views.park_ticket, name='park_ticket_api'),
    path('pos/api/parked/', views.parked_tickets_list, name='parked_tickets_api'),
    path('pos/api/recover/<int:ticket_id>/', views.recover_parked_ticket, name='recover_ticket_api'),

    # Sales History
    path('history/', views.sales_history, name='history'),
    path('history/api/list/', views.sales_list_ajax, name='sales_list_ajax'),
    path('history/<int:sale_id>/', views.sale_detail, name='sale_detail'),

    # Sales API (alternative endpoint)
    path('api/sales/', views.sales_list_ajax, name='api_sales'),

    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/api/stats/', views.reports_stats_ajax, name='reports_stats_ajax'),

    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/save/', views.settings_save, name='settings_save'),
]
