from django.urls import reverse

from .base import BaseShopTestCase


class AuthenticationTests(BaseShopTestCase):

    def test_correct_login_redirects_to_dashboard(self):
        response = self.client.post(reverse("login"), {"username": "admin", "password": "admin12345"})
        self.assertRedirects(response, reverse("dashboard"))

    def test_incorrect_login_shows_error_and_does_not_authenticate(self):
        response = self.client.post(reverse("login"), {"username": "admin", "password": "wrongpassword"})
        self.assertEqual(response.status_code, 200)  # re-rendered, not redirected
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_ends_session(self):
        self.login()
        self.client.post(reverse("logout"))
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_unauthenticated_user_redirected_from_dashboard(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_unauthenticated_user_redirected_from_protected_pages(self):
        protected_urls = [
            reverse("book_list"), reverse("category_list"), reverse("customer_list"),
            reverse("sale_list"), reverse("inventory_overview"), reverse("sales_report"),
            reverse("settings_page"),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"{url} should redirect when logged out")
            self.assertIn(reverse("login"), response.url)

    def test_authenticated_user_can_access_dashboard(self):
        self.login()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
