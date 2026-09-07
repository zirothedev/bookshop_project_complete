from decimal import Decimal

from django.urls import reverse

from shop.models import Book, Sale, SaleItem

from .base import BaseShopTestCase
from .helpers import formset_data


class SaleWorkflowTests(BaseShopTestCase):

    def setUp(self):
        super().setUp()
        self.login()
        self.second_book = Book.objects.create(
            title="The Pragmatic Programmer", author="Andrew Hunt", isbn="9780135957059",
            category=self.category, price=Decimal("25000.00"), quantity=10,
        )

    def _post_sale(self, items):
        data = {"customer": self.customer.pk}
        data.update(formset_data(items))
        return self.client.post(reverse("sale_create"), data, follow=True)

    def test_valid_sale_is_recorded(self):
        response = self._post_sale([(self.book, 3)])
        self.assertEqual(Sale.objects.count(), 1)
        self.assertContains(response, "Sale recorded successfully.")

    def test_sale_reduces_stock_correctly(self):
        starting_qty = self.book.quantity
        self._post_sale([(self.book, 3)])
        self.book.refresh_from_db()
        self.assertEqual(self.book.quantity, starting_qty - 3)

    def test_sale_total_amount_is_calculated_correctly(self):
        self._post_sale([(self.book, 3), (self.second_book, 2)])
        sale = Sale.objects.latest("created_at")
        expected_total = (self.book.price * 3) + (self.second_book.price * 2)
        self.assertEqual(sale.total_amount, expected_total)

    def test_multiple_books_in_one_sale_create_separate_line_items(self):
        self._post_sale([(self.book, 1), (self.second_book, 4)])
        sale = Sale.objects.latest("created_at")
        self.assertEqual(sale.items.count(), 2)
        item_for_book = sale.items.get(book=self.book)
        item_for_second_book = sale.items.get(book=self.second_book)
        self.assertEqual(item_for_book.quantity, 1)
        self.assertEqual(item_for_book.unit_price, self.book.price)
        self.assertEqual(item_for_book.subtotal, self.book.price * 1)
        self.assertEqual(item_for_second_book.quantity, 4)
        self.assertEqual(item_for_second_book.subtotal, self.second_book.price * 4)

    def test_insufficient_stock_rejects_sale_and_leaves_stock_untouched(self):
        starting_qty = self.book.quantity  # 20
        response = self._post_sale([(self.book, starting_qty + 100)])
        self.assertContains(response, "Insufficient stock")
        self.assertEqual(Sale.objects.count(), 0)
        self.book.refresh_from_db()
        self.assertEqual(self.book.quantity, starting_qty)

    def test_zero_stock_book_cannot_be_sold(self):
        self.book.quantity = 0
        self.book.save()
        response = self._post_sale([(self.book, 1)])
        self.assertContains(response, "Insufficient stock")
        self.assertEqual(Sale.objects.count(), 0)

    def test_sale_does_not_leave_partial_records_on_failure(self):
        """If one line item in a multi-book sale is invalid, nothing should be saved."""
        response = self._post_sale([(self.book, 2), (self.second_book, 999)])
        self.assertContains(response, "Insufficient stock")
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(SaleItem.objects.count(), 0)
        self.book.refresh_from_db()
        self.second_book.refresh_from_db()
        self.assertEqual(self.book.quantity, 20)
        self.assertEqual(self.second_book.quantity, 10)

    def test_sale_with_no_books_is_rejected(self):
        data = {
            "customer": self.customer.pk,
            "items-TOTAL_FORMS": "1", "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1", "items-MAX_NUM_FORMS": "1000",
            "items-0-book": "", "items-0-quantity": "",
        }
        response = self.client.post(reverse("sale_create"), data, follow=True)
        self.assertEqual(Sale.objects.count(), 0)

    def test_sale_list_shows_recorded_sales(self):
        self._post_sale([(self.book, 1)])
        response = self.client.get(reverse("sale_list"))
        self.assertContains(response, self.customer.name)

    def test_sale_detail_shows_line_items(self):
        self._post_sale([(self.book, 2)])
        sale = Sale.objects.latest("created_at")
        response = self.client.get(reverse("sale_detail", args=[sale.pk]))
        self.assertContains(response, self.book.title)
        self.assertContains(response, "2")
