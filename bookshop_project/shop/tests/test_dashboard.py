from decimal import Decimal

from django.urls import reverse

from shop.models import Book

from .base import BaseShopTestCase
from .helpers import formset_data


class DashboardStatsTests(BaseShopTestCase):

    def setUp(self):
        super().setUp()
        self.login()

    def test_dashboard_reflects_current_book_count(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, ">1<")  # one book from the base fixture

        Book.objects.create(
            title="Design Patterns", author="Erich Gamma", isbn="9780201633610",
            category=self.category, price=Decimal("22000.00"), quantity=5,
        )
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, ">2<")

    def test_dashboard_total_stock_matches_sum_of_quantities(self):
        Book.objects.create(
            title="Design Patterns", author="Erich Gamma", isbn="9780201633610",
            category=self.category, price=Decimal("22000.00"), quantity=5,
        )
        # base fixture book has quantity=20, new book has quantity=5 -> total 25
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, ">25<")

    def test_dashboard_revenue_updates_after_recording_a_sale(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "\u20a60")  # ₦0 revenue initially

        data = {"customer": self.customer.pk}
        data.update(formset_data([(self.book, 2)]))
        self.client.post(reverse("sale_create"), data)

        response = self.client.get(reverse("dashboard"))
        expected_revenue = self.book.price * 2
        self.assertContains(response, f"\u20a6{expected_revenue:.0f}")

    def test_dashboard_shows_low_stock_book(self):
        from django.conf import settings
        self.book.quantity = settings.LOW_STOCK_THRESHOLD
        self.book.save()
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, self.book.title)

    def test_dashboard_shows_recent_sale(self):
        data = {"customer": self.customer.pk}
        data.update(formset_data([(self.book, 1)]))
        self.client.post(reverse("sale_create"), data)

        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, self.customer.name)
