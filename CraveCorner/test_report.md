# CraveCorner Test Report

Verification record for the source project and its live Replit preview.

## Tests executed

- `python -m unittest discover -s tests -v` — **13 passed**.
- Python `py_compile` across the app, database, queue, and helper scripts — **passed**.
- `node --check` for all three browser JavaScript files — **passed**.
- Workspace `pnpm run typecheck` — **passed**.
- Live HTTP smoke checks — **passed**: home, menu, cart, checkout, tracking, about, and admin login returned HTTP 200; `/api/healthz` returned `{"status":"ok"}`; menu API returned 21 dishes across 7 categories; unauthenticated admin stats returned HTTP 401.
- Desktop (1440px) and narrow mobile (320px) preview screenshots reviewed.

## Results

### Customer ordering

- Menu, category/filter API integration, rupee prices, persistent cart UI, checkout, confirmation, and order tracking routes are present and served.
- Automated order tests verify persistence, server-calculated prices despite a submitted client total, rejection of empty/invalid orders and quantities, CSRF enforcement, and tracking privacy.
- Live route smoke checks confirm the customer pages load. Browser-driven checkout was not run.

### FIFO kitchen queue

- Orders are stored in SQLite and appended to a Python `collections.deque`.
- Automated tests verify arrival-order processing, later orders being blocked, invalid transitions being rejected, and pending/preparing orders being restored in arrival order after app recreation.
- Completed orders remain in history; duplicate completion and out-of-order completion are rejected.

### Admin dashboard and protection

- Dashboard API routes require an authenticated admin session. The UI exposes live queue/status actions, order details, refresh, completed-order history, and summary statistics.
- Automated tests verify protected access, valid/invalid login, the login-attempt limit, FIFO enforcement, and retained completed-order history.
- The protected admin stats endpoint returned HTTP 401 without a session.

### Package contents

- The ZIP packaging script checks required project files, ensures a single `CraveCorner/` root, and rejects generated databases, bytecode, local `.env` files, and runtime environments before reporting success.

## Verification limits

- Screenshot capture is a static visual check, not an interaction test; it cannot open navigation or submit forms.
- Menu item photos use remote Unsplash URLs and require an internet connection. The homepage hero image and favicon are bundled locally.
- The Flask development server is suitable for the local project and Replit preview. A production WSGI server should be used for a public deployment.
