from django.urls import reverse

from shop.models import Customer

from .base import BaseShopTestCase


class CustomerCrudTests(BaseShopTestCase):

    def setUp(self):
        super().setUp()
        self.login()

    def test_add_customer_success(self):
        response = self.client.post(reverse("customer_create"), {
            "name": "Jane Smith", "phone": "08098765432", "email": "jane@example.com",
        })
        self.assertRedirects(response, reverse("customer_list"))
        self.assertTrue(Customer.objects.filter(email="jane@example.com").exists())

    def test_edit_customer_success(self):
        response = self.client.post(reverse("customer_edit", args=[self.customer.pk]), {
            "name": "John Doe Jr.", "phone": self.customer.phone, "email": self.customer.email,
        })
        self.assertRedirects(response, reverse("customer_detail", args=[self.customer.pk]))
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "John Doe Jr.")

    def test_delete_customer_success(self):
        response = self.client.post(reverse("customer_delete", args=[self.customer.pk]))
        self.assertRedirects(response, reverse("customer_list"))
        self.assertFalse(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_delete_customer_with_sales_is_protected(self):
        from shop.models import Sale
        Sale.objects.create(customer=self.customer, total_amount=1000)
        response = self.client.post(reverse("customer_delete", args=[self.customer.pk]), follow=True)
        self.assertContains(response, "cannot be deleted")
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_search_customers(self):
        Customer.objects.create(name="Amaka Chukwu", phone="08011112222", email="amaka@example.com")
        response = self.client.get(reverse("customer_list"), {"q": "John"})
        self.assertContains(response, "John Doe")
        self.assertNotContains(response, "Amaka Chukwu")
