from django.contrib import admin
from .models import Category, Book, Customer, Sale, SaleItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "price", "quantity", "stock_status_label")
    list_filter = ("category",)
    search_fields = ("title", "author", "isbn")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "created_at")
    search_fields = ("name", "phone", "email")


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ("unit_price", "subtotal")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "total_amount", "created_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("customer__name",)
    inlines = [SaleItemInline]


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ("sale", "book", "quantity", "unit_price", "subtotal")
