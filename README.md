# SEASIDE Online POS System

A comprehensive, web-based Point of Sale (POS) system built with Python and Flask. This system is designed to manage products, customers, sales transactions, and provide insightful reports for small to medium-sized businesses.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technologies Used](#technologies-used)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Overview

The SEASIDE Online POS System offers a user-friendly interface for daily sales operations and an administrative backend for system management and reporting. It aims to provide a lightweight yet effective solution for businesses looking to streamline their sales processes.

## Features

* **Dashboard:**
    * Quick overview of "Today's Total Sales".
    * Summary of "This Week - Mon to Sun" total sales.
* **Point of Sale (POS) Interface:**
    * Intuitive interface for adding products to a sale.
    * Option to add custom items/services with custom pricing (allows selecting an existing product to customize its price, or typing a completely new item name).
    * Ability to adjust item quantities (increase/decrease) in the current sale.
    * Remove items from the current sale.
    * Assign sales to existing customers or handle as walk-in ("N/A") transactions.
    * Finalize sales, which are then recorded in the sales history.
    * Option to clear the current sale.
* **Product Management:**
    * Add new products with names and prices.
    * Edit existing product details.
    * Delete products from the system.
    * View a paginated list of all available products.
* **Customer Management:**
    * Add new customers with details like name, contact information, and address.
    * Edit existing customer information.
    * Delete customers.
    * View a paginated list of all registered customers.
* **Sales History:**
    * View a paginated list of all completed sales transactions, ordered by date.
    * Access detailed views for each sale, showing items sold, quantities, prices at the time of sale, and total amount.
    * Ability to delete sales records (which also removes associated sale items).
* **Reporting:**
    * **Weekly Sales Report:** Visual bar chart displaying daily sales totals for the current week (Monday-Sunday). Includes a summary table of items sold during that week.
    * **Monthly Sales Report:** Visual bar chart displaying daily sales totals for a user-selected month and year. Includes a summary table of items sold during that month. Provides navigation to view previous/next months.
* **Admin Panel:**
    * **Database Backup:** Functionality to create a timestamped backup of the SQLite database.
    * **Database Restore:** Ability to restore the database from an uploaded `.db`, `.sqlite`, or `.sqlite3` file. (Note: This typically backs up the current database before restoring).
* **User Authentication:**
    * Simple password-based login to secure access to the application.
* **API Endpoints (Protected by API Key):**
    * `GET /api/products`: Retrieve a list of all products.
    * `GET /api/products/<name>`: Retrieve details for a specific product by its name.
    * `POST /api/sales`: Create/synchronize a new sale transaction via the API.
* **Responsive Design:** The user interface is designed to be functional across various screen sizes, including desktops, tablets, and mobile devices.

## Technologies Used

* **Backend:**
    * Python 3
    * Flask (Micro web framework)
    * SQLite (Relational database)
* **Frontend:**
    * HTML5
    * CSS3 (Custom styling, leveraging Flexbox and CSS Grid for layout)
    * JavaScript (Vanilla JS for client-side interactions, modal dialogs, navigation toggles, and dynamic content updates)
* **Charting:**
    * Chart.js (For rendering bar charts in sales reports)
* **Date/Time Utilities:**
    * Python `datetime` module
    * `python-dateutil` (specifically `relativedelta` for month navigation in reports)
* **Development Environment (Recommended):**
    * `venv` (Python's built-in virtual environment manager)

## Project Structure

your-repository-name/
├── app.py                 # Main Flask application file, contains routes and core logic
├── db_operations.py       # Module for all database interaction functions
├── pos_system.db          # SQLite database file (created on first run or by setup script)
├── static/
│   ├── css/
│   │   └── style.css      # Main stylesheet for the application
│   └── js/
│       └── script.js      # Main JavaScript file for client-side logic
├── templates/
│   ├── base.html          # Base HTML template inherited by other pages
│   ├── index.html         # Dashboard page
│   ├── login.html         # Login page
│   ├── reports.html       # Template for the Weekly Sales Report
│   ├── monthly_report.html # Template for the Monthly Sales Report
│   ├── admin/
│   │   ├── index.html     # Admin panel main page
│   │   └── restore_db.html # Database restore page
│   ├── products/
│   │   ├── list.html      # Page to list all products
│   │   └── add_edit.html  # Form to add or edit products
│   ├── customers/
│   │   ├── list.html      # Page to list all customers
│   │   └── add_edit.html  # Form to add or edit customers
│   ├── sales/
│   │   ├── list.html      # Page to list sales history
│   │   └── details.html   # Page to view details of a specific sale
│   └── pos/
│       └── interface.html   # POS interface page
├── README.md              # This file
└── requirements.txt       # (Recommended) File listing Python dependencies


## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/your-repository-name.git](https://github.com/your-username/your-repository-name.git)
    cd your-repository-name
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    # On Windows
    # .venv\Scripts\activate
    # On macOS/Linux
    # source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install Flask python-dateutil
    # If you create a requirements.txt file (recommended):
    # pip install -r requirements.txt
    ```
    To create `requirements.txt`, run `pip freeze > requirements.txt` in your activated virtual environment after installing packages.

4.  **Initialize the Database:**
    * The application is designed to create the `pos_system.db` file and its tables if they don't exist when `db_operations.py` functions are first called (specifically `get_db_connection` which then might be followed by table creation logic if you've added it, or your `database_setup.py` if you have one).
    * If you have a separate `database_setup.py` script, run it:
        ```bash
        python database_setup.py
        ```
    * Refer to `db_operations.py` for the table schemas.

5.  **Set Environment Variables (Important for Security):**
    * **`SECRET_KEY`**: A strong, random string used by Flask for session security.
        * Example (generate your own unique key): `export SECRET_KEY='a_very_secure_and_random_string_!@#$%'`
    * **`VALID_API_KEYS`**: A comma-separated list of API keys for accessing protected API endpoints.
        * Example: `export VALID_API_KEYS='your_first_api_key,another_secret_key'`
    * These can be set in your shell, in a `.env` file (if using a library like `python-dotenv`), or configured within your deployment environment.

6.  **Run the application:**
    ```bash
    flask run
    # Or, if your app.py has the `if __name__ == '__main__':` block:
    # python app.py
    ```
    The application should typically be accessible at `http://127.0.0.1:5000/`.

## Usage

1.  **Login:** Access the application via your browser. You will be prompted to log in. The default password is "password123" as defined in `app.py`.
    **IMPORTANT SECURITY NOTE:** This hardcoded password is for demonstration purposes only. For any real-world deployment, you **MUST** replace this with a secure user authentication system (e.g., hashed passwords, user accounts).
2.  **Navigate:** Use the navigation bar to access the various modules:
    * **Dashboard:** View summaries of today's and this week's sales.
    * **New Sale (POS):** Create new sales transactions.
    * **Manage Products:** Add, edit, or delete product listings.
    * **Manage Customers:** Add, edit, or delete customer records.
    * **Sales History:** Review past transactions and view sale details.
    * **Reports:** Access Weekly and Monthly sales reports with visual charts.
    * **Admin:** Perform administrative tasks like database backup and restore.
    * **Logout:** Securely end your session.

## API Endpoints

The following API endpoints are available and protected by an API key (sent via `X-API-KEY` header or `api_key` parameter/JSON field):

* `GET /api/products`: Retrieves a list of all products.
* `GET /api/products/<product_name>`: Retrieves details for a specific product by its name.
* `POST /api/sales`: Creates a new sale. Expects a JSON payload with `items` (list of products with name, quantity, price_at_sale) and optionally `customer_name`.

## Future Enhancements

* [ ] **Critical Security:** Implement a robust user authentication system (e.g., Flask-Login, Flask-Security) with hashed passwords, user roles (admin, staff), and registration.
* [ ] Inventory Management: Track stock levels, low stock alerts.
* [ ] Advanced Reporting: Custom date ranges, profit calculation, best-selling products, customer purchase history.
* [ ] User Management Interface: Allow admins to create and manage user accounts.
* [ ] UI/UX Improvements: Potentially integrate a modern CSS framework (like Bootstrap if not already fully utilized for all components) or refine the custom design for better aesthetics and usability.
* [ ] Testing: Implement unit and integration tests for backend logic and API endpoints.
* [ ] Payment Gateway Integration: Options for processing different payment methods.
* [ ] Receipt Generation: Ability to print or generate PDF receipts for sales.
* [ ] Enhanced Search & Filtering: For product lists, customer lists, and sales history.
* [ ] Configuration File: Move settings like `DATABASE_URL`, `ITEMS_PER_PAGE` to a configuration file or environment variables.

## Contributing

Contributions, issues, and feature requests are welcome! Please feel free to:
1.  Fork the repository.
2.  Create a new branch for your feature or fix (`git checkout -b feature/YourAmazingFeature` or `fix/BugFixDescription`).
3.  Make your changes and commit them (`git commit -m 'Add some amazing feature'`).
4.  Push to your branch (`git push origin feature/YourAmazingFeature`).
5.  Open a Pull Request.

Please ensure your code adheres to any existing style guidelines and includes relevant tests if applicable.

## License

This project is currently unlicensed. You may choose to add a license file (e.g., MIT, GPL) if you wish to define usage terms.

## Contact

Your Name / Project Alias - your.email@example.com
Project Link: [https://github.com/your-username/your-repository-name](https://github.com/your-username/your-repository-name)

---
_This README provides a general template. Please customize it further with specific details about your project's unique aspects and current status._
