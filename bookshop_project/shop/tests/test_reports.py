from decimal import Decimal

from django.urls import reverse

from shop.models import Book

from .base import BaseShopTestCase
from .helpers import formset_data


class ReportsTests(BaseShopTestCase):

    def setUp(self):
        super().setUp()
        self.login()
        self.second_book = Book.objects.create(
            title="The Pragmatic Programmer", author="Andrew Hunt", isbn="9780135957059",
            category=self.category, price=Decimal("25000.00"), quantity=10,
        )

    def _record_sale(self, items):
        data = {"customer": self.customer.pk}
        data.update(formset_data(items))
        return self.client.post(reverse("sale_create"), data)

    def test_sales_report_shows_correct_transaction_count(self):
        self._record_sale([(self.book, 1)])
        self._record_sale([(self.second_book, 1)])
        response = self.client.get(reverse("sales_report"))
        self.assertContains(response, ">2<")  # 2 transactions

    def test_sales_report_shows_correct_total_revenue(self):
        self._record_sale([(self.book, 2)])       # 20000 * 2 = 40000
        self._record_sale([(self.second_book, 1)])  # 25000 * 1 = 25000
        response = self.client.get(reverse("sales_report"))
        self.assertContains(response, "65000.00")

    def test_sales_report_date_filter_excludes_out_of_range_sales(self):
        self._record_sale([(self.book, 1)])
        response = self.client.get(reverse("sales_report"), {"from": "2099-01-01"})
        self.assertContains(response, ">0<")  # no sales in a future-dated range

    def test_inventory_report_shows_correct_totals(self):
        # base fixture: 1 book, quantity 20. plus second_book quantity 10 -> total_books=2, total_stock=30
        response = self.client.get(reverse("inventory_report"))
        self.assertContains(response, ">2<")   # total books
        self.assertContains(response, ">30<")  # total stock

    def test_inventory_report_lists_low_stock_books(self):
        from django.conf import settings
        self.book.quantity = settings.LOW_STOCK_THRESHOLD
        self.book.save()
        response = self.client.get(reverse("inventory_report"))
        self.assertContains(response, self.book.title)

    def test_inventory_report_lists_out_of_stock_books(self):
        self.second_book.quantity = 0
        self.second_book.save()
        response = self.client.get(reverse("inventory_report"))
        self.assertContains(response, self.second_book.title)
        self.assertContains(response, "Out of Stock")

    def test_inventory_report_stock_value_is_correct(self):
        # 20000*20 + 25000*10 = 400000 + 250000 = 650000
        response = self.client.get(reverse("inventory_report"))
        self.assertContains(response, "650000.00")
