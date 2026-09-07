from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from shop.models import Book, Category, Customer


class BaseShopTestCase(TestCase):
    """Common fixtures shared across the test suite."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="admin12345", is_staff=True)
        self.category = Category.objects.create(name="Programming", description="Software books")
        self.book = Book.objects.create(
            title="Clean Code",
            author="Robert C. Martin",
            isbn="9780132350884",
            category=self.category,
            price=Decimal("20000.00"),
            quantity=20,
        )
        self.customer = Customer.objects.create(name="John Doe", phone="08012345678", email="john@example.com")

    def login(self):
        self.client.login(username="admin", password="admin12345")
