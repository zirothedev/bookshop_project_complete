import json
from datetime import timedelta
from decimal import Decimal

from django.conf import settings as dj_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import DecimalField, ProtectedError, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BookForm, CategoryForm, CustomerForm, SaleForm, SaleItemFormSet
from .models import Book, Category, Customer, Sale, SaleItem


def _percent_change(current, previous):
    """Genuine month-over-month change, guarding against divide-by-zero."""
    if not previous:
        return None
    return round((float(current) - float(previous)) / float(previous) * 100, 1)


def _start_of_month(dt):
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def landing_page(request):
    """Public marketing page. Signed-in staff go straight to the dashboard."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    zero_money = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))
    context = {
        "total_books": Book.objects.count(),
        "total_customers": Customer.objects.count(),
        "total_sales": Sale.objects.count(),
        "total_stock": Book.objects.aggregate(total=Coalesce(Sum("quantity"), 0))["total"],
        "total_revenue": Sale.objects.aggregate(total=Coalesce(Sum("total_amount"), zero_money))["total"],
    }
    return render(request, "landing/index.html", context)


@login_required
def dashboard(request):
    now = timezone.now()
    this_month_start = _start_of_month(now)
    last_month_start = _start_of_month(this_month_start - timedelta(days=1))

    total_books = Book.objects.count()
    total_stock = Book.objects.aggregate(total=Coalesce(Sum("quantity"), 0))["total"]
    total_customers = Customer.objects.count()

    zero_money = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))
    total_revenue = Sale.objects.aggregate(total=Coalesce(Sum("total_amount"), zero_money))["total"]

    # Month-over-month comparisons, computed from real timestamps rather than hardcoded.
    books_before_this_month = Book.objects.filter(created_at__lt=this_month_start).count()
    customers_before_this_month = Customer.objects.filter(created_at__lt=this_month_start).count()
    revenue_this_month = Sale.objects.filter(created_at__gte=this_month_start).aggregate(
        total=Coalesce(Sum("total_amount"), zero_money))["total"]
    revenue_last_month = Sale.objects.filter(
        created_at__gte=last_month_start, created_at__lt=this_month_start
    ).aggregate(total=Coalesce(Sum("total_amount"), zero_money))["total"]

    books_growth = _percent_change(total_books, books_before_this_month)
    customers_growth = _percent_change(total_customers, customers_before_this_month)
    revenue_growth = _percent_change(revenue_this_month, revenue_last_month)

    low_stock_threshold = getattr(dj_settings, "LOW_STOCK_THRESHOLD", 5)
    low_stock_books = Book.objects.filter(quantity__lte=low_stock_threshold).order_by("quantity")[:6]

    recent_sales = Sale.objects.select_related("customer").order_by("-created_at")[:6]

    top_books = (
        SaleItem.objects.values("book__id", "book__title")
        .annotate(revenue=Sum("subtotal"))
        .order_by("-revenue")[:5]
    )

    # Monthly revenue for the last 6 months, for the sales-overview chart.
    six_months_ago = _start_of_month(now - timedelta(days=150))
    monthly = (
        Sale.objects.filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("total_amount"))
        .order_by("month")
    )
    monthly_map = {row["month"].strftime("%Y-%m"): float(row["total"]) for row in monthly}
    chart_labels, chart_values = [], []
    cursor = six_months_ago
    for _ in range(6):
        key = cursor.strftime("%Y-%m")
        chart_labels.append(cursor.strftime("%b"))
        chart_values.append(monthly_map.get(key, 0))
        # advance one month
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    context = {
        "active_nav": "dashboard",
        "total_books": total_books,
        "total_stock": total_stock,
        "total_customers": total_customers,
        "total_revenue": total_revenue,
        "books_growth": books_growth,
        "customers_growth": customers_growth,
        "revenue_growth": revenue_growth,
        "low_stock_books": low_stock_books,
        "recent_sales": recent_sales,
        "top_books": top_books,
        "chart_labels_json": json.dumps(chart_labels),
        "chart_values_json": json.dumps(chart_values),
    }
    return render(request, "dashboard/dashboard.html", context)


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

@login_required
def inventory_overview(request):
    low_stock_threshold = getattr(dj_settings, "LOW_STOCK_THRESHOLD", 5)
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    books = Book.objects.select_related("category").all()
    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))

    in_stock_count = books.filter(quantity__gt=low_stock_threshold).count()
    low_stock_count = books.filter(quantity__gt=0, quantity__lte=low_stock_threshold).count()
    out_of_stock_count = books.filter(quantity=0).count()

    if status == "in_stock":
        books = books.filter(quantity__gt=low_stock_threshold)
    elif status == "low_stock":
        books = books.filter(quantity__gt=0, quantity__lte=low_stock_threshold)
    elif status == "out_of_stock":
        books = books.filter(quantity=0)

    total_stock_value = books.aggregate(
        total=Coalesce(Sum("quantity"), 0)
    )["total"]

    return render(request, "inventory/overview.html", {
        "active_nav": "inventory",
        "books": books.order_by("quantity"),
        "query": query,
        "selected_status": status,
        "in_stock_count": in_stock_count,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "total_stock_value": total_stock_value,
        "low_stock_threshold": low_stock_threshold,
    })


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@login_required
def sales_report(request):
    zero_money = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))

    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()

    sales = Sale.objects.select_related("customer").all()
    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)
    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)

    sale_count = sales.count()
    total_revenue = sales.aggregate(total=Coalesce(Sum("total_amount"), zero_money))["total"]
    average_sale = (total_revenue / sale_count) if sale_count else Decimal("0.00")

    top_books = (
        SaleItem.objects.filter(sale__in=sales)
        .values("book__title")
        .annotate(qty_sold=Sum("quantity"), revenue=Sum("subtotal"))
        .order_by("-revenue")[:5]
    )

    recent_transactions = sales.order_by("-created_at")[:15]

    return render(request, "reports/sales_report.html", {
        "active_nav": "reports",
        "sale_count": sale_count,
        "total_revenue": total_revenue,
        "average_sale": average_sale,
        "top_books": top_books,
        "recent_transactions": recent_transactions,
        "date_from": date_from,
        "date_to": date_to,
    })


@login_required
def inventory_report(request):
    low_stock_threshold = getattr(dj_settings, "LOW_STOCK_THRESHOLD", 5)
    books = Book.objects.select_related("category").all()

    total_books = books.count()
    total_stock = books.aggregate(total=Coalesce(Sum("quantity"), 0))["total"]
    low_stock_books = books.filter(quantity__gt=0, quantity__lte=low_stock_threshold).order_by("quantity")
    out_of_stock_books = books.filter(quantity=0)

    # Total stock value = sum(price * quantity), computed in Python for clarity.
    stock_value = sum((b.price * b.quantity for b in books), Decimal("0.00"))

    return render(request, "reports/inventory_report.html", {
        "active_nav": "reports",
        "total_books": total_books,
        "total_stock": total_stock,
        "low_stock_books": low_stock_books,
        "out_of_stock_books": out_of_stock_books,
        "stock_value": stock_value,
        "low_stock_threshold": low_stock_threshold,
    })


@login_required
def settings_page(request):
    return render(request, "settings/settings.html", {"active_nav": "settings"})


# ---------------------------------------------------------------------------
# Category CRUD
# ---------------------------------------------------------------------------

@login_required
def category_list(request):
    query = request.GET.get("q", "").strip()
    categories = Category.objects.all()
    if query:
        categories = categories.filter(name__icontains=query)
    return render(request, "categories/category_list.html", {
        "active_nav": "categories",
        "categories": categories,
        "query": query,
    })


@login_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully.")
            return redirect("category_list")
    else:
        form = CategoryForm()
    return render(request, "categories/category_form.html", {
        "active_nav": "categories", "form": form, "is_edit": False,
    })


@login_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect("category_list")
    else:
        form = CategoryForm(instance=category)
    return render(request, "categories/category_form.html", {
        "active_nav": "categories", "form": form, "is_edit": True, "category": category,
    })


@login_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    try:
        category.delete()
        messages.success(request, "Category deleted successfully.")
    except ProtectedError:
        messages.error(
            request,
            f"Category '{category.name}' cannot be deleted because it is being used by one or more books.",
        )
    return redirect("category_list")


# ---------------------------------------------------------------------------
# Book CRUD
# ---------------------------------------------------------------------------

@login_required
def book_list(request):
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    status = request.GET.get("status", "").strip()

    books = Book.objects.select_related("category").all()
    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query) | Q(isbn__icontains=query))
    if category_id:
        books = books.filter(category_id=category_id)

    if status:
        matching_ids = [b.pk for b in books if b.stock_status == status]
        books = books.filter(pk__in=matching_ids)

    return render(request, "books/book_list.html", {
        "active_nav": "books",
        "books": books,
        "categories": Category.objects.all(),
        "query": query,
        "selected_category": category_id,
        "selected_status": status,
    })


@login_required
def book_detail(request, pk):
    book = get_object_or_404(Book.objects.select_related("category"), pk=pk)
    return render(request, "books/book_detail.html", {"active_nav": "books", "book": book})


@login_required
def book_create(request):
    if request.method == "POST":
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Book added successfully.")
            return redirect("book_list")
    else:
        form = BookForm()
    return render(request, "books/book_form.html", {
        "active_nav": "books", "form": form, "is_edit": False,
    })


@login_required
def book_edit(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, "Book updated successfully.")
            return redirect("book_detail", pk=book.pk)
    else:
        form = BookForm(instance=book)
    return render(request, "books/book_form.html", {
        "active_nav": "books", "form": form, "is_edit": True, "book": book,
    })


@login_required
@require_POST
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    try:
        title = book.title
        book.delete()
        messages.success(request, f"'{title}' deleted successfully.")
    except ProtectedError:
        messages.error(request, f"'{book.title}' cannot be deleted because it has sales recorded against it.")
    return redirect("book_list")


# ---------------------------------------------------------------------------
# Customer CRUD
# ---------------------------------------------------------------------------

@login_required
def customer_list(request):
    query = request.GET.get("q", "").strip()
    customers = Customer.objects.all()
    if query:
        customers = customers.filter(Q(name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query))
    return render(request, "customers/customer_list.html", {
        "active_nav": "customers", "customers": customers, "query": query,
    })


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    sales = customer.sales.all()
    return render(request, "customers/customer_detail.html", {
        "active_nav": "customers", "customer": customer, "sales": sales,
    })


@login_required
def customer_create(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer added successfully.")
            return redirect("customer_list")
    else:
        form = CustomerForm()
    return render(request, "customers/customer_form.html", {
        "active_nav": "customers", "form": form, "is_edit": False,
    })


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer updated successfully.")
            return redirect("customer_detail", pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    return render(request, "customers/customer_form.html", {
        "active_nav": "customers", "form": form, "is_edit": True, "customer": customer,
    })


@login_required
@require_POST
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    try:
        name = customer.name
        customer.delete()
        messages.success(request, f"'{name}' deleted successfully.")
    except ProtectedError:
        messages.error(request, f"'{customer.name}' cannot be deleted because they have sales recorded.")
    return redirect("customer_list")


# ---------------------------------------------------------------------------
# Sales — the core business workflow
# ---------------------------------------------------------------------------

@login_required
def sale_list(request):
    sales = Sale.objects.select_related("customer").all()
    query = request.GET.get("q", "").strip()
    if query:
        sales = sales.filter(customer__name__icontains=query)
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()
    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)
    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)
    return render(request, "sales/sale_list.html", {
        "active_nav": "sales", "sales": sales, "query": query,
        "date_from": date_from, "date_to": date_to,
    })


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("customer", "created_by").prefetch_related("items__book"), pk=pk)
    return render(request, "sales/sale_detail.html", {"active_nav": "sales", "sale": sale})


@login_required
def sale_create(request):
    """
    Record a new sale.

    Business rule: stock is validated and reduced on the server, inside a
    single database transaction, so a failed sale never leaves stock
    partially reduced or a sale recorded without matching stock movement.
    """
    if request.method == "POST":
        sale_form = SaleForm(request.POST)
        formset = SaleItemFormSet(request.POST, instance=Sale())

        if sale_form.is_valid() and formset.is_valid():
            # Re-check stock across all submitted lines together, in case the
            # same book appears more than once in the same sale.
            requested_totals = {}
            has_items = False
            for form in formset:
                if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                    continue
                book = form.cleaned_data.get("book")
                quantity = form.cleaned_data.get("quantity")
                if not book or not quantity:
                    continue
                has_items = True
                requested_totals[book.pk] = requested_totals.get(book.pk, 0) + quantity

            insufficient = []
            for book_id, requested_qty in requested_totals.items():
                book = Book.objects.get(pk=book_id)
                if requested_qty > book.quantity:
                    insufficient.append(f"{book.title} (only {book.quantity} available, {requested_qty} requested)")

            if not has_items:
                messages.error(request, "Add at least one book to the sale.")
            elif insufficient:
                messages.error(request, "Insufficient stock: " + "; ".join(insufficient))
            else:
                with transaction.atomic():
                    sale = sale_form.save(commit=False)
                    sale.created_by = request.user
                    sale.total_amount = 0
                    sale.save()

                    total = 0
                    for form in formset:
                        if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                            continue
                        book = form.cleaned_data.get("book")
                        quantity = form.cleaned_data.get("quantity")
                        if not book or not quantity:
                            continue
                        unit_price = book.price
                        subtotal = unit_price * quantity
                        total += subtotal

                        item = form.save(commit=False)
                        item.sale = sale
                        item.unit_price = unit_price
                        item.subtotal = subtotal
                        item.save()

                        # Atomic, race-safe stock reduction.
                        Book.objects.filter(pk=book.pk).update(quantity=book.quantity - quantity)

                    sale.total_amount = total
                    sale.save(update_fields=["total_amount"])

                messages.success(request, "Sale recorded successfully.")
                return redirect("sale_detail", pk=sale.pk)
    else:
        sale_form = SaleForm()
        formset = SaleItemFormSet(instance=Sale())

    return render(request, "sales/sale_form.html", {
        "active_nav": "sales",
        "sale_form": sale_form,
        "formset": formset,
    })
