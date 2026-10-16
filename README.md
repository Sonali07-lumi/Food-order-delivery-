# 🍔 CraveCorner — Good Food. Great Mood.

**CraveCorner** is a full-stack food ordering web application designed to provide customers with a smooth ordering experience and administrators with an organized order management system.

The project combines a responsive frontend, a Flask backend, an SQLite database, and FIFO (First In, First Out) queue management.

## ✨ Features

### 🛒 Customer Features

* Browse an interactive food menu.
* Search and filter menu items.
* Add items to a shopping cart.
* Review cart items and quantities.
* Place orders through checkout.
* Track order status.
* Enjoy a responsive interface across desktop and mobile devices.

### 🔐 Admin Dashboard

* Access the admin login page.
* View and manage customer orders.
* Organize orders using FIFO queue management.
* Update order statuses:

  * Pending
  * Preparing
  * Completed
* Retain completed orders in order history.

### ⚙️ Backend and Database

* Flask-powered backend.
* SQLite database for persistent data storage.
* Server-side price calculations.
* Order and order-item storage.
* Queue restoration after application restarts.
* Checkout duplicate-submission protection.

### 🎨 UI and Design

* Deep burgundy, warm cream, and champagne gold theme.
* Responsive layouts.
* Interactive shopping cart.
* Clean, modern restaurant-inspired design.

## 🛠️ Tech Stack

| Technology          | Purpose                       |
| ------------------- | ----------------------------- |
| Python              | Backend programming           |
| Flask               | Web framework                 |
| SQLite              | Database                      |
| HTML5               | Website structure             |
| CSS3                | Styling and responsive design |
| JavaScript          | Frontend interactions         |
| `collections.deque` | FIFO queue management         |
| pytest              | Automated testing             |

## 📂 Project Structure

```text
CraveCorner/
├── app.py
├── database.py
├── queue_manager.py
├── requirements.txt
├── README.md
├── PROJECT_SUMMARY.md
├── TEST_REPORT.md
├── .env.example
├── templates/
├── static/
│   ├── css/
│   └── js/
├── scripts/
└── tests/
```

## 🚀 Installation and Setup

### Prerequisites

Install Python 3.10 or a compatible version supported by the project dependencies.

### 1. Download the Project

Download or clone the repository and open its folder in your terminal.

### 2. Create a Virtual Environment

**Windows:**

```bash
py -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Initialize the Database

```bash
python scripts/init_db.py
```

### 5. Create an Admin Account

```bash
python scripts/create_admin.py
```

Follow the prompts to configure the administrator account.

### 6. Start the Application

```bash
python app.py
```

Open the local address below in your browser:

```text
http://127.0.0.1:5000
```

The administrator login page is available at:

```text
http://127.0.0.1:5000/admin/login
```

## 🧪 Running Tests

Run the project's automated tests with:

```bash
python -m pytest -q
```

Review `TEST_REPORT.md` for the verification status and any testing limitations.

**Note:** The project package was checked for Python syntax and ZIP integrity, but automated tests and browser-based testing have not yet been confirmed successful in the development environment. Run the tests locally before relying on the application in production.

## 🔄 Order Workflow

1. The customer browses the menu.
2. The customer adds items to the cart.
3. The customer checks out and places an order.
4. The order is saved in the SQLite database.
5. The order enters the FIFO queue.
6. The administrator updates its status.
7. Completed orders remain available in the order history.

## 🎯 Project Objectives

* Demonstrate full-stack web development.
* Implement persistent data storage with SQLite.
* Apply FIFO queue concepts to order management.
* Build a responsive and user-friendly interface.
* Practice backend development, database integration, and frontend interaction.

## 🔮 Future Improvements

* Online payment integration.
* Customer registration and login.
* Menu and inventory management.
* Order notifications.
* Sales analytics and reporting.
* Deployment to a cloud hosting platform.

## 👩‍💻 Author

Developed as a full-stack web development project.

## 📄 License

This project is intended for educational and demonstration purposes. Add a license file if you plan to distribute it under a specific open-source license.
