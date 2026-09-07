from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from .models import Book, Category, Customer, Sale, SaleItem


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Fiction"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional description"}),
        }


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title", "author", "isbn", "category", "price", "quantity", "description", "cover_image_url"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter book title"}),
            "author": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter author name"}),
            "isbn": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 9780132350884"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Enter price", "step": "0.01", "min": "0"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Enter stock quantity", "min": "0"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional description"}),
            "cover_image_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://... (optional cover image URL)"}),
        }

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price is not None and price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity is not None and quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return quantity


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "email"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter customer name"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter phone number"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter email address"}),
        }


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ["customer"]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-select"}),
        }


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ["book", "quantity"]
        widgets = {
            "book": forms.Select(attrs={"class": "form-select sale-book-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control sale-qty-input", "min": "1", "value": "1"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        book = cleaned_data.get("book")
        quantity = cleaned_data.get("quantity")
        if book and quantity:
            if quantity > book.quantity:
                raise forms.ValidationError(
                    f"Insufficient stock for '{book.title}'. Only {book.quantity} copies are available."
                )
        return cleaned_data


SaleItemFormSet = inlineformset_factory(
    Sale,
    SaleItem,
    form=SaleItemForm,
    fields=["book", "quantity"],
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
