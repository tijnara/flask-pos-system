# db_operations.py
# Description: This file contains functions to interact with the SQLite database.
import sqlite3
import logging
import datetime  # Make sure this is imported

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_URL = "pos_system.db"


def get_db_connection():
    """Establishes a connection to the SQLite database specified by DATABASE_URL."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row  # Access columns by name
        conn.execute("PRAGMA foreign_keys = ON;")  # Ensure foreign key constraints are enforced
        logging.debug("Database connection established.")
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}", exc_info=True)
        raise  # Re-raise the exception if connection fails
    return conn


# --- Product Operations ---
def add_product_db(name, price):
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
        logging.warning(f"Failed to add product '{name}'. It might already exist.")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_product_db for product '{name}': {e}", exc_info=True)
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()


def get_all_products_db():
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
        return []
    finally:
        if conn: conn.close()


def get_product_by_id_db(product_id):
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
    sql = "UPDATE Products SET ProductName = ?, Price = ? WHERE ProductID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (name, price, product_id))
        conn.commit()
        updated_rows = cursor.rowcount
        logging.info(f"Updated product ID {product_id}. Rows affected: {updated_rows}")
        return updated_rows > 0
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
    sql = "DELETE FROM Products WHERE ProductID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (product_id,))
        conn.commit()
        deleted_rows = cursor.rowcount
        logging.info(f"Deleted product ID {product_id}. Rows affected: {deleted_rows}")
        return deleted_rows > 0
    except sqlite3.Error as e:  # Catching generic sqlite3.Error, could be IntegrityError if FK constraints exist
        logging.error(f"Database error in delete_product_db for ID {product_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


# --- Customer Operations ---
def add_customer_db(name, contact=None, address=None):  # Using your existing signature
    # Assuming your Customers table has CustomerName, ContactNumber, Address, DateAdded
    # And DateAdded has a DEFAULT CURRENT_TIMESTAMP or is handled by your schema
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
    except sqlite3.IntegrityError:  # Assuming CustomerName might be UNIQUE
        logging.warning(f"Failed to add customer '{name}'. Name might already exist.")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_customer_db for customer '{name}': {e}", exc_info=True)
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()


def get_customers_paginated_db(page=1, per_page=10):
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
    # Assuming your app.py might use this to link sales to existing customers
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
    except sqlite3.Error as e:  # Could be IntegrityError if customer is linked in Sales and FK is RESTRICT
        logging.error(f"Database error in delete_customer_db for ID {customer_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


# --- Sales Operations ---
def create_sale_db(customer_name='N/A'):
    # Using your schema: Sales (SaleTimestamp, CustomerName, TotalAmount)
    # Note: Your app.py passes customer_name. If you want to link by CustomerID,
    # you'd fetch CustomerID based on customer_name here.
    # For simplicity, this version stores CustomerName directly in Sales table as per your existing function.
    sql = """
          INSERT INTO Sales (SaleTimestamp, CustomerName, TotalAmount)
          VALUES (?, ?, 0.0) \
          """  # Initial total is 0, will be updated later
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # If you decide to link by CustomerID in Sales table instead of CustomerName:
        # customer_id_to_link = None
        # if customer_name and customer_name != 'N/A':
        #     cust_record = get_customer_by_name_db(customer_name) # Assumes this returns a record with CustomerID
        #     if cust_record:
        #         customer_id_to_link = cust_record['CustomerID']
        # cursor.execute(sql, (now_timestamp, customer_id_to_link, 0.0))

        # Sticking to your current direct CustomerName storage in Sales:
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
    # Using your schema: SaleItems (SaleID, ProductName, Quantity, PriceAtSale, Subtotal)
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
        return True  # Indicates success
    except sqlite3.Error as e:
        logging.error(f"Database error in add_sale_item_db for SaleID {sale_id}, Item '{product_name}': {e}",
                      exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


def get_sale_details_db(sale_id):
    # Using your schema: Sales (SaleID, SaleTimestamp, TotalAmount, CustomerName)
    # SaleItems (SaleItemID, ProductName, Quantity, PriceAtSale, Subtotal)
    sql_sale = "SELECT SaleID, SaleTimestamp, TotalAmount, CustomerName FROM Sales WHERE SaleID = ?"
    sql_items = "SELECT SaleItemID, ProductName, Quantity, PriceAtSale, Subtotal FROM SaleItems WHERE SaleID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql_sale, (sale_id,))
        sale_info_row = cursor.fetchone()
        if not sale_info_row:
            logging.warning(f"No sale found with SaleID: {sale_id}")
            return None

        sale_info = dict(sale_info_row)  # Convert sqlite3.Row to dict

        cursor.execute(sql_items, (sale_id,))
        sale_items_rows = cursor.fetchall()
        sale_items = [dict(row) for row in sale_items_rows]  # Convert list of sqlite3.Row to list of dicts

        return {"info": sale_info, "items": sale_items}
    except sqlite3.Error as e:
        logging.error(f"Database error in get_sale_details_db for SaleID {sale_id}: {e}", exc_info=True)
        return None
    finally:
        if conn: conn.close()


def get_sales_paginated_db(page=1, per_page=10):
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
        return sales  # Returns list of sqlite3.Row objects
    except sqlite3.Error as e:
        logging.error(f"Database error in get_sales_paginated_db: {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()


def count_total_sales_db():
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
    # Assumes SaleItems are deleted by CASCADE constraint or handled separately if needed
    sql_delete_items = "DELETE FROM SaleItems WHERE SaleID = ?"
    sql_delete_sale = "DELETE FROM Sales WHERE SaleID = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Explicitly delete items first if no CASCADE ON DELETE for SaleItems.SaleID
        cursor.execute(sql_delete_items, (sale_id,))
        cursor.execute(sql_delete_sale, (sale_id,))
        conn.commit()
        deleted_rows = cursor.rowcount  # This will be for the Sales table deletion
        if deleted_rows > 0:
            logging.info(f"Deleted SaleID {sale_id} and its items. Rows affected for Sales table: {deleted_rows}")
        else:
            logging.warning(f"Attempted to delete SaleID {sale_id}, but it was not found in Sales table.")
        return deleted_rows > 0
    except sqlite3.Error as e:
        logging.error(f"Database error deleting SaleID {sale_id}: {e}", exc_info=True)
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


# --- Dashboard / Sales Summary Functions ---
def get_total_sales_today_db():
    """Calculates the total amount of sales made today."""
    today_date_str = datetime.date.today().strftime('%Y-%m-%d')
    # Uses DATE(SaleTimestamp) to compare just the date part
    sql = "SELECT SUM(TotalAmount) FROM Sales WHERE DATE(SaleTimestamp) = ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (today_date_str,))
        total = cursor.fetchone()[0]
        return total if total is not None else 0.0
    except sqlite3.Error as e:
        logging.error(f"Database error getting total sales for today ({today_date_str}): {e}", exc_info=True)
        return 0.0
    finally:
        if conn: conn.close()


def get_items_sold_today_db():  # This function was in your uploaded file, keeping it.
    """Gets a summary of items sold today (ProductName and total Quantity)."""
    today_date_str = datetime.date.today().strftime('%Y-%m-%d')
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
        cursor.execute(sql, (today_date_str,))
        items_summary = cursor.fetchall()
        return items_summary  # Returns list of sqlite3.Row
    except sqlite3.Error as e:
        logging.error(f"Database error getting items sold today ({today_date_str}): {e}", exc_info=True)
        return []
    finally:
        if conn: conn.close()


def get_total_sales_current_week_db():
    """Calculates the total amount of sales made in the current week (Mon-Today)."""
    today = datetime.date.today()
    # Monday is 0, Sunday is 6. today.weekday() gives Monday as 0.
    days_since_monday = today.weekday()
    start_of_week = today - datetime.timedelta(days=days_since_monday)

    start_date_str = start_of_week.strftime('%Y-%m-%d')
    end_date_str = today.strftime('%Y-%m-%d')  # Current week means up to today

    sql = "SELECT SUM(TotalAmount) FROM Sales WHERE DATE(SaleTimestamp) >= ? AND DATE(SaleTimestamp) <= ?"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (start_date_str, end_date_str))
        total = cursor.fetchone()[0]
        logging.info(
            f"Fetched current week sales total (Mon-Today: {start_date_str} to {end_date_str}): {total if total else 0.0}")
        return total if total is not None else 0.0
    except sqlite3.Error as e:
        logging.error(f"Database error getting total sales for current week ({start_date_str} to {end_date_str}): {e}",
                      exc_info=True)
        return 0.0
    finally:
        if conn: conn.close()


# --- REPORTING FUNCTIONS (FOR REPORTS PAGE) ---

def get_weekly_sales_chart_data_db(start_date_obj, end_date_obj):
    """
    Fetches sales data for a given period (typically a week) for chart display.
    Args:
        start_date_obj (datetime.date): The first day of the period.
        end_date_obj (datetime.date): The last day of the period.
    Returns:
        dict: {'labels': list_of_day_names, 'data': list_of_sales_amounts, 'total': total_sales_for_period}
              Returns a default dict with zeros/empty lists if an error occurs or no data.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL query to get daily totals within the date range
        sql_daily_totals = """
                           SELECT
                               DATE (SaleTimestamp) as SaleDay, SUM (TotalAmount) as DailyTotal
                           FROM Sales
                           WHERE DATE (SaleTimestamp) >= ? AND DATE (SaleTimestamp) <= ?
                           GROUP BY SaleDay
                           ORDER BY SaleDay ASC; \
                           """
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')

        cursor.execute(sql_daily_totals, (start_date_str, end_date_str))
        sales_data_rows = cursor.fetchall()

        labels = []
        data = []
        total_sales_for_period = 0.0

        # Create a dictionary of sales for quick lookup
        sales_dict = {row['SaleDay']: row['DailyTotal'] for row in sales_data_rows}

        # Iterate through each day in the specified period to ensure all days are represented
        current_date = start_date_obj
        while current_date <= end_date_obj:
            date_str_key = current_date.strftime('%Y-%m-%d')
            labels.append(current_date.strftime('%a'))  # e.g., 'Mon', 'Tue' for chart labels

            daily_total = sales_dict.get(date_str_key, 0.0)  # Get sales for the day, or 0.0 if no sales
            data.append(daily_total)
            total_sales_for_period += daily_total

            current_date += datetime.timedelta(days=1)

        logging.info(
            f"Weekly sales chart data fetched for {start_date_str} to {end_date_str}. Total: {total_sales_for_period}")
        return {'labels': labels, 'data': data, 'total': total_sales_for_period}

    except sqlite3.Error as e:
        logging.error(
            f"Database error in get_weekly_sales_chart_data_db for period {start_date_obj} to {end_date_obj}: {e}",
            exc_info=True)
        return {'labels': [], 'data': [], 'total': 0.0, 'error': str(e)}  # Return default on error
    except Exception as e:  # Catch any other unexpected errors
        logging.error(f"An unexpected error occurred in get_weekly_sales_chart_data_db: {e}", exc_info=True)
        return {'labels': [], 'data': [], 'total': 0.0, 'error': str(e)}
    finally:
        if conn:
            conn.close()


def get_items_sold_summary_for_period_db(start_date_obj, end_date_obj):
    """
    Fetches a summary of items sold within a given period.
    This function is adapted from your 'get_item_summary_for_week_db'
    and renamed to match what app.py's reports_page expects.
    Args:
        start_date_obj (datetime.date): The first day of the period.
        end_date_obj (datetime.date): The last day of the period.
    Returns:
        list: A list of dictionaries, e.g.,
              [{'ItemName': 'Product A', 'ItemsSold': 10, 'TotalSales': 100.00}, ...]
              Returns an empty list if an error occurs or no data.
    """
    sql = """
          SELECT si.ProductName   as ItemName, \
                 SUM(si.Quantity) as ItemsSold, \
                 SUM(si.Subtotal) as TotalSales
          FROM SaleItems si
                   JOIN Sales s ON si.SaleID = s.SaleID
          WHERE DATE (s.SaleTimestamp) >= ? AND DATE (s.SaleTimestamp) <= ?
          GROUP BY si.ProductName -- Using ProductName from SaleItems as ItemName
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
        # Convert list of sqlite3.Row objects to list of dictionaries
        item_summary = [dict(row) for row in item_summary_rows]
        logging.info(
            f"Item summary fetched for period {start_date_str} to {end_date_str}. Items found: {len(item_summary)}")
        return item_summary
    except sqlite3.Error as e:
        logging.error(f"Database error getting item summary for period {start_date_obj} to {end_date_obj}: {e}",
                      exc_info=True)
        return []  # Return empty list on error
    except Exception as e:  # Catch any other unexpected errors
        logging.error(f"An unexpected error occurred in get_items_sold_summary_for_period_db: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

# Note: The functions get_daily_sales_for_week_db and get_item_summary_for_week_db
# from your uploaded file have been effectively replaced/renamed to
# get_weekly_sales_chart_data_db and get_items_sold_summary_for_period_db
# to match the expectations of the app.py reports_page route.
