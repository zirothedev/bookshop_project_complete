from django.urls import reverse

from shop.models import Category

from .base import BaseShopTestCase


class CategoryCrudTests(BaseShopTestCase):

    def setUp(self):
        super().setUp()
        self.login()

    def test_add_category_success(self):
        response = self.client.post(reverse("category_create"), {"name": "Fiction", "description": "Novels"})
        self.assertRedirects(response, reverse("category_list"))
        self.assertTrue(Category.objects.filter(name="Fiction").exists())

    def test_edit_category_success(self):
        response = self.client.post(reverse("category_edit", args=[self.category.pk]), {
            "name": "Software Engineering", "description": "Updated"
        })
        self.assertRedirects(response, reverse("category_list"))
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Software Engineering")

    def test_delete_unused_category_succeeds(self):
        empty_category = Category.objects.create(name="Unused Category")
        response = self.client.post(reverse("category_delete", args=[empty_category.pk]))
        self.assertRedirects(response, reverse("category_list"))
        self.assertFalse(Category.objects.filter(pk=empty_category.pk).exists())

    def test_delete_category_in_use_is_protected(self):
        # self.book already belongs to self.category (see base fixture)
        response = self.client.post(reverse("category_delete", args=[self.category.pk]), follow=True)
        self.assertContains(response, "cannot be deleted")
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
