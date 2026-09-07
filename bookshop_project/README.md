# Book Shop Management System (Django)

## Setup
1. `python -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`)
2. `pip install django`
3. `python manage.py migrate`
4. `python manage.py runserver`

The included `db.sqlite3` already has demo data loaded, so you can run the server
immediately after `migrate` and start browsing.

## Login
- Username: `admin`
- Password: `admin12345`

Change this before your defense/demo.

## Demo data
`python manage.py seed_demo_data` populates 7 categories, 20 real book titles, 15
Nigerian customers, and 10 sales created through the real Sale/SaleItem models (so
stock levels genuinely reflect what's been sold). Safe to re-run.

## Running the tests
```
python manage.py test shop
```
47 tests, all passing. Covers:
- **Authentication** — correct/incorrect login, logout, unauthorized-access redirects
  on every protected page
- **Books** — add/edit/delete, search, category filter, negative price/quantity
  rejection, invalid ISBN rejection, delete-protection when sales exist, stock-status
  threshold boundaries (in/low/out of stock)
- **Categories** — add/edit, delete-protection when books are assigned
- **Customers** — add/edit/delete, search, delete-protection when sales exist
- **Sales** — valid sale, multiple books in one sale, insufficient stock rejection,
  zero-stock rejection, correct total calculation, correct per-line unit price/subtotal,
  correct stock reduction, and (the important one) that a sale with one bad line item
  saves *nothing* rather than partially recording
- **Dashboard** — book count, total stock, and revenue update correctly as data changes;
  low-stock and recent-sale widgets show the right entries
- **Reports** — correct transaction count, correct total revenue, date-range filtering,
  correct inventory totals and stock value, correct low/out-of-stock lists

## What's built (Phases 1-9 - complete)
- **Phase 1** — Project setup, SQLite, Bootstrap 5 + custom design system matching
  the moodboard (`#0F766E` primary, Inter font, card/table/badge/button styles)
- **Phase 2** — Models: Category, Book, Customer, Sale, SaleItem, registered in Django Admin
- **Phase 3** — Core CRUD: Books, Categories, Customers (search, filters, validation,
  protected deletes)
- **Phase 4** — Sales: multi-book recording, server-side stock validation/recalculation,
  atomic stock reduction, sales history/detail
- **Phase 5** — Dashboard: live stat cards with genuine month-over-month growth,
  6-month revenue chart, top-selling books, recent sales, low-stock widget
- **Phase 6** — Inventory overview: stock-level summary cards, filterable table
- **Phase 7** — Reports: Sales Report and Inventory Report, both with real figures
- **Phase 8** — UI refinement: floating toast notifications (replacing inline alerts),
  loading/disabled state on form submit buttons, Table/Card view toggle on the Books
  page (using the book-card style from the moodboard), horizontally-scrollable tables
  on small screens
- **Phase 9** — Automated test suite (47 tests, see above)

## Known trade-offs worth knowing about
- Growth percentages on the dashboard only display once there's a prior-month baseline
  to compare against (a fresh install has none) — it shows a plain count instead of a
  fabricated percentage in that case. This is intentional, not a bug.
- Global topbar search (shown in the moodboard) wasn't built — the written spec only
  asked for page-level search on each list page, which is what's implemented. Flag if
  you want the omnisearch too; it's a bigger feature (cross-model search) than the
  rest of Phase 8 and wasn't in the original written requirements.
