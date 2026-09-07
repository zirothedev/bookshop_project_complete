from decimal import Decimal

from django.urls import reverse

from shop.models import Book

from .base import BaseShopTestCase


class BookCrudTests(BaseShopTestCase):

    def setUp(self):
        super().setUp()
        self.login()

    def test_add_book_success(self):
        response = self.client.post(reverse("book_create"), {
            "title": "The Pragmatic Programmer",
            "author": "Andrew Hunt",
            "isbn": "9780135957059",
            "category": self.category.pk,
            "price": "25000.00",
            "quantity": "10",
            "description": "",
            "cover_image_url": "",
        })
        self.assertRedirects(response, reverse("book_list"))
        self.assertTrue(Book.objects.filter(isbn="9780135957059").exists())

    def test_edit_book_success(self):
        response = self.client.post(reverse("book_edit", args=[self.book.pk]), {
            "title": "Clean Code (2nd Print)",
            "author": self.book.author,
            "isbn": self.book.isbn,
            "category": self.category.pk,
            "price": "21000.00",
            "quantity": "18",
            "description": "",
            "cover_image_url": "",
        })
        self.assertRedirects(response, reverse("book_detail", args=[self.book.pk]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "Clean Code (2nd Print)")
        self.assertEqual(self.book.price, Decimal("21000.00"))
        self.assertEqual(self.book.quantity, 18)

    def test_delete_book_success(self):
        response = self.client.post(reverse("book_delete", args=[self.book.pk]))
        self.assertRedirects(response, reverse("book_list"))
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())

    def test_delete_book_with_sales_is_protected(self):
        from shop.models import Sale, SaleItem
        sale = Sale.objects.create(customer=self.customer, total_amount=self.book.price)
        SaleItem.objects.create(sale=sale, book=self.book, quantity=1, unit_price=self.book.price, subtotal=self.book.price)

        response = self.client.post(reverse("book_delete", args=[self.book.pk]), follow=True)
        self.assertContains(response, "cannot be deleted")
        self.assertTrue(Book.objects.filter(pk=self.book.pk).exists())

    def test_search_books_by_title(self):
        Book.objects.create(
            title="Design Patterns", author="Erich Gamma", isbn="9780201633610",
            category=self.category, price=Decimal("22000.00"), quantity=5,
        )
        response = self.client.get(reverse("book_list"), {"q": "Clean"})
        self.assertContains(response, "Clean Code")
        self.assertNotContains(response, "Design Patterns")

    def test_filter_books_by_category(self):
        other_category = self.category.__class__.objects.create(name="Fiction")
        Book.objects.create(
            title="Americanah", author="Chimamanda Ngozi Adichie", isbn="9780307455925",
            category=other_category, price=Decimal("9500.00"), quantity=5,
        )
        response = self.client.get(reverse("book_list"), {"category": self.category.pk})
        self.assertContains(response, "Clean Code")
        self.assertNotContains(response, "Americanah")

    def test_negative_price_rejected(self):
        response = self.client.post(reverse("book_create"), {
            "title": "Bad Book", "author": "X", "isbn": "1234567890",
            "category": self.category.pk, "price": "-500.00", "quantity": "5",
            "description": "", "cover_image_url": "",
        })
        self.assertEqual(response.status_code, 200)  # form re-rendered with errors
        self.assertFalse(Book.objects.filter(isbn="1234567890").exists())

    def test_negative_quantity_rejected(self):
        response = self.client.post(reverse("book_create"), {
            "title": "Bad Book", "author": "X", "isbn": "1234567891",
            "category": self.category.pk, "price": "500.00", "quantity": "-5",
            "description": "", "cover_image_url": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Book.objects.filter(isbn="1234567891").exists())

    def test_invalid_isbn_rejected(self):
        response = self.client.post(reverse("book_create"), {
            "title": "Bad ISBN Book", "author": "X", "isbn": "12345",
            "category": self.category.pk, "price": "500.00", "quantity": "5",
            "description": "", "cover_image_url": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "valid 10 or 13 digit ISBN")
        self.assertFalse(Book.objects.filter(title="Bad ISBN Book").exists())

    def test_stock_status_thresholds(self):
        from django.conf import settings
        threshold = settings.LOW_STOCK_THRESHOLD

        self.book.quantity = threshold + 10
        self.book.save()
        self.assertEqual(self.book.stock_status, "in_stock")

        self.book.quantity = threshold
        self.book.save()
        self.assertEqual(self.book.stock_status, "low_stock")

        self.book.quantity = 0
        self.book.save()
        self.assertEqual(self.book.stock_status, "out_of_stock")
