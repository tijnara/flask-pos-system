# db_operations.py
# Description: This file contains functions to interact with the SQLite database
# for the SEASIDE Online POS System.

import sqlite3
import logging
import datetime
import calendar  # For month-related calculations in reports

# --- Database Configuration & Connection ---
DATABASE_URL = "pos_system.db"  # Name of the SQLite database file

# Configure basic logging for this module
# In a larger application, this might be configured globally.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(module)s - %(levelname)s - %(message)s')


def get_db_connection():
    """
    Establishes and returns a connection to the SQLite database.
    The connection is configured to return rows as dictionary-like objects
    and to enforce foreign key constraints.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row  # Access columns by name (e.g., row['ColumnName'])
        conn.execute("PRAGMA foreign_keys = ON;")  # Enforce foreign key constraints
        logging.debug("Database connection established successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database connection error to '{DATABASE_URL}': {e}", exc_info=True)
        raise  # Re-raise the exception if connection fails, so the app can handle it
    return conn


# --- Product Operations ---

def add_product_db(name, price):
    """Adds a new product to the Products table."""
    sql = "INSERT INTO Products (ProductName, Price) VALUES (?, ?)"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (name, price))
        conn.commit()
        product_id = cursor.lastrowid
        logging.info(f"Product '{name}' added successfully with ID: {product_id}.")
        return product_id
    except sqlite3.IntegrityError:  # Handles cases like duplicate product names if UNIQUE constraint exists
        logging.warning(f"Failed to add product '{name}'. It might already exist or violate a constraint.")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_product_db for product '{name}': {e}", exc_info=True)
        if conn: conn.rollback()  # Rollback changes on error
        return None
    finally:
        if conn: conn.close()


def get_all_products_db():
    """Retrieves all products from the Products table, ordered by name."""
    sql = "SELECT ProductID, ProductName, Price FROM Products ORDER BY ProductName COLLATE NOCASE"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        products = cursor.fetchall()  # Returns a list of sqlite3.Row objects
        return products
    except sqlite3.Error as e:
        logging.error(f"Database error in get_all_products_db: {e}", exc_info=True)
        return []  # Return an empty list on error
    finally:
        if conn: conn.close()


def get_product_by_id_db(product_id):
    """Retrieves a specific product by its ProductID."""
    sql = "SELECT ProductID, ProductName, Price FROM Products WHERE ProductID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (product_id,))
        product = cursor.fetchone()  # Returns a single sqlite3.Row object or None
        return product
    except sqlite3.Error as e:
        logging.error(f"Database error in get_product_by_id_db for ID {product_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def get_product_by_name_db(product_name):
    """Retrieves a specific product by its ProductName (case-insensitive)."""
    sql = "SELECT ProductID, ProductName, Price FROM Products WHERE ProductName = ? COLLATE NOCASE"
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
    """Updates an existing product's details."""
    sql = "UPDATE Products SET ProductName = ?, Price = ? WHERE ProductID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (name, price, product_id))
        conn.commit()
        updated_rows = cursor.rowcount
        if updated_rows > 0:
            logging.info(f"Product ID {product_id} updated successfully. Name: '{name}', Price: {price}.")
        else:
            logging.warning(
                f"Attempted to update product ID {product_id}, but no rows were affected (product might not exist).")
        return updated_rows > 0  # Returns True if a row was updated, False otherwise
    except sqlite3.IntegrityError:
        logging.warning(
            f"Failed to update product ID {product_id}. New name '{name}' might already exist or violate a constraint.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error in update_product_db for ID {product_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


def delete_product_db(product_id):
    """Deletes a product from the Products table."""
    # Note: If foreign key constraints link Products to SaleItems,
    # this might fail if the product is part of any sale, unless ON DELETE CASCADE/SET NULL is set up.
    sql = "DELETE FROM Products WHERE ProductID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (product_id,))
        conn.commit()
        deleted_rows = cursor.rowcount
        if deleted_rows > 0:
            logging.info(f"Product ID {product_id} deleted successfully.")
        else:
            logging.warning(f"Attempted to delete product ID {product_id}, but it was not found.")
        return deleted_rows > 0
    except sqlite3.IntegrityError as ie:  # Specifically catch integrity errors (like FK constraints)
        logging.error(
            f"Database integrity error deleting product ID {product_id}: {ie}. Product might be in use in sales records.",
            exc_info=True)
        if conn: conn.rollback()
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error in delete_product_db for ID {product_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


# --- Customer Operations ---

def add_customer_db(name, contact=None, address=None):
    """Adds a new customer to the Customers table."""
    # Assuming your Customers table has CustomerName, ContactNumber, Address
    # And DateAdded might have a DEFAULT CURRENT_TIMESTAMP or is handled by your schema
    sql = "INSERT INTO Customers (CustomerName, ContactNumber, Address) VALUES (?, ?, ?)"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (name, contact or None, address or None))  # Ensure empty strings become NULL if desired
        conn.commit()
        customer_id = cursor.lastrowid
        logging.info(f"Customer '{name}' added successfully with ID: {customer_id}.")
        return customer_id
    except sqlite3.IntegrityError:  # Assuming CustomerName might be UNIQUE
        logging.warning(f"Failed to add customer '{name}'. Name might already exist or violate a constraint.")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_customer_db for customer '{name}': {e}", exc_info=True)
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()


def get_customers_paginated_db(page=1, per_page=10):
    """Retrieves a paginated list of customers."""
    # Using your existing column names: CustomerID, CustomerName, ContactNumber, Address, DateAdded
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
        total_customers = cursor.fetchone()[0]
        return total_customers
    except sqlite3.Error as e:
        logging.error(f"Database error in count_total_customers_db: {e}", exc_info=True)
        return 0
    finally:
        if conn: conn.close()


def get_all_customers_db():
    """Retrieves all customers, ordered by name."""
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
    """Retrieves a specific customer by their CustomerID."""
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
    """Retrieves a customer by their name (case-insensitive)."""
    # Used in POS to link sales to existing customers.
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
    """Updates an existing customer's details."""
    sql = "UPDATE Customers SET CustomerName = ?, ContactNumber = ?, Address = ? WHERE CustomerID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (name, contact or None, address or None, customer_id))
        conn.commit()
        updated_rows = cursor.rowcount
        if updated_rows > 0:
            logging.info(f"Customer ID {customer_id} updated successfully. Name: '{name}'.")
        else:
            logging.warning(
                f"Attempted to update customer ID {customer_id}, but no rows affected (customer might not exist).")
        return updated_rows > 0
    except sqlite3.IntegrityError:
        logging.warning(f"Failed to update customer ID {customer_id}. New name '{name}' might already exist.")
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error in update_customer_db for ID {customer_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


def delete_customer_db(customer_id):
    """Deletes a customer from the Customers table."""
    # Note: If CustomerID in Sales table has a FK constraint to Customers.CustomerID,
    # this might fail unless ON DELETE SET NULL or ON DELETE SET DEFAULT is configured.
    # Your current Sales table seems to store CustomerName directly.
    sql = "DELETE FROM Customers WHERE CustomerID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (customer_id,))
        conn.commit()
        deleted_rows = cursor.rowcount
        if deleted_rows > 0:
            logging.info(f"Customer ID {customer_id} deleted successfully.")
        else:
            logging.warning(f"Attempted to delete customer ID {customer_id}, but it was not found.")
        return deleted_rows > 0
    except sqlite3.IntegrityError as ie:
        logging.error(
            f"Database integrity error deleting customer ID {customer_id}: {ie}. Customer might be linked in other records.",
            exc_info=True)
        if conn: conn.rollback()
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error in delete_customer_db for ID {customer_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


# --- Sales Operations ---

def create_sale_db(customer_name='N/A'):
    """
    Creates a new sale record in the Sales table.
    Assumes Sales table stores CustomerName directly.
    Initial TotalAmount is 0.0, to be updated after items are added.
    """
    sql = "INSERT INTO Sales (SaleTimestamp, CustomerName, TotalAmount) VALUES (?, ?, 0.0)"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(sql, (now_timestamp, customer_name if customer_name else 'N/A'))
        conn.commit()
        sale_id = cursor.lastrowid
        logging.info(f"Sale record created with SaleID: {sale_id} for Customer: '{customer_name}' at {now_timestamp}.")
        return sale_id
    except sqlite3.Error as e:
        logging.error(f"Database error in create_sale_db for customer '{customer_name}': {e}", exc_info=True)
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()


def add_sale_item_db(sale_id, product_name, quantity, price_at_sale):
    """Adds an item to a sale in the SaleItems table."""
    sql = "INSERT INTO SaleItems (SaleID, ProductName, Quantity, PriceAtSale, Subtotal) VALUES (?, ?, ?, ?, ?)"
    conn = None
    try:
        subtotal = round(quantity * price_at_sale, 2)  # Calculate and round subtotal
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (sale_id, product_name, quantity, price_at_sale, subtotal))
        conn.commit()
        logging.info(f"Added item '{product_name}' (Qty: {quantity}, Price: {price_at_sale}) to SaleID: {sale_id}.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error in add_sale_item_db for SaleID {sale_id}, Item '{product_name}': {e}",
                      exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


def get_sale_details_db(sale_id):
    """Retrieves details for a specific sale, including its items."""
    sql_sale = "SELECT SaleID, SaleTimestamp, TotalAmount, CustomerName FROM Sales WHERE SaleID = ?"
    sql_items = "SELECT SaleItemID, ProductName, Quantity, PriceAtSale, Subtotal FROM SaleItems WHERE SaleID = ? ORDER BY SaleItemID"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql_sale, (sale_id,))
        sale_info_row = cursor.fetchone()

        if not sale_info_row:
            logging.warning(f"No sale found with SaleID: {sale_id} in get_sale_details_db.")
            return None

        sale_info = dict(sale_info_row)

        cursor.execute(sql_items, (sale_id,))
        sale_items_rows = cursor.fetchall()
        sale_items = [dict(row) for row in sale_items_rows]

        return {"info": sale_info, "items": sale_items}
    except sqlite3.Error as e:
        logging.error(f"Database error in get_sale_details_db for SaleID {sale_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def get_sales_paginated_db(page=1, per_page=10, start_date=None, end_date=None):
    """
    Fetches paginated sales records, optionally filtered by a date range.
    Args:
        page (int): The current page number.
        per_page (int): Number of items per page.
        start_date (str, optional): Start date in 'YYYY-MM-DD' format.
        end_date (str, optional): End date in 'YYYY-MM-DD' format.
    Returns:
        list: A list of sales records (sqlite3.Row objects).
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        offset = (page - 1) * per_page

        params = []
        sql = "SELECT s.SaleID, s.SaleTimestamp, s.TotalAmount, s.CustomerName FROM Sales s"

        conditions = []
        if start_date:
            conditions.append("DATE(s.SaleTimestamp) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(s.SaleTimestamp) <= ?")
            params.append(end_date)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY s.SaleTimestamp DESC, s.SaleID DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        logging.debug(f"Executing SQL for paginated sales: {sql} with params: {params}")
        cursor.execute(sql, tuple(params))
        sales = cursor.fetchall()
        return sales
    except sqlite3.Error as e:
        logging.error(f"Database error in get_sales_paginated_db: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()


def count_total_sales_db(start_date=None, end_date=None):
    """
    Counts total sales records, optionally filtered by a date range.
    Args:
        start_date (str, optional): Start date in 'YYYY-MM-DD' format.
        end_date (str, optional): End date in 'YYYY-MM-DD' format.
    Returns:
        int: The total number of sales records matching the criteria.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        params = []
        sql = "SELECT COUNT(*) FROM Sales s"

        conditions = []
        if start_date:
            conditions.append("DATE(s.SaleTimestamp) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(s.SaleTimestamp) <= ?")
            params.append(end_date)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        logging.debug(f"Executing SQL for counting sales: {sql} with params: {params}")
        cursor.execute(sql, tuple(params))
        total_sales = cursor.fetchone()[0]
        return total_sales
    except sqlite3.Error as e:
        logging.error(f"Database error in count_total_sales_db: {e}", exc_info=True)
        return 0
    finally:
        if conn: conn.close()


def delete_sale_db(sale_id):
    """Deletes a sale and its associated items from the database."""
    sql_delete_items = "DELETE FROM SaleItems WHERE SaleID = ?"
    sql_delete_sale = "DELETE FROM Sales WHERE SaleID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        conn.execute("BEGIN TRANSACTION")
        cursor.execute(sql_delete_items, (sale_id,))
        cursor.execute(sql_delete_sale, (sale_id,))
        conn.commit()
        logging.info(f"SaleID {sale_id} and its items deleted successfully.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Database error deleting SaleID {sale_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


def get_sales_in_range_summary_db(start_date=None, end_date=None):
    """
    Fetches summary information for all sales within a given date range.
    Not paginated. Used for 'View All Receipts for Range'.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        params = []
        sql = "SELECT s.SaleID, s.SaleTimestamp, s.TotalAmount, s.CustomerName FROM Sales s"
        conditions = []
        if start_date:
            conditions.append("DATE(s.SaleTimestamp) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(s.SaleTimestamp) <= ?")
            params.append(end_date)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY s.SaleTimestamp ASC, s.SaleID ASC"

        logging.debug(f"Executing SQL for sales in range summary: {sql} with params: {params}")
        cursor.execute(sql, tuple(params))
        sales_summaries = cursor.fetchall()
        return sales_summaries
    except sqlite3.Error as e:
        logging.error(f"Database error in get_sales_in_range_summary_db: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()


# --- Dashboard / Sales Summary Functions ---

def get_total_sales_today_db():
    """Calculates the total amount of sales made today."""
    today_date_str = datetime.date.today().strftime('%Y-%m-%d')
    sql = "SELECT SUM(TotalAmount) FROM Sales WHERE DATE(SaleTimestamp) = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (today_date_str,))
        total_row = cursor.fetchone()
        total = total_row[0] if total_row and total_row[0] is not None else 0.0
        return total
    except sqlite3.Error as e:
        logging.error(f"Database error getting total sales for today ({today_date_str}): {e}", exc_info=True)
        return 0.0
    finally:
        if conn: conn.close()


def get_items_sold_today_db():
    """Gets a summary of items sold today (ProductName and total Quantity)."""
    today_date_str = datetime.date.today().strftime('%Y-%m-%d')
    sql = """
          SELECT si.ProductName, SUM(si.Quantity) as TotalQuantity
          FROM SaleItems si
                   JOIN Sales s ON si.SaleID = s.SaleID
          WHERE DATE (s.SaleTimestamp) = ?
          GROUP BY si.ProductName COLLATE NOCASE
          ORDER BY TotalQuantity DESC, si.ProductName \
          """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (today_date_str,))
        items_summary = cursor.fetchall()
        return items_summary
    except sqlite3.Error as e:
        logging.error(f"Database error getting items sold today ({today_date_str}): {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()


def get_total_sales_current_week_db():
    """
    Calculates the total amount of sales made in the current week (Monday to Sunday).
    """
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + datetime.timedelta(days=6)  # Sunday

    start_date_str = start_of_week.strftime('%Y-%m-%d')
    end_date_str = end_of_week.strftime('%Y-%m-%d')

    sql = "SELECT SUM(TotalAmount) FROM Sales WHERE DATE(SaleTimestamp) >= ? AND DATE(SaleTimestamp) <= ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (start_date_str, end_date_str))
        total_row = cursor.fetchone()
        total = total_row[0] if total_row and total_row[0] is not None else 0.0
        logging.info(f"Fetched current week (Mon-Sun) sales total ({start_date_str} to {end_date_str}): {total}")
        return total
    except sqlite3.Error as e:
        logging.error(
            f"Database error getting total sales for current week Mon-Sun ({start_date_str} to {end_date_str}): {e}",
            exc_info=True)
        return 0.0
    finally:
        if conn: conn.close()


# --- Reporting Functions (Weekly & Monthly) ---

def get_weekly_sales_chart_data_db(start_date_obj, end_date_obj):
    """
    Fetches daily sales data for a given week for chart display.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql_daily_totals = """
                           SELECT DATE (SaleTimestamp) as SaleDay, SUM (TotalAmount) as DailyTotal
                           FROM Sales
                           WHERE DATE (SaleTimestamp) >= ? AND DATE (SaleTimestamp) <= ?
                           GROUP BY SaleDay \
                           ORDER BY SaleDay ASC; \
                           """
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')

        cursor.execute(sql_daily_totals, (start_date_str, end_date_str))
        sales_data_rows = cursor.fetchall()

        labels = []
        data = []
        total_sales_for_period = 0.0
        sales_dict = {row['SaleDay']: row['DailyTotal'] for row in sales_data_rows}

        current_date = start_date_obj
        while current_date <= end_date_obj:
            date_str_key = current_date.strftime('%Y-%m-%d')
            labels.append(current_date.strftime('%a'))
            daily_total = float(sales_dict.get(date_str_key, 0.0))
            data.append(daily_total)
            total_sales_for_period += daily_total
            current_date += datetime.timedelta(days=1)

        logging.info(f"Weekly sales chart data: {start_date_str} to {end_date_str}. Total: {total_sales_for_period}")
        return {'labels': labels, 'data': data, 'total': round(total_sales_for_period, 2)}
    except sqlite3.Error as e:
        logging.error(f"DB error in get_weekly_sales_chart_data_db ({start_date_obj} to {end_date_obj}): {e}",
                      exc_info=True)
        return {'labels': [], 'data': [], 'total': 0.0, 'error': str(e)}
    except Exception as e:
        logging.error(f"Unexpected error in get_weekly_sales_chart_data_db: {e}", exc_info=True)
        return {'labels': [], 'data': [], 'total': 0.0, 'error': str(e)}
    finally:
        if conn: conn.close()


def get_items_sold_summary_for_period_db(start_date_obj, end_date_obj):
    """
    Fetches a summary of items sold within a given period (e.g., a week).
    """
    sql = """
          SELECT si.ProductName as ItemName, SUM(si.Quantity) as ItemsSold, SUM(si.Subtotal) as TotalSales
          FROM SaleItems si
                   JOIN Sales s ON si.SaleID = s.SaleID
          WHERE DATE (s.SaleTimestamp) >= ? AND DATE (s.SaleTimestamp) <= ?
          GROUP BY si.ProductName COLLATE NOCASE
          ORDER BY TotalSales DESC, si.ProductName ASC; \
          """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')

        cursor.execute(sql, (start_date_str, end_date_str))
        item_summary_rows = cursor.fetchall()
        item_summary = [dict(row) for row in item_summary_rows]
        logging.info(f"Item summary for period {start_date_str} to {end_date_str}. Items: {len(item_summary)}")
        return item_summary
    except sqlite3.Error as e:
        logging.error(f"DB error in get_items_sold_summary_for_period_db ({start_date_obj} to {end_date_obj}): {e}",
                      exc_info=True)
        return None
    except Exception as e:
        logging.error(f"Unexpected error in get_items_sold_summary_for_period_db: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def get_monthly_sales_chart_data_db(year, month):
    """
    Fetches daily sales data for a given month for chart display.
    """
    conn = None
    month_name_str = calendar.month_name[month] if 1 <= month <= 12 else "Invalid Month"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        first_day_of_month = datetime.date(year, month, 1)
        num_days_in_month = calendar.monthrange(year, month)[1]
        last_day_of_month = datetime.date(year, month, num_days_in_month)

        start_date_str = first_day_of_month.strftime('%Y-%m-%d')
        end_date_str = last_day_of_month.strftime('%Y-%m-%d')

        sql_daily_totals = """
                           SELECT DATE (SaleTimestamp) as SaleDay, SUM (TotalAmount) as DailyTotal
                           FROM Sales
                           WHERE DATE (SaleTimestamp) >= ? AND DATE (SaleTimestamp) <= ?
                           GROUP BY SaleDay \
                           ORDER BY SaleDay ASC; \
                           """
        cursor.execute(sql_daily_totals, (start_date_str, end_date_str))
        sales_data_rows = cursor.fetchall()

        labels = []
        data = []
        total_sales_for_month = 0.0
        sales_dict = {row['SaleDay']: row['DailyTotal'] for row in sales_data_rows}

        for day_num in range(1, num_days_in_month + 1):
            current_day_obj = datetime.date(year, month, day_num)
            current_day_str_key = current_day_obj.strftime('%Y-%m-%d')
            labels.append(str(day_num))
            daily_total = float(sales_dict.get(current_day_str_key, 0.0))
            data.append(daily_total)
            total_sales_for_month += daily_total

        logging.info(f"Monthly sales chart data for {year}-{month:02d}. Total: {total_sales_for_month}")
        return {'labels': labels, 'data': data, 'total': round(total_sales_for_month, 2), 'month_name': month_name_str}
    except sqlite3.Error as e:
        logging.error(f"DB error in get_monthly_sales_chart_data_db ({year}-{month:02d}): {e}", exc_info=True)
        return {'labels': [], 'data': [], 'total': 0.0, 'month_name': month_name_str, 'error': str(e)}
    except Exception as e:
        logging.error(f"Unexpected error in get_monthly_sales_chart_data_db ({year}-{month:02d}): {e}", exc_info=True)
        return {'labels': [], 'data': [], 'total': 0.0, 'month_name': month_name_str, 'error': str(e)}
    finally:
        if conn: conn.close()


def get_items_sold_summary_for_month_db(year, month):
    """
    Fetches a summary of items sold within a given month.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        first_day_of_month = datetime.date(year, month, 1)
        num_days_in_month = calendar.monthrange(year, month)[1]
        last_day_of_month = datetime.date(year, month, num_days_in_month)

        start_date_str = first_day_of_month.strftime('%Y-%m-%d')
        end_date_str = last_day_of_month.strftime('%Y-%m-%d')

        sql = """
              SELECT si.ProductName as ItemName, SUM(si.Quantity) as ItemsSold, SUM(si.Subtotal) as TotalSales
              FROM SaleItems si
                       JOIN Sales s ON si.SaleID = s.SaleID
              WHERE DATE (s.SaleTimestamp) >= ? AND DATE (s.SaleTimestamp) <= ?
              GROUP BY si.ProductName COLLATE NOCASE
              ORDER BY TotalSales DESC, si.ProductName ASC; \
              """
        cursor.execute(sql, (start_date_str, end_date_str))
        item_summary_rows = cursor.fetchall()
        item_summary = [dict(row) for row in item_summary_rows]

        logging.info(f"Monthly item summary for {year}-{month:02d}. Items: {len(item_summary)}")
        return item_summary
    except sqlite3.Error as e:
        logging.error(f"DB error in get_items_sold_summary_for_month_db ({year}-{month:02d}): {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"Unexpected error in get_items_sold_summary_for_month_db ({year}-{month:02d}): {e}",
                      exc_info=True)
        return None
    finally:
        if conn: conn.close()
