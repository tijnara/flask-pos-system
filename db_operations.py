# db_operations.py
# Description: This file contains functions to interact with the SQLite database.
import sqlite3
import logging  # Import the logging module
import datetime  # Import datetime to get current timestamp

# Configure basic logging
# This will log messages to the console. You might want to configure file logging for production.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_URL = "pos_system.db"  # Name of your database file


def get_db_connection():
    """Establishes a connection to the SQLite database specified by DATABASE_URL."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_URL)
        # Set row_factory to sqlite3.Row to access columns by name
        conn.row_factory = sqlite3.Row
        # Enable foreign key support (good practice for SQLite)
        conn.execute("PRAGMA foreign_keys = ON;")
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}", exc_info=True)
        raise  # Re-raise the exception if connection fails
    return conn


# --- Product Operations ---

def add_product_db(name, price):
    """Adds a new product to the database.

    Args:
        name (str): The name of the product.
        price (float): The price of the product.

    Returns:
        int or None: The ID of the newly inserted product, or None if an error occurred.
    """
    sql = "INSERT INTO Products (ProductName, Price) VALUES (?, ?)"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (name, price))
        conn.commit()
        product_id = cursor.lastrowid
        logging.info(f"Added product '{name}' with ID: {product_id}")
        return product_id
    except sqlite3.IntegrityError:
        # Handles UNIQUE constraint violation for ProductName
        logging.warning(f"Failed to add product '{name}'. It might already exist.")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_product_db for product '{name}': {e}", exc_info=True)
        if conn: conn.rollback()  # Rollback changes on error
        return None
    finally:
        if conn: conn.close()


def get_all_products_db():
    """Retrieves all products from the database, ordered by name."""
    sql = "SELECT ProductID, ProductName, Price FROM Products ORDER BY ProductName"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        products = cursor.fetchall()
        return products
    except sqlite3.Error as e:
        logging.error(f"Database error in get_all_products_db: {e}", exc_info=True)
        return []  # Return empty list on error
    finally:
        if conn: conn.close()


def get_product_by_id_db(product_id):
    """Retrieves a single product by its ID."""
    sql = "SELECT ProductID, ProductName, Price FROM Products WHERE ProductID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (product_id,))
        product = cursor.fetchone()
        return product
    except sqlite3.Error as e:
        logging.error(f"Database error in get_product_by_id_db for ID {product_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def get_product_by_name_db(product_name):
    """Retrieves a single product by its name (case-sensitive)."""
    # Note: If you need case-insensitive search here, add COLLATE NOCASE
    # sql = "SELECT ProductID, ProductName, Price FROM Products WHERE ProductName = ? COLLATE NOCASE"
    sql = "SELECT ProductID, ProductName, Price FROM Products WHERE ProductName = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (product_name,))
        product = cursor.fetchone()
        return product
    except sqlite3.Error as e:
        logging.error(f"Database error in get_product_by_name_db for name '{product_name}': {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def update_product_db(product_id, name, price):
    """Updates an existing product's name and price."""
    sql = "UPDATE Products SET ProductName = ?, Price = ? WHERE ProductID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (name, price, product_id))
        conn.commit()
        updated_rows = cursor.rowcount
        logging.info(f"Updated product ID {product_id}. Rows affected: {updated_rows}")
        return updated_rows > 0  # Return True if update was successful
    except sqlite3.IntegrityError:
        logging.warning(f"Failed to update product ID {product_id}. Name '{name}' might already exist.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error in update_product_db for ID {product_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


def delete_product_db(product_id):
    """Deletes a product from the database."""
    sql = "DELETE FROM Products WHERE ProductID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (product_id,))
        conn.commit()
        deleted_rows = cursor.rowcount
        logging.info(f"Deleted product ID {product_id}. Rows affected: {deleted_rows}")
        return deleted_rows > 0  # Return True if a row was deleted
    except sqlite3.Error as e:
        # Foreign key errors might occur here if product is in SaleItems and ON DELETE is restricted
        logging.error(f"Database error in delete_product_db for ID {product_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


# --- Customer Operations ---

def add_customer_db(name, contact=None, address=None):
    """Adds a new customer."""
    sql = "INSERT INTO Customers (CustomerName, ContactNumber, Address) VALUES (?, ?, ?)"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (name, contact, address))
        conn.commit()
        customer_id = cursor.lastrowid
        logging.info(f"Added customer '{name}' with ID: {customer_id}")
        return customer_id
    except sqlite3.IntegrityError:
        logging.warning(f"Failed to add customer '{name}'. Name might already exist.")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_customer_db for customer '{name}': {e}", exc_info=True)
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()


def get_customers_paginated_db(page=1, per_page=10):
    """Retrieves customers paginated, ordered by name (case-insensitive)."""
    sql = """
          SELECT CustomerID, CustomerName, ContactNumber, Address, DateAdded
          FROM Customers
          ORDER BY CustomerName COLLATE NOCASE LIMIT ? \
          OFFSET ? \
          """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        offset = (page - 1) * per_page
        cursor.execute(sql, (per_page, offset))
        customers = cursor.fetchall()
        return customers
    except sqlite3.Error as e:
        logging.error(f"Database error in get_customers_paginated_db: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()


def count_total_customers_db():
    """Counts the total number of customers."""
    sql = "SELECT COUNT(*) FROM Customers"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        total_customers = cursor.fetchone()[0]  # fetchone()[0] gets the count value
        return total_customers
    except sqlite3.Error as e:
        logging.error(f"Database error in count_total_customers_db: {e}", exc_info=True)
        return 0  # Return 0 on error
    finally:
        if conn: conn.close()


def get_all_customers_db():
    """Retrieves ALL customers (not paginated), ordered by name (case-insensitive)."""
    sql = "SELECT CustomerID, CustomerName, ContactNumber, Address, DateAdded FROM Customers ORDER BY CustomerName COLLATE NOCASE"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        customers = cursor.fetchall()
        return customers
    except sqlite3.Error as e:
        logging.error(f"Database error in get_all_customers_db: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()


def get_customer_by_id_db(customer_id):
    """Retrieves a customer by ID."""
    sql = "SELECT CustomerID, CustomerName, ContactNumber, Address, DateAdded FROM Customers WHERE CustomerID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (customer_id,))
        customer = cursor.fetchone()
        return customer
    except sqlite3.Error as e:
        logging.error(f"Database error in get_customer_by_id_db for ID {customer_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def get_customer_by_name_db(customer_name):
    """Retrieves a customer by name (case-insensitive)."""
    sql = "SELECT CustomerID, CustomerName FROM Customers WHERE CustomerName = ? COLLATE NOCASE"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (customer_name,))
        customer = cursor.fetchone()
        return customer
    except sqlite3.Error as e:
        logging.error(f"Database error in get_customer_by_name_db for name '{customer_name}': {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def update_customer_db(customer_id, name, contact, address):
    """Updates an existing customer."""
    sql = "UPDATE Customers SET CustomerName = ?, ContactNumber = ?, Address = ? WHERE CustomerID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (name, contact, address, customer_id))
        conn.commit()
        updated_rows = cursor.rowcount
        logging.info(f"Updated customer ID {customer_id}. Rows affected: {updated_rows}")
        return updated_rows > 0
    except sqlite3.IntegrityError:
        logging.warning(f"Failed to update customer ID {customer_id}. Name '{name}' might already exist.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error in update_customer_db for ID {customer_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


def delete_customer_db(customer_id):
    """Deletes a customer."""
    sql = "DELETE FROM Customers WHERE CustomerID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (customer_id,))
        conn.commit()
        deleted_rows = cursor.rowcount
        logging.info(f"Deleted customer ID {customer_id}. Rows affected: {deleted_rows}")
        return deleted_rows > 0
    except sqlite3.Error as e:
        logging.error(f"Database error in delete_customer_db for ID {customer_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


# --- Sales Operations ---

def create_sale_db(customer_name='N/A'):
    """Creates a new sale record (with timestamp) and returns the SaleID."""
    sql = """
          INSERT INTO Sales (SaleTimestamp, CustomerName, TotalAmount)
          VALUES (?, ?, 0.0) \
          """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Get current timestamp in a format SQLite understands (YYYY-MM-DD HH:MM:SS)
        now_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(sql, (now_timestamp, customer_name))
        conn.commit()
        sale_id = cursor.lastrowid
        logging.info(
            f"Sale record created successfully with SaleID: {sale_id} for Customer: {customer_name} at {now_timestamp}")
        return sale_id
    except sqlite3.Error as e:
        logging.error(f"Database error in create_sale_db for customer '{customer_name}': {e}", exc_info=True)
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()


def add_sale_item_db(sale_id, product_name, quantity, price_at_sale):
    """Adds an item to a sale using the provided price_at_sale."""
    sql = """
          INSERT INTO SaleItems (SaleID, ProductName, Quantity, PriceAtSale, Subtotal)
          VALUES (?, ?, ?, ?, ?) \
          """
    conn = None
    try:
        subtotal = quantity * price_at_sale
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (sale_id, product_name, quantity, price_at_sale, subtotal))
        conn.commit()
        logging.info(f"Added item '{product_name}' (Qty: {quantity}, Price: {price_at_sale}) to SaleID: {sale_id}")
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error in add_sale_item_db for SaleID {sale_id}, Item '{product_name}': {e}",
                      exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


def get_sale_details_db(sale_id):
    """Retrieves sale details and its items."""
    sql_sale = "SELECT SaleID, SaleTimestamp, TotalAmount, CustomerName FROM Sales WHERE SaleID = ?"
    sql_items = "SELECT SaleItemID, ProductName, Quantity, PriceAtSale, Subtotal FROM SaleItems WHERE SaleID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql_sale, (sale_id,))
        sale_info = cursor.fetchone()
        if not sale_info: return None  # Sale not found

        cursor.execute(sql_items, (sale_id,))
        sale_items = cursor.fetchall()
        return {"info": sale_info, "items": sale_items}
    except sqlite3.Error as e:
        logging.error(f"Database error in get_sale_details_db for SaleID {sale_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def get_sales_paginated_db(page=1, per_page=10):
    """Retrieves sales records paginated, ordered by most recent first."""
    sql = """
          SELECT SaleID, SaleTimestamp, TotalAmount, CustomerName
          FROM Sales
          ORDER BY SaleTimestamp DESC, SaleID DESC LIMIT ? \
          OFFSET ? \
          """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        offset = (page - 1) * per_page
        cursor.execute(sql, (per_page, offset))
        sales = cursor.fetchall()
        return sales
    except sqlite3.Error as e:
        logging.error(f"Database error in get_sales_paginated_db: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()


def count_total_sales_db():
    """Counts the total number of sales records."""
    sql = "SELECT COUNT(*) FROM Sales"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        total_sales = cursor.fetchone()[0]
        return total_sales
    except sqlite3.Error as e:
        logging.error(f"Database error in count_total_sales_db: {e}", exc_info=True)
        return 0
    finally:
        if conn: conn.close()


def delete_sale_db(sale_id):
    """Deletes a sale record and its associated items (due to CASCADE)."""
    sql = "DELETE FROM Sales WHERE SaleID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (sale_id,))
        conn.commit()
        deleted_rows = cursor.rowcount
        if deleted_rows > 0:
            logging.info(f"Deleted SaleID {sale_id} and associated items. Rows affected: {deleted_rows}")
        else:
            logging.warning(f"Attempted to delete SaleID {sale_id}, but it was not found.")
        return deleted_rows > 0  # Return True if a row was deleted
    except sqlite3.Error as e:
        logging.error(f"Database error deleting SaleID {sale_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False  # Return False on error
    finally:
        if conn: conn.close()


# --- Dashboard / Sales Summary Functions ---

def get_total_sales_today_db():
    """Calculates the total amount of sales made today."""
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    # Assumes SaleTimestamp is stored as TEXT in 'YYYY-MM-DD HH:MM:SS' format
    sql = "SELECT SUM(TotalAmount) FROM Sales WHERE DATE(SaleTimestamp) = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (today_date,))
        total = cursor.fetchone()[0]
        return total if total is not None else 0.0  # Return 0.0 if no sales today
    except sqlite3.Error as e:
        logging.error(f"Database error getting total sales for today ({today_date}): {e}", exc_info=True)
        return 0.0  # Return 0.0 on error
    finally:
        if conn: conn.close()


def get_items_sold_today_db():
    """Gets a summary of items sold today (ProductName and total Quantity)."""
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    # Join Sales and SaleItems, filter by today's date, group by product name and sum quantity
    sql = """
          SELECT si.ProductName, SUM(si.Quantity) as TotalQuantity
          FROM SaleItems si
                   JOIN Sales s ON si.SaleID = s.SaleID
          WHERE DATE (s.SaleTimestamp) = ?
          GROUP BY si.ProductName
          ORDER BY TotalQuantity DESC, si.ProductName \
          """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (today_date,))
        items_summary = cursor.fetchall()
        return items_summary  # Returns a list of Row objects
    except sqlite3.Error as e:
        logging.error(f"Database error getting items sold today ({today_date}): {e}", exc_info=True)
        return []  # Return empty list on error
    finally:
        if conn: conn.close()


def get_total_sales_current_week_db():
    """Calculates the total amount of sales made in the current week (Mon-Today)."""
    today = datetime.date.today()
    # Calculate days to subtract to get to the previous Monday (weekday() is 0 for Mon, 6 for Sun)
    days_since_monday = today.weekday()
    start_of_week = today - datetime.timedelta(days=days_since_monday)

    start_date_str = start_of_week.strftime('%Y-%m-%d')
    end_date_str = today.strftime('%Y-%m-%d')  # Today is included

    # Assumes SaleTimestamp is stored as TEXT in 'YYYY-MM-DD HH:MM:SS' format
    # We compare the DATE part of the timestamp.
    sql = "SELECT SUM(TotalAmount) FROM Sales WHERE DATE(SaleTimestamp) >= ? AND DATE(SaleTimestamp) <= ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (start_date_str, end_date_str))
        total = cursor.fetchone()[0]
        logging.info(f"Fetched current week sales total ({start_date_str} to {end_date_str}): {total}")
        return total if total is not None else 0.0  # Return 0.0 if no sales in the period
    except sqlite3.Error as e:
        logging.error(f"Database error getting total sales for current week ({start_date_str} to {end_date_str}): {e}",
                      exc_info=True)
        return 0.0  # Return 0.0 on error
    finally:
        if conn: conn.close()

