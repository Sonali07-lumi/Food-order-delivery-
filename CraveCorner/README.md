# CraveCorner

**Good Food. Great Mood.**

CraveCorner is a fictional restaurant ordering website and college DSA mini-project. Customers browse a live menu, keep a cart between pages, place an order, and track its status. The kitchen dashboard processes orders in arrival order with a Python `collections.deque`.

## Problem statement

A restaurant needs to process incoming orders fairly. If a later order can jump ahead, the order flow is unpredictable. CraveCorner demonstrates a first-in, first-out (FIFO) queue and saves order history so the app can recover its active queue after a restart.

## Project objectives and features

- Responsive customer home, menu, cart, checkout, confirmation, tracking, and about pages.
- Searchable, filterable menu seeded with 21 sample dishes across seven categories.
- Browser-local cart persistence and live quantity/subtotal updates.
- Server-side validation and price calculation; no payment data is collected.
- SQLite order and item snapshots with integer paise amounts.
- Session-authenticated administrator login, hashed passwords, CSRF protection, and basic login-attempt limits.
- Live admin statistics, active queue, status actions, and completed-order history.
- Strict FIFO status changes enforced by the backend, not just by hidden buttons.
- Queue restoration from SQLite, preserving a front order that is already being prepared.
- Automated tests for queue behavior, order validation, persistence, authentication, and queue restoration.

## Technology stack

- Frontend: HTML5, CSS3, and vanilla JavaScript using the Fetch API.
- Backend: Python 3 and Flask REST-style routes.
- Data structures: `collections.deque` for active FIFO processing.
- Database: SQLite using bound parameters and transaction boundaries.
- Password hashing: Werkzeug's password hashing utilities.

## DSA concept: queue and FIFO

A queue processes the first item that arrived before later items. CraveCorner adds an order with `deque.append()`. The administrator can start or complete only the order at the front of the queue. After that front order is completed in a database transaction, the app removes it with `deque.popleft()`. The next order is then eligible.

The queue is held in memory while the app is running. On startup, CraveCorner reads all `PENDING` and `PREPARING` orders from SQLite in their original database sequence and rebuilds the deque. SQLite keeps completed orders and their receipt snapshots for history.

This is an educational single-application queue, not a distributed production queue. If multiple independent app servers share this database, use a dedicated transactional/distributed queue service instead.

## System architecture and workflow

```text
Browser (vanilla JS)
  ├── menu/cart/checkout/tracking
  └── authenticated admin dashboard
          │ Fetch API, session cookie, CSRF token
          ▼
Flask routes (/api/*)
  ├── server-side input and price validation
  ├── queue_manager.py (deque + process lock)
  └── database.py → SQLite
```

1. Menu entries are loaded from `GET /api/menu`.
2. The cart stays in browser `localStorage`; displayed browser prices are not trusted by the backend.
3. Checkout submits only menu IDs and quantities plus customer details.
4. Flask validates the request, reads current item prices from SQLite, computes the total in integer paise, saves the order and item snapshots, then appends the order number to the queue.
5. Customers can poll `GET /api/orders/<order_number>` to see the current saved status.
6. An authenticated administrator can process only the front order. Status changes are saved to SQLite and the in-memory queue while holding a lock.
7. On restart, the active queue is rebuilt in original arrival order.

## Database schema overview

- `menu_items`: available menu items, categories, image paths, vegetarian flag, and price in paise.
- `orders`: customer/order metadata, total in paise, status, and lifecycle timestamps.
- `order_items`: immutable item-name and price snapshots, quantities, and line totals.
- `admin_users`: unique username and Werkzeug password hash.

The order tables use foreign keys, checks, unique constraints, and indexes. Tracking responses omit customer phone and address; authenticated admin responses include them for kitchen management.

## Folder structure

```text
CraveCorner/
├── app.py
├── config.py
├── database.py
├── models.py
├── queue_manager.py
├── requirements.txt
├── .env.example
├── README.md
├── PROJECT_SUMMARY.md
├── test_report.md
├── templates/
│   ├── index.html
│   ├── menu.html
│   ├── cart.html
│   ├── checkout.html
│   ├── confirmation.html
│   ├── tracking.html
│   ├── about.html
│   ├── admin_login.html
│   └── admin.html
├── static/
│   ├── css/
│   ├── js/
│   └── images/README.md
├── scripts/
│   ├── init_db.py
│   └── create_admin.py
├── tests/
├── instance/.gitkeep
└── database/.gitkeep
```

## Windows installation and setup

Install Python 3.10 or newer and VS Code. Then open PowerShell in the extracted `CraveCorner` folder.

1. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

2. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again. Alternatively, use Command Prompt and run `.venv\Scripts\activate.bat`.

3. Install the dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Optionally copy the configuration template:

   ```powershell
   Copy-Item .env.example .env
   ```

   The app uses the `SESSION_SECRET` environment variable when present. For local development only, it creates a random, untracked key in `instance/local_secret_key` if no secret is configured. Never commit that file or use a development key for a public deployment.

5. Initialize the database and sample menu:

   ```powershell
   python scripts/init_db.py
   ```

6. Create an administrator account. The script prompts for a username and password (at least 12 characters); the password is hashed before it is saved:

   ```powershell
   python scripts/create_admin.py
   ```

7. Start the app:

   ```powershell
   python app.py
   ```

   Open `http://127.0.0.1:5000`. Admin sign-in is at `http://127.0.0.1:5000/admin/login`.

## Tests

From the project root, with the virtual environment activated:

```powershell
python -m unittest discover -s tests -v
```

The suite covers FIFO order, status transition rules, input validation, server-calculated totals, SQLite persistence, CSRF validation, admin authentication, completed history, and startup queue recovery. See `test_report.md` for the results executed for this package.

## Screenshots

Screenshots can be added here after running the app at desktop and mobile viewport widths.

To create a fresh, verified source archive after updating this project, run `python scripts/package_project.py --output CraveCorner.zip`.

## Menu images

The sample menu references public Unsplash image URLs and requires an internet connection to load the photographs. To use local or replacement licensed images, put them in `static/images/` and update `image_path` values in the seed data in `database.py`. Menu details live in one seed structure; they are not duplicated in frontend scripts.

## Known limitations

- The active queue is an in-memory `deque` for this educational single-application deployment. SQLite restores it on restart, but it is not a distributed queue for multiple worker processes.
- Menu photography is loaded from public image URLs; offline browsing still works apart from those images.
- The restaurant and all reviews/contact details are fictional sample content.
- No real payments, delivery integrations, or production-security certification are included.

## Future enhancements

- Replace the in-memory queue with a shared durable queue for multi-worker deployments.
- Add inventory/availability management and configurable delivery zones.
- Add order notifications and customer accounts.
- Bundle licensed photography locally and add image-management controls.

## Security notes

This is a classroom project, not a production security review. Admin passwords are hashed, browser mutations use session-bound CSRF tokens, API queries are parameterized, and checkout prices are authoritative on the server. Configure a strong secret and HTTPS before any public use.
