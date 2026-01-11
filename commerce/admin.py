from django.contrib import admin
from .models import Product, Price, Coupon, Order, LineItem, Invoice, Receipt, Refund


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type', 'is_active', 'created_at')
    list_filter = ('product_type', 'is_active')
    search_fields = ('name', 'description')


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'amount', 'currency', 'billing_interval', 'is_active')
    list_filter = ('billing_interval', 'is_active', 'currency')
    search_fields = ('product__name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id')
    date_hierarchy = 'created_at'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'status', 'total', 'issue_date')
    list_filter = ('status', 'issue_date')
    search_fields = ('invoice_number', 'user__username')
    date_hierarchy = 'issue_date'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'times_redeemed', 'is_active')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code',)

