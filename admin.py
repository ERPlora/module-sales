from django.contrib import admin
from .models import SalesConfig, Sale, SaleItem, ActiveCart, ParkedTicket


@admin.register(SalesConfig)
class SalesConfigAdmin(admin.ModelAdmin):
    list_display = ['allow_cash', 'allow_card', 'allow_transfer', 'require_customer', 'allow_discounts']
    fieldsets = (
        ('Payment Methods', {
            'fields': ('allow_cash', 'allow_card', 'allow_transfer')
        }),
        ('Sales Settings', {
            'fields': ('require_customer', 'allow_discounts', 'enable_parked_tickets')
        }),
    )


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['line_total']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['sale_number', 'status', 'user', 'customer_name', 'total', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'user', 'created_at']
    search_fields = ['sale_number', 'customer_name', 'customer_email', 'user__name', 'user__email']
    readonly_fields = ['sale_number', 'created_at', 'updated_at', 'change_given']
    inlines = [SaleItemInline]

    fieldsets = (
        ('Sale Information', {
            'fields': ('sale_number', 'status', 'user')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total')
        }),
        ('Payment', {
            'fields': ('payment_method', 'amount_paid', 'change_given')
        }),
        ('Customer', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Additional', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'product_name', 'quantity', 'unit_price', 'discount_percent', 'line_total']
    list_filter = ['created_at']
    search_fields = ['product_name', 'product_sku']
    readonly_fields = ['line_total', 'created_at']


@admin.register(ActiveCart)
class ActiveCartAdmin(admin.ModelAdmin):
    list_display = ['employee_name', 'item_count', 'age_minutes', 'updated_at']
    search_fields = ['employee_name']
    readonly_fields = ['created_at', 'updated_at', 'item_count', 'age_minutes']

    def item_count(self, obj):
        return obj.item_count
    item_count.short_description = 'Items'

    def age_minutes(self, obj):
        return f"{obj.age_minutes:.1f} min"
    age_minutes.short_description = 'Age'


@admin.register(ParkedTicket)
class ParkedTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'employee_name', 'item_count', 'age_hours', 'is_expired', 'created_at']
    search_fields = ['ticket_number', 'employee_name']
    readonly_fields = ['ticket_number', 'created_at', 'expires_at', 'item_count', 'age_hours', 'is_expired']

    def item_count(self, obj):
        return obj.item_count
    item_count.short_description = 'Items'

    def age_hours(self, obj):
        return f"{obj.age_hours:.1f}h"
    age_hours.short_description = 'Age'
