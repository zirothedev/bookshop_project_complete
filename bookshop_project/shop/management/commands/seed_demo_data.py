"""
Populates the database with realistic demo data for project defense/demo purposes.

Usage:
    python manage.py seed_demo_data

Safe to run multiple times:
- Categories and Books are matched on unique fields (name / isbn), so re-running
  never creates duplicates and will pick up edits made to this file (e.g. a
  changed price) without erroring.
- Customers are matched on email.
- The 10 demo sales are only created once: if the first seed customer already
  has sales recorded, the sales step is skipped so re-running the command
  doesn't keep adding more transactions and further draining stock.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import Book, Category, Customer, Sale, SaleItem

CATEGORIES = [
    ("African Literature", "Fiction and literary works by African authors"),
    ("Fiction", "General and contemporary fiction"),
    ("Programming", "Software development and computer science"),
    ("Business", "Business, finance and entrepreneurship"),
    ("Self-Help", "Personal development and productivity"),
    ("Poetry", "Poetry collections"),
    ("History", "History, memoir and non-fiction"),
]

# (title, author, isbn, category, price_naira, quantity)
BOOKS = [
    ("Things Fall Apart", "Chinua Achebe", "9780385474542", "African Literature", Decimal("4500.00"), 3),
    ("Half of a Yellow Sun", "Chimamanda Ngozi Adichie", "9780007200283", "African Literature", Decimal("8500.00"), 40),
    ("Purple Hibiscus", "Chimamanda Ngozi Adichie", "9781616202415", "African Literature", Decimal("7000.00"), 25),
    ("Americanah", "Chimamanda Ngozi Adichie", "9780307455925", "Fiction", Decimal("9500.00"), 18),
    ("The Fishermen", "Chigozie Obioma", "9781627794465", "African Literature", Decimal("7800.00"), 4),
    ("My Life in the Bush of Ghosts", "Amos Tutuola", "9780571230115", "African Literature", Decimal("6200.00"), 12),
    ("The Joys of Motherhood", "Buchi Emecheta", "9780435905951", "Fiction", Decimal("6800.00"), 30),
    ("Efuru", "Flora Nwapa", "9780435900141", "African Literature", Decimal("5900.00"), 20),
    ("A Man of the People", "Chinua Achebe", "9780385086161", "African Literature", Decimal("5200.00"), 15),
    ("Sozaboy", "Ken Saro-Wiwa", "9780582266109", "Fiction", Decimal("6000.00"), 22),
    ("There Was a Country", "Chinua Achebe", "9780143124030", "History", Decimal("8900.00"), 10),
    ("Song of Lawino", "Okot p'Bitek", "9780435900110", "Poetry", Decimal("4800.00"), 8),
    ("Clean Code", "Robert C. Martin", "9780132350884", "Programming", Decimal("2000.00"), 45),
    ("The Pragmatic Programmer", "Andrew Hunt", "9780135957059", "Programming", Decimal("2500.00"), 3),
    ("Introduction to Algorithms", "Thomas H. Cormen", "9780262033848", "Programming", Decimal("3000.00"), 20),
    ("Design Patterns", "Erich Gamma", "9780201633610", "Programming", Decimal("2200.00"), 15),
    ("Python Crash Course", "Eric Matthes", "9781593279288", "Programming", Decimal("8000.00"), 50),
    ("Rich Dad Poor Dad", "Robert Kiyosaki", "9781612680194", "Business", Decimal("6500.00"), 35),
    ("Think and Grow Rich", "Napoleon Hill", "9781585424337", "Business", Decimal("5800.00"), 28),
    ("Atomic Habits", "James Clear", "9780735211292", "Self-Help", Decimal("5000.00"), 60),
]

# (name, phone, email)
CUSTOMERS = [
    ("Adaeze Okafor", "08012345601", "adaeze.okafor@example.com"),
    ("Chinedu Eze", "08023456702", "chinedu.eze@example.com"),
    ("Ngozi Balogun", "07034567803", "ngozi.balogun@example.com"),
    ("Emeka Nwosu", "09045678904", "emeka.nwosu@example.com"),
    ("Fatima Abdullahi", "08056789005", "fatima.abdullahi@example.com"),
    ("Ibrahim Musa", "08167890106", "ibrahim.musa@example.com"),
    ("Blessing Uche", "07078901207", "blessing.uche@example.com"),
    ("Tunde Bakare", "09089012308", "tunde.bakare@example.com"),
    ("Amaka Chukwu", "08190123409", "amaka.chukwu@example.com"),
    ("Yusuf Aliyu", "08101234510", "yusuf.aliyu@example.com"),
    ("Chioma Nnamdi", "07012345611", "chioma.nnamdi@example.com"),
    ("Segun Adeyemi", "09023456712", "segun.adeyemi@example.com"),
    ("Aisha Bello", "08134567813", "aisha.bello@example.com"),
    ("Obinna Okoro", "08145678914", "obinna.okoro@example.com"),
    ("Folake Adebayo", "07056789015", "folake.adebayo@example.com"),
]

# (customer_index, [(book_title, quantity), ...])
SALES = [
    (0, [("Clean Code", 2), ("Python Crash Course", 1)]),
    (1, [("Things Fall Apart", 3)]),
    (2, [("Half of a Yellow Sun", 3), ("Purple Hibiscus", 1)]),
    (3, [("The Fishermen", 3)]),
    (4, [("Atomic Habits", 2), ("Rich Dad Poor Dad", 1)]),
    (5, [("The Pragmatic Programmer", 2)]),
    (6, [("Design Patterns", 1), ("Introduction to Algorithms", 2)]),
    (7, [("Sozaboy", 2), ("There Was a Country", 1)]),
    (8, [("Efuru", 3), ("A Man of the People", 2)]),
    (9, [("Song of Lawino", 2), ("My Life in the Bush of Ghosts", 1)]),
]


def cover_url(isbn):
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"


class Command(BaseCommand):
    help = "Seed the database with realistic demo data (categories, books, customers, sales)."

    def handle(self, *args, **options):
        with transaction.atomic():
            categories = self._seed_categories()
            books = self._seed_books(categories)
            customers = self._seed_customers()
            self._seed_sales(customers, books)

        self.stdout.write(self.style.SUCCESS(
            f"Done. {Category.objects.count()} categories, {Book.objects.count()} books, "
            f"{Customer.objects.count()} customers, {Sale.objects.count()} sales in the database."
        ))

    def _seed_categories(self):
        categories = {}
        for name, description in CATEGORIES:
            category, created = Category.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            categories[name] = category
            self.stdout.write(f"  {'created' if created else 'exists '} category: {name}")
        return categories

    def _seed_books(self, categories):
        books = {}
        for title, author, isbn, category_name, price, quantity in BOOKS:
            book, created = Book.objects.get_or_create(
                isbn=isbn,
                defaults={
                    "title": title,
                    "author": author,
                    "category": categories[category_name],
                    "price": price,
                    "quantity": quantity,
                    "cover_image_url": cover_url(isbn),
                },
            )
            books[title] = book
            self.stdout.write(f"  {'created' if created else 'exists '} book: {title}")
        return books

    def _seed_customers(self):
        customers = []
        for name, phone, email in CUSTOMERS:
            customer, created = Customer.objects.get_or_create(
                email=email, defaults={"name": name, "phone": phone}
            )
            customers.append(customer)
            self.stdout.write(f"  {'created' if created else 'exists '} customer: {name}")
        return customers

    def _seed_sales(self, customers, books):
        # Idempotency guard: if the first seed customer already has a sale,
        # assume this command has already seeded sales and skip, so
        # re-running the command doesn't keep draining stock further.
        if customers and customers[0].sales.exists():
            self.stdout.write(self.style.WARNING(
                "  Sales already seeded for this customer set - skipping sale creation."
            ))
            return

        demo_user = User.objects.filter(is_superuser=True).first()

        for customer_index, items in SALES:
            customer = customers[customer_index]

            # Verify stock is sufficient before creating anything, exactly
            # like the real "Record Sale" view does.
            insufficient = []
            for title, qty in items:
                book = books[title]
                if qty > book.quantity:
                    insufficient.append(title)
            if insufficient:
                self.stdout.write(self.style.WARNING(
                    f"  Skipped a sale for {customer.name} - insufficient stock for: {', '.join(insufficient)}"
                ))
                continue

            sale = Sale.objects.create(customer=customer, total_amount=0, created_by=demo_user)
            total = Decimal("0.00")
            for title, qty in items:
                book = books[title]
                unit_price = book.price
                subtotal = unit_price * qty
                SaleItem.objects.create(
                    sale=sale, book=book, quantity=qty, unit_price=unit_price, subtotal=subtotal
                )
                Book.objects.filter(pk=book.pk).update(quantity=book.quantity - qty)
                book.quantity -= qty  # keep in-memory object in sync for subsequent checks
                total += subtotal

            sale.total_amount = total
            sale.save(update_fields=["total_amount"])
            self.stdout.write(f"  created sale #{sale.pk} for {customer.name}: N{total:,.2f}")
