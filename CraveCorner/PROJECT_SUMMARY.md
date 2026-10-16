# CraveCorner — Project Summary

CraveCorner is a fictional restaurant-ordering web app and DSA mini-project. Customers browse a backend-loaded menu, save cart selections locally, submit an order, and track the stored status. Administrators sign in to a protected dashboard and process orders in FIFO order.

## Features and architecture

- Vanilla HTML/CSS/JavaScript client pages use Fetch API calls to Flask.
- Flask serves the customer/admin pages and JSON API; SQLite persists the menu, orders, receipt snapshots, and administrator account.
- Server-side checkout revalidates available menu items and prices, calculates totals in integer paise, and stores each order transactionally.
- The active queue is `collections.deque`: new orders append at the rear, and only the eligible front order may move from pending to preparing or preparing to completed. Completion pops the front order; completed history stays in SQLite.
- The queue lock protects each order-processing operation in this single application. Startup rebuilds the queue from incomplete database records in arrival order, preserving already-preparing orders.
- Admin sessions use Flask's signed session cookie, Werkzeug password hashes, CSRF tokens, and a basic per-IP/username login-attempt limit.

## Technologies

Python 3, Flask, Werkzeug, SQLite, `collections.deque`, HTML5, CSS3, and vanilla JavaScript.

## Run

Install `requirements.txt`, create the database with `python scripts/init_db.py`, create an admin with `python scripts/create_admin.py`, then run `python app.py`. See `README.md` for Windows setup.
