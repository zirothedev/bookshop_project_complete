def formset_data(items):
    """Builds the management-form + item fields for the SaleItemFormSet."""
    data = {
        "items-TOTAL_FORMS": str(len(items)),
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "1",
        "items-MAX_NUM_FORMS": "1000",
    }
    for i, (book, qty) in enumerate(items):
        data[f"items-{i}-book"] = book.pk
        data[f"items-{i}-quantity"] = str(qty)
    return data
