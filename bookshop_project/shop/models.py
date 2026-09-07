from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("category_list")


isbn_validator = RegexValidator(
    regex=r"^[0-9]{10}([0-9]{3})?$",
    message="Enter a valid 10 or 13 digit ISBN (numbers only, no dashes).",
)


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True, validators=[isbn_validator])
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="books")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    description = models.TextField(blank=True)
    cover_image_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("book_detail", args=[self.pk])

    @property
    def stock_status(self):
        from django.conf import settings as dj_settings
        threshold = getattr(dj_settings, "LOW_STOCK_THRESHOLD", 5)
        if self.quantity <= 0:
            return "out_of_stock"
        if self.quantity <= threshold:
            return "low_stock"
        return "in_stock"

    @property
    def stock_status_label(self):
        return {
            "out_of_stock": "Out of Stock",
            "low_stock": "Low Stock",
            "in_stock": "In Stock",
        }[self.stock_status]


class Customer(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("customer_detail", args=[self.pk])


class Sale(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="sales")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sale #{self.pk} - {self.customer.name}"

    def get_absolute_url(self):
        return reverse("sale_detail", args=[self.pk])


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.book.title}"
