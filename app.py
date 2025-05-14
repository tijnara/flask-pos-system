# app.py
# Description: The main Flask application file for SEASIDE Online POS System.

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import sqlite3  # Import sqlite3 directly
import db_operations as db  # Handles database interactions
import datetime
from dateutil.relativedelta import relativedelta  # For date calculations (e.g., previous/next month)
import os
import shutil
from werkzeug.utils import secure_filename
import math  # For pagination calculations (math.ceil)
import logging
from functools import wraps  # For decorators like @login_required
import calendar  # For month names and date calculations

app = Flask(__name__)

# --- IMPORTANT: Secret Key Configuration ---
# MUST be set to a strong, random, secret value for sessions to be secure.
# Load from environment variable in production!
app.secret_key = os.environ.get("SECRET_KEY", "a_very_secret_default_key_for_dev_123!@#$")
if app.secret_key == "a_very_secret_default_key_for_dev_123!@#$" and os.environ.get("FLASK_ENV") != "development":
    with app.app_context():  # Use app context for logger if app is already created
        app.logger.warning(
            "SECURITY WARNING: Using default SECRET_KEY. Set the SECRET_KEY environment variable in production.")

# --- Hardcoded Password (INSECURE - FOR DEMO/DEVELOPMENT ONLY) ---
# Replace this with a proper user authentication system in a real application.
HARDCODED_PASSWORD = "password123"

# --- Configuration for Database, Backups, and Pagination ---
DATABASE_FILE = "pos_system.db"  # Name of your SQLite database file
BACKUP_DIR = "db_backups"  # Directory to store database backups
ITEMS_PER_PAGE = 10  # Number of items (sales, customers, etc.) to display per page in paginated lists

# --- API Key Configuration ---
# Load API keys from environment variable for better security.
# Example: VALID_API_KEYS="key1,key2,anotherkey"
api_keys_str = os.environ.get("VALID_API_KEYS", "YOUR_SUPER_SECRET_API_KEY_12345_DEV_ONLY")
VALID_API_KEYS = set(key.strip() for key in api_keys_str.split(',') if key.strip())  # Create a set of valid keys
if not VALID_API_KEYS or "YOUR_SUPER_SECRET_API_KEY_12345_DEV_ONLY" in VALID_API_KEYS:
    with app.app_context():
        app.logger.warning(
            "SECURITY WARNING: Using default or no API keys. Set the VALID_API_KEYS environment variable for production.")

# --- Logging Configuration ---
# Configure basic logging for the Flask app.
# In production, you'd likely use a more robust logging setup (e.g., logging to a file, using a logging service).
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Backup Directory Creation ---
# Create backup directory if it doesn't exist.
# Uses absolute path based on app.root_path for reliability on server environments.
backup_dir_path = os.path.join(app.root_path, BACKUP_DIR)
if not os.path.exists(backup_dir_path):
    try:
        os.makedirs(backup_dir_path)
        with app.app_context():  # Use Flask's logger after app is initialized
            app.logger.info(f"Created backup directory at: {backup_dir_path}")
    except OSError as e:
        with app.app_context():
            app.logger.error(f"Could not create backup directory {backup_dir_path}: {e}")


# --- Custom Jinja Filter for Datetime Formatting ---
@app.template_filter('format_datetime')
def format_datetime_filter(value, format_str='%Y-%m-%d %I:%M %p'):  # Default format example
    """Formats a datetime string or object into a more readable format."""
    if not value:
        return "N/A"  # Or some other placeholder for None/empty values
    if isinstance(value, str):
        try:
            # Attempt to parse common ISO-like format from database
            dt_obj = datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')  # Adjust if your DB format is different
            return dt_obj.strftime(format_str)
        except ValueError:
            # If parsing fails, return the original string or a placeholder
            app.logger.warning(f"Could not parse datetime string for formatting: {value}")
            return value
    elif isinstance(value, datetime.datetime):
        return value.strftime(format_str)
    return value  # Fallback for other types


# --- Context Processors ---
@app.context_processor
def utility_processor():
    """Injects utility functions and modules into the template context."""
    return {
        'now': datetime.datetime.now,  # Current datetime for use in templates (e.g., footer year)
        'min': min,  # Make min() function available
        'max': max,  # Make max() function available
        'logged_in': session.get('logged_in', False),  # Check login status
        'calendar': calendar  # Make calendar module available (e.g., for month names)
    }


# --- Decorators for Route Protection ---
def login_required(f):
    """Decorator to ensure a user is logged in before accessing a route."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))  # Redirect to login, remembering the intended page
        return f(*args, **kwargs)

    return decorated_function


def require_api_key(f):
    """Decorator to protect API routes with an API key check."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = None
        # Check for API key in headers (common), URL arguments, JSON payload, or form data
        if 'X-API-KEY' in request.headers:
            api_key = request.headers['X-API-KEY']
        elif 'api_key' in request.args:
            api_key = request.args['api_key']
        elif request.is_json and request.json and 'api_key' in request.json:  # Check if request.json is not None
            api_key = request.json.get('api_key')
        elif 'api_key' in request.form:
            api_key = request.form['api_key']

        if not api_key or api_key not in VALID_API_KEYS:
            app.logger.warning(
                f"Unauthorized API access attempt. Key used: {api_key}. Remote IP: {request.remote_addr}")
            return jsonify({"error": "Unauthorized - Invalid or missing API key"}), 401  # HTTP 401 Unauthorized
        return f(*args, **kwargs)

    return decorated_function


# --- Main Application Routes ---

@app.route('/')
@login_required  # Protect the dashboard
def index():
    """Displays the main dashboard if logged in."""
    total_sales_today = 0.0
    total_sales_this_week_actual = 0.0
    current_week_start_display = "N/A"
    current_week_end_display = "N/A"

    try:
        today = datetime.date.today()
        current_week_monday = today - datetime.timedelta(days=today.weekday())  # Monday of current week
        current_week_sunday = current_week_monday + datetime.timedelta(days=6)  # Sunday of current week

        total_sales_today = db.get_total_sales_today_db()
        total_sales_this_week_actual = db.get_total_sales_current_week_db()  # Fetches Mon-Sun total

        # Format dates for display (e.g., "May 05" - "May 11, 2025")
        current_week_start_display = current_week_monday.strftime("%b %d")
        current_week_end_display = current_week_sunday.strftime("%b %d, %Y")

    except Exception as e:
        app.logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        flash("Could not load dashboard data due to a server error.", "error")
        # Defaults are already set above

    return render_template('index.html',
                           title="Dashboard",
                           total_sales_today=total_sales_today,
                           total_sales_this_week=total_sales_this_week_actual,
                           current_week_start_date_display=current_week_start_display,
                           current_week_end_date_display=current_week_end_display)


# --- Login/Logout Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if session.get('logged_in'):  # If already logged in, redirect to dashboard
        return redirect(url_for('index'))

    if request.method == 'POST':
        password_attempt = request.form.get('password')
        # --- INSECURE PASSWORD CHECK ---
        # This is highly insecure and only for demonstration.
        # Implement proper password hashing and user management in a real application.
        if password_attempt == HARDCODED_PASSWORD:
            session['logged_in'] = True  # Mark user as logged in
            session.permanent = True  # Make session last longer (optional, requires app.permanent_session_lifetime)
            app.logger.info(f"Login successful for user. IP: {request.remote_addr}")
            flash("Login successful!", "success")
            next_url = request.args.get('next')  # Redirect to the page user was trying to access
            return redirect(next_url or url_for('index'))
        else:
            app.logger.warning(f"Failed login attempt. IP: {request.remote_addr}")
            flash("Incorrect password. Please try again.", "error")

    return render_template('login.html', title="Login")


@app.route('/logout')
@login_required  # Ensure user is logged in to be able to log out
def logout():
    """Logs the user out by clearing session variables."""
    session.pop('logged_in', None)
    session.pop('current_sale', None)  # Clear any pending sale data on logout
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('login'))


# --- Product Management Routes ---
@app.route('/products')
@login_required
def list_products():
    """Displays a paginated list of all products."""
    # For simplicity, this example doesn't paginate products, but you can add it similarly to sales_history.
    products = db.get_all_products_db()
    return render_template('products/list.html', products=products, title="Manage Products")


@app.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    """Handles adding a new product."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price_str = request.form.get('price', '').strip()

        if not name or not price_str:
            flash("Product Name and Price are required.", "error")
        else:
            try:
                price = float(price_str)
                if price < 0:
                    flash("Price must be a non-negative number.", "error")
                else:
                    product_id = db.add_product_db(name, price)
                    if product_id:
                        flash(f"Product '{name}' added successfully!", "success")
                        return redirect(url_for('list_products'))
                    else:
                        # This case might happen if product name is unique and already exists,
                        # or due to other DB constraints/errors.
                        flash(f"Failed to add product '{name}'. It might already exist or a database error occurred.",
                              "error")
            except ValueError:
                flash("Invalid price format. Please enter a number.", "error")
        # If there was an error, re-render the form with submitted data (if any)
        return render_template('products/add_edit.html', title="Add Product", product=None, form_data=request.form)
    return render_template('products/add_edit.html', title="Add Product", product=None)


@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Handles editing an existing product."""
    product = db.get_product_by_id_db(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('list_products'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price_str = request.form.get('price', '').strip()
        if not name or not price_str:
            flash("Product Name and Price are required.", "error")
        else:
            try:
                price = float(price_str)
                if price < 0:
                    flash("Price must be a non-negative number.", "error")
                else:
                    if db.update_product_db(product_id, name, price):
                        flash(f"Product '{name}' updated successfully!", "success")
                        return redirect(url_for('list_products'))
                    else:
                        flash(
                            f"Failed to update product '{name}'. Name might already exist or a database error occurred.",
                            "error")
            except ValueError:
                flash("Invalid price format. Please enter a number.", "error")
        # Re-render form with current product data on error
        return render_template('products/add_edit.html', title="Edit Product",
                               product=product)  # Pass current product data
    return render_template('products/add_edit.html', title="Edit Product", product=product)


@app.route('/products/delete/<int:product_id>', methods=['POST'])  # Should be POST for destructive action
@login_required
def delete_product(product_id):
    """Handles deleting a product."""
    product = db.get_product_by_id_db(product_id)  # Fetch for flash message
    if not product:
        flash("Product not found.", "error")
    elif db.delete_product_db(product_id):
        flash(f"Product '{product['ProductName']}' deleted successfully!", "success")
    else:
        # This could be due to foreign key constraints (e.g., product is in SaleItems)
        # or other database errors.
        flash(
            f"Failed to delete product '{product['ProductName']}'. It might be part of an existing sale or a database error occurred.",
            "error")
    return redirect(url_for('list_products'))


# --- Customer Management Routes ---
@app.route('/customers')
@app.route('/customers/page/<int:page_num>')
@login_required
def list_customers(page_num=1):
    """Displays a paginated list of all customers."""
    total_customers = db.count_total_customers_db()
    customers_on_page = db.get_customers_paginated_db(page=page_num, per_page=ITEMS_PER_PAGE)

    if not customers_on_page and page_num > 1 and total_customers > 0:  # If page is out of bounds
        flash(f"No customers found on page {page_num}. Showing last available page.", "info")
        last_page = math.ceil(total_customers / ITEMS_PER_PAGE) if total_customers > 0 else 1
        return redirect(url_for('list_customers', page_num=last_page))

    total_pages = math.ceil(total_customers / ITEMS_PER_PAGE) if total_customers > 0 else 0
    return render_template('customers/list.html',
                           customers=customers_on_page, title="Manage Customers",
                           current_page=page_num, total_pages=total_pages,
                           total_items=total_customers, per_page=ITEMS_PER_PAGE)


@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    """Handles adding a new customer."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        address = request.form.get('address', '').strip()

        if not name:
            flash("Customer Name is required.", "error")
        else:
            customer_id = db.add_customer_db(name, contact, address)
            if customer_id:
                flash(f"Customer '{name}' added successfully!", "success")
                return redirect(url_for('list_customers'))
            else:
                flash(f"Failed to add customer '{name}'. Name might already exist or a database error occurred.",
                      "error")
        return render_template('customers/add_edit.html', title="Add Customer", customer=None, form_data=request.form)
    return render_template('customers/add_edit.html', title="Add Customer", customer=None)


@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    """Handles editing an existing customer."""
    customer = db.get_customer_by_id_db(customer_id)
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for('list_customers'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact', '').strip()
        address = request.form.get('address', '').strip()
        if not name:
            flash("Customer Name is required.", "error")
        else:
            if db.update_customer_db(customer_id, name, contact, address):
                flash(f"Customer '{name}' updated successfully!", "success")
                return redirect(url_for('list_customers'))
            else:
                flash(f"Failed to update customer '{name}'. Name might already exist or a database error occurred.",
                      "error")
        return render_template('customers/add_edit.html', title="Edit Customer", customer=customer)
    return render_template('customers/add_edit.html', title="Edit Customer", customer=customer)


@app.route('/customers/delete/<int:customer_id>', methods=['POST'])  # Should be POST
@login_required
def delete_customer(customer_id):
    """Handles deleting a customer."""
    customer = db.get_customer_by_id_db(customer_id)  # Fetch for flash message
    if not customer:
        flash("Customer not found to delete.", "error")
    elif db.delete_customer_db(customer_id):
        flash(f"Customer '{customer['CustomerName']}' deleted successfully!", "success")
    else:
        flash(
            f"Failed to delete customer '{customer['CustomerName']}'. They might be linked to sales or a database error occurred.",
            "error")
    return redirect(url_for('list_customers'))


# --- POS Interface Route ---
@app.route('/pos', methods=['GET', 'POST'])
@login_required
def pos_interface():
    """Point of Sale interface for creating new sales."""
    current_sale = session.get('current_sale', {"items": [], "customer_name": "N/A", "total": 0.0})
    all_products = db.get_all_products_db()
    customers = db.get_all_customers_db()

    # Example: Prioritize some products for quicker access
    prioritized_product_names = ["Refill (20)", "Refill (25)"]
    prioritized_products = [p for p in all_products if p['ProductName'] in prioritized_product_names]
    other_products = [p for p in all_products if p['ProductName'] not in prioritized_product_names]

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_item':
            product_name = request.form.get('product_name')
            quantity_str = request.form.get('quantity', '1')
            try:
                quantity = int(quantity_str)
                if quantity <= 0:
                    flash("Quantity must be positive.", "error")
                else:
                    product = db.get_product_by_name_db(product_name)
                    if product:
                        found = False
                        for item in current_sale["items"]:
                            # Check if item with same name AND price already exists to increment quantity
                            if item["name"] == product_name and item["price"] == product['Price']:
                                item["quantity"] += quantity
                                item["subtotal"] = round(item["quantity"] * item["price"], 2)  # Ensure rounding
                                found = True;
                                break
                        if not found:
                            current_sale["items"].append({
                                "name": product_name, "price": product['Price'],
                                "quantity": quantity, "subtotal": round(product['Price'] * quantity, 2)
                            })
                        current_sale["total"] = round(sum(item['subtotal'] for item in current_sale['items']), 2)
                        flash(f"Added {quantity} x {product_name}.", "info")
                    else:
                        flash(f"Product '{product_name}' not found.", "error")
            except ValueError:
                flash("Invalid quantity.", "error")

        elif action == 'add_custom_item':
            selected_product_name = request.form.get('custom_product_name')  # From select in modal
            manual_product_name = request.form.get('custom_product_name_override')  # From text input in modal

            custom_name_to_use = selected_product_name
            # If "Custom Item/Service" was selected and a manual name was provided, use the manual name.
            if selected_product_name == 'Custom Item/Service':
                if manual_product_name and manual_product_name.strip():
                    custom_name_to_use = manual_product_name.strip()
                else:
                    custom_name_to_use = "Custom Item"  # Default if no manual name typed

            custom_price_str = request.form.get('custom_price')
            custom_quantity_str = request.form.get('custom_quantity', '1')
            try:
                custom_price = round(float(custom_price_str if custom_price_str else 0), 2)
                custom_quantity = int(custom_quantity_str if custom_quantity_str else 1)
                if custom_price < 0:
                    flash("Custom price must be non-negative.", "error")
                elif custom_quantity <= 0:
                    flash("Custom quantity must be positive.", "error")
                else:
                    found = False
                    for item in current_sale["items"]:
                        if item["name"] == custom_name_to_use and item["price"] == custom_price:
                            item["quantity"] += custom_quantity
                            item["subtotal"] = round(item["quantity"] * item["price"], 2)
                            found = True;
                            break
                    if not found:
                        current_sale["items"].append({
                            "name": custom_name_to_use, "price": custom_price,
                            "quantity": custom_quantity, "subtotal": round(custom_price * custom_quantity, 2)
                        })
                    current_sale["total"] = round(sum(item['subtotal'] for item in current_sale['items']), 2)
                    flash(f"Added {custom_quantity} x {custom_name_to_use}.", "info")
            except (ValueError, TypeError):
                flash("Invalid custom price or quantity.", "error")

        elif action == 'set_customer':
            customer_name_from_form = request.form.get('customer_name_select', "N/A").strip()
            current_sale["customer_name"] = customer_name_from_form or "N/A"  # Ensure it's not empty string
            flash(f"Customer set to '{current_sale['customer_name']}'.", "info")

        elif action == 'remove_item':
            item_name_to_remove = request.form.get('item_name')
            item_price_to_remove_str = request.form.get('item_price')
            try:
                item_price_to_remove = float(item_price_to_remove_str)  # Ensure price is float for comparison
                initial_length = len(current_sale["items"])
                # Remove item matching both name and price (to handle items with same name but different custom prices)
                current_sale["items"] = [
                    item for item in current_sale["items"]
                    if not (item["name"] == item_name_to_remove and math.isclose(item["price"], item_price_to_remove))
                ]
                if len(current_sale["items"]) < initial_length:
                    current_sale["total"] = round(sum(item['subtotal'] for item in current_sale['items']), 2)
                    flash(f"Removed {item_name_to_remove} from sale.", "info")
                else:
                    flash(f"Could not find exact item '{item_name_to_remove}' to remove.", "warning")
            except (ValueError, TypeError):
                flash(f"Error removing item '{item_name_to_remove}'. Invalid data.", "error")

        elif action == 'increase_qty' or action == 'decrease_qty':
            item_name = request.form.get('item_name')
            item_price_str = request.form.get('item_price')
            try:
                item_price = float(item_price_str)
                item_found_for_qty_adj = False
                for i, item in enumerate(current_sale["items"]):
                    if item["name"] == item_name and math.isclose(item["price"], item_price):
                        if action == 'increase_qty':
                            item["quantity"] += 1
                        elif action == 'decrease_qty':
                            item["quantity"] -= 1

                        if item["quantity"] <= 0:
                            current_sale["items"].pop(i)  # Remove item if quantity is zero or less
                            flash(f"Removed {item_name}.", "info")
                        else:
                            item["subtotal"] = round(item["quantity"] * item["price"], 2)
                            flash(f"Adjusted quantity for {item_name}.", "info")

                        item_found_for_qty_adj = True;
                        break
                if item_found_for_qty_adj:
                    current_sale["total"] = round(sum(it['subtotal'] for it in current_sale['items']), 2)
                else:
                    flash(f"Could not find '{item_name}' to adjust quantity.", "warning")
            except (ValueError, TypeError):
                flash(f"Error adjusting quantity for '{item_name}'. Invalid data.", "error")

        elif action == 'clear_sale':
            session.pop('current_sale', None)  # Clear the sale from session
            flash("Sale cleared.", "info")
            return redirect(url_for('pos_interface'))  # Redirect to refresh POS view

        elif action == 'finalize_sale':
            if not current_sale["items"]:
                flash("Cannot finalize an empty sale.", "error")
            else:
                sale_id = db.create_sale_db(customer_name=current_sale["customer_name"])
                if sale_id:
                    all_items_added = True
                    for item in current_sale["items"]:
                        if not db.add_sale_item_db(sale_id, item["name"], item["quantity"], item["price"]):
                            all_items_added = False
                            flash(
                                f"Failed to add item '{item['name']}'. Sale partially created (ID: {sale_id}). Please review.",
                                "error")
                            # Do not break here, attempt to save other items if possible, or handle as a transaction failure.
                            # For simplicity, we'll let it continue and flag the error.

                    if all_items_added:
                        # Update the final total in the Sales table
                        conn = None
                        try:
                            conn = db.get_db_connection()
                            cursor = conn.cursor()
                            # Recalculate total from DB to ensure accuracy
                            cursor.execute("SELECT SUM(Subtotal) FROM SaleItems WHERE SaleID = ?", (sale_id,))
                            final_total_row = cursor.fetchone()
                            final_total = final_total_row[0] if final_total_row and final_total_row[
                                0] is not None else 0.0

                            cursor.execute("UPDATE Sales SET TotalAmount = ? WHERE SaleID = ?", (final_total, sale_id))
                            conn.commit()
                            app.logger.info(f"Final total {final_total} updated for SaleID {sale_id}")
                            flash(f"Sale #{sale_id} finalized successfully for ₱{final_total:.2f}!", "success")
                            session.pop('current_sale', None)  # Clear sale from session on success
                            return redirect(url_for('view_sale', sale_id=sale_id))
                        except sqlite3.Error as e:  # Catch specific sqlite3 error from the standard library
                            app.logger.error(f"DB Error updating final total for SaleID {sale_id}: {e}", exc_info=True)
                            flash(f"DB Error updating final total for Sale #{sale_id}. Items may have been saved.",
                                  "error")
                            # current_sale remains in session for potential correction
                        finally:
                            if conn: conn.close()
                    else:
                        # If not all items were added, it's a partial success/failure.
                        # The current_sale remains in session for the user to see what might have failed.
                        flash(
                            f"Sale #{sale_id} created, but some items could not be saved. Please review the current sale.",
                            "warning")
                else:
                    flash("Failed to create sale record in database.", "error")

        session['current_sale'] = current_sale  # Save changes to session after any POST action
        return redirect(url_for('pos_interface'))  # Redirect to refresh POS view after any POST

    return render_template('pos/interface.html',
                           title="New Sale",
                           prioritized_products=prioritized_products,
                           other_products=other_products,
                           customers=customers,
                           current_sale_items=current_sale.get("items", []),
                           current_customer=current_sale.get("customer_name", "N/A"),
                           current_total=current_sale.get("total", 0.0))


# --- Sales History Routes ---
@app.route('/sales')
@app.route('/sales/page/<int:page_num>')
@login_required
def list_sales(page_num=1):
    """Displays paginated sales history, optionally filtered by date."""
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    date_filter_error = None
    start_date, end_date = None, None

    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            date_filter_error = "Invalid start date format (YYYY-MM-DD)."
    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            date_filter_error = (
                                    date_filter_error + " " if date_filter_error else "") + "Invalid end date format (YYYY-MM-DD)."

    if start_date and end_date and start_date > end_date:
        date_filter_error = (
                                date_filter_error + " " if date_filter_error else "") + "Start date cannot be after end date."

    if date_filter_error:
        flash(date_filter_error, "error")
        # Optionally clear dates if invalid to show all sales
        start_date, end_date = None, None
        start_date_str, end_date_str = None, None  # For repopulating form

    # Convert valid date objects back to strings for DB query if needed, or pass date objects
    # db_operations expects string format 'YYYY-MM-DD'
    db_start_date = start_date.strftime('%Y-%m-%d') if start_date else None
    db_end_date = end_date.strftime('%Y-%m-%d') if end_date else None

    app.logger.info(f"Sales History: Filtering from '{db_start_date}' to '{db_end_date}', page {page_num}")

    total_sales = db.count_total_sales_db(start_date=db_start_date, end_date=db_end_date)
    sales_on_page = db.get_sales_paginated_db(
        page=page_num,
        per_page=ITEMS_PER_PAGE,
        start_date=db_start_date,
        end_date=db_end_date
    )

    if not sales_on_page and page_num > 1 and total_sales > 0:
        flash(f"No sales found on page {page_num} for the selected filter. Showing last available page.", "info")
        last_page = math.ceil(total_sales / ITEMS_PER_PAGE) if total_sales > 0 else 1
        return redirect(url_for('list_sales', page_num=last_page, start_date=start_date_str, end_date=end_date_str))

    total_pages = math.ceil(total_sales / ITEMS_PER_PAGE) if total_sales > 0 else 0

    return render_template('sales/list.html',
                           sales=sales_on_page, title="Sales History",
                           current_page=page_num, total_pages=total_pages,
                           total_items=total_sales, per_page=ITEMS_PER_PAGE
                           # start_date_str and end_date_str will be available via request.args in template
                           )


@app.route('/sales/<int:sale_id>')
@login_required
def view_sale(sale_id):
    """Displays details for a specific sale."""
    sale_details = db.get_sale_details_db(sale_id)
    if not sale_details:
        flash(f"Sale with ID {sale_id} not found.", "error")
        return redirect(url_for('list_sales'))  # Consider redirecting back with filters if coming from filtered view
    return render_template('sales/details.html',
                           sale=sale_details["info"],
                           items=sale_details["items"],
                           title=f"Sale #{sale_id} Details")


@app.route('/sales/delete/<int:sale_id>', methods=['POST'])
@login_required
def delete_sale(sale_id):
    """Handles deleting a sale record."""
    page = request.form.get('page', 1, type=int)
    start_date = request.form.get('start_date')  # Preserve filter
    end_date = request.form.get('end_date')  # Preserve filter

    if db.delete_sale_db(sale_id):
        flash(f"Sale #{sale_id} deleted successfully!", "success")
    else:
        flash(f"Failed to delete Sale #{sale_id}. It might have already been deleted or a database error occurred.",
              "error")
    return redirect(url_for('list_sales', page_num=page, start_date=start_date, end_date=end_date))


# NEW ROUTE for viewing all receipts in a date range
@app.route('/sales/receipts_for_range')
@login_required
def view_receipts_for_range():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        flash("Both start date and end date are required to view receipts for a range.", "error")
        return redirect(url_for('list_sales'))

    try:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD.", "error")
        return redirect(url_for('list_sales'))

    if start_date > end_date:
        flash("Start date cannot be after end date.", "error")
        return redirect(url_for('list_sales'))

    # Fetch all sales within the date range (not paginated)
    sales_in_range_summary = db.get_sales_in_range_summary_db(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    all_sale_details = []
    if sales_in_range_summary:
        for sale_summary in sales_in_range_summary:
            details = db.get_sale_details_db(sale_summary['SaleID'])  # Assumes SaleID is the key
            if details:
                all_sale_details.append(details)

    if not all_sale_details:
        flash(f"No sales found between {start_date_str} and {end_date_str}.", "info")
        # Optionally, still render the page with a "no sales" message
        # Or redirect back: return redirect(url_for('list_sales', start_date=start_date_str, end_date=end_date_str))

    return render_template('sales/receipts_range.html',
                           title=f"Receipts from {start_date_str} to {end_date_str}",
                           all_sale_details=all_sale_details,
                           start_date_str=start_date_str,  # Pass dates back for display or "Back" button
                           end_date_str=end_date_str)


# --- Reports Routes ---
@app.route('/reports/weekly')
@login_required
def weekly_reports_page():
    """Generates and displays the weekly sales report."""
    page_error_message = None
    chart_labels_for_template = []
    chart_data_for_template = []
    total_sales_for_period = 0.0
    items_summary_for_template = []

    try:
        today = datetime.date.today()
        week_start_date = today - datetime.timedelta(days=today.weekday())
        week_end_date = week_start_date + datetime.timedelta(days=6)

        chart_info = db.get_weekly_sales_chart_data_db(week_start_date, week_end_date)
        items_summary = db.get_items_sold_summary_for_period_db(week_start_date, week_end_date)

        # Robustly extract data from chart_info
        if chart_info and isinstance(chart_info, dict):
            if chart_info.get('error'):
                app.logger.error(f"DB Error (Weekly Chart): {chart_info.get('error')}")
                page_error_message = "Error loading weekly chart data from database."

            raw_labels = chart_info.get('labels', [])
            chart_labels_for_template = [str(lbl) for lbl in raw_labels] if isinstance(raw_labels, list) else []
            if not isinstance(raw_labels, list): app.logger.warning(f"Weekly chart labels not a list: {raw_labels}")

            raw_data = chart_info.get('data', [])
            try:
                chart_data_for_template = [float(d) for d in raw_data] if isinstance(raw_data, list) else []
            except (ValueError, TypeError):
                app.logger.error(f"Weekly chart data contained non-numeric values: {raw_data}")
                chart_data_for_template = []  # Default to empty if conversion fails
                if not page_error_message: page_error_message = "Weekly chart data format error."
            if not isinstance(raw_data, list): app.logger.warning(f"Weekly chart data not a list: {raw_data}")

            total_sales_for_period = float(chart_info.get('total', 0.0))
        else:
            app.logger.error(f"Invalid chart_info structure for weekly report: {chart_info}")
            page_error_message = "Failed to retrieve weekly chart data."
            # Ensure defaults if chart_info is bad
            chart_labels_for_template = []
            chart_data_for_template = []
            total_sales_for_period = 0.0

        # Handle items_summary
        if items_summary is None:
            items_summary_for_template = []
            if not page_error_message: page_error_message = "Could not load weekly item summary."
        elif isinstance(items_summary, list):
            items_summary_for_template = items_summary
        else:
            app.logger.error(f"Invalid items_summary for weekly report: {items_summary}")
            items_summary_for_template = []
            if not page_error_message: page_error_message = "Item summary format error (weekly)."

        app.logger.info(
            f"WEEKLY REPORT PREPARED - Labels: {chart_labels_for_template}, Data: {chart_data_for_template}, Error: {page_error_message}")
        return render_template('reports.html',
                               title="Weekly Sales Report",
                               week_start_date=week_start_date.strftime('%Y-%m-%d'),
                               week_end_date=week_end_date.strftime('%Y-%m-%d'),
                               total_sales_for_chart_week=total_sales_for_period,
                               chart_labels=chart_labels_for_template,
                               chart_data=chart_data_for_template,
                               items_sold_summary=items_summary_for_template,
                               error_message=page_error_message)
    except Exception as e:
        app.logger.error(f"Critical error in weekly_reports_page: {e}", exc_info=True)
        flash("An unexpected error occurred generating the weekly report.", "error")
        return render_template('reports.html', title="Weekly Sales Report",
                               error_message="Unexpected error loading report data.")


@app.route('/reports/monthly')
@app.route('/reports/monthly/<int:year>/<int:month>')
@login_required
def monthly_reports_page(year=None, month=None):
    """Generates and displays the monthly sales report."""
    page_error_message = None
    today = datetime.date.today()
    chart_labels_for_template = []
    chart_data_for_template = []
    total_sales_for_month_val = 0.0
    items_summary_for_template = []
    month_name_str_val = ""

    try:
        if year is None: year = today.year
        if month is None: month = today.month

        if not (1 <= month <= 12):
            flash("Invalid month. Defaulting to current month.", "warning")
            year, month = today.year, today.month
        if not (today.year - 50 <= year <= today.year + 5):  # Basic year range validation
            flash("Invalid year. Defaulting to current month.", "warning")
            year, month = today.year, today.month

        month_name_str_val = calendar.month_name[month]

        chart_info = db.get_monthly_sales_chart_data_db(year, month)
        items_summary = db.get_items_sold_summary_for_month_db(year, month)

        if chart_info and isinstance(chart_info, dict):
            if chart_info.get('error'):
                app.logger.error(f"DB Error (Monthly Chart for {year}-{month}): {chart_info.get('error')}")
                page_error_message = f"Error loading chart data for {month_name_str_val} {year}."

            raw_labels = chart_info.get('labels', [])
            chart_labels_for_template = [str(lbl) for lbl in raw_labels] if isinstance(raw_labels, list) else []
            if not isinstance(raw_labels, list): app.logger.warning(f"Monthly chart labels not a list: {raw_labels}")

            raw_data = chart_info.get('data', [])
            try:
                chart_data_for_template = [float(d) for d in raw_data] if isinstance(raw_data, list) else []
            except (ValueError, TypeError):
                app.logger.error(f"Monthly chart data non-numeric: {raw_data}")
                chart_data_for_template = []
                if not page_error_message: page_error_message = f"Chart data format error for {month_name_str_val} {year}."
            if not isinstance(raw_data, list): app.logger.warning(f"Monthly chart data not a list: {raw_data}")

            total_sales_for_month_val = float(chart_info.get('total', 0.0))
            month_name_str_val = chart_info.get('month_name', month_name_str_val)
        else:
            app.logger.error(f"Invalid chart_info for monthly report ({year}-{month}): {chart_info}")
            page_error_message = f"Failed to retrieve chart data for {month_name_str_val} {year}."
            # Ensure defaults if chart_info is bad
            chart_labels_for_template = []
            chart_data_for_template = []
            total_sales_for_month_val = 0.0

        if items_summary is None:
            items_summary_for_template = []
            if not page_error_message: page_error_message = f"Could not load item summary for {month_name_str_val} {year}."
        elif isinstance(items_summary, list):
            items_summary_for_template = items_summary
        else:
            app.logger.error(f"Invalid items_summary for monthly report ({year}-{month}): {items_summary}")
            items_summary_for_template = []
            if not page_error_message: page_error_message = f"Item summary format error for {month_name_str_val} {year}."

        current_month_date = datetime.date(year, month, 1)
        prev_month_date = current_month_date - relativedelta(months=1)
        next_month_date = current_month_date + relativedelta(months=1)

        app.logger.info(
            f"MONTHLY REPORT ({year}-{month}) - Labels: {chart_labels_for_template}, Data: {chart_data_for_template}, Error: {page_error_message}")
        return render_template('monthly_report.html',
                               title=f"Monthly Sales Report - {month_name_str_val} {year}",
                               report_year=year, report_month_num=month, report_month_name=month_name_str_val,
                               total_sales_for_month=total_sales_for_month_val,
                               chart_labels=chart_labels_for_template, chart_data=chart_data_for_template,
                               items_sold_summary=items_summary_for_template,
                               prev_month_year=prev_month_date.year, prev_month_num=prev_month_date.month,
                               next_month_year=next_month_date.year, next_month_num=next_month_date.month,
                               current_year=today.year, current_month=today.month,
                               error_message=page_error_message)
    except ValueError as ve:
        app.logger.error(f"Date error in monthly_reports_page ({year}-{month}): {ve}", exc_info=True)
        flash("Invalid date parameters for the monthly report.", "error")
        return redirect(url_for('monthly_reports_page'))
    except Exception as e:
        app.logger.error(f"Critical error in monthly_reports_page ({year}-{month}): {e}", exc_info=True)
        flash("An unexpected error occurred generating the monthly report.", "error")
        # Fallback rendering for monthly report on critical error
        today_fallback = datetime.date.today()
        prev_month_fallback = today_fallback - relativedelta(months=1)
        next_month_fallback = today_fallback + relativedelta(months=1)
        return render_template('monthly_report.html',
                               title="Monthly Sales Report",
                               error_message="Unexpected error loading report data.",
                               report_year=today_fallback.year, report_month_num=today_fallback.month,
                               report_month_name=calendar.month_name[today_fallback.month],
                               total_sales_for_month=0.0, chart_labels=[], chart_data=[], items_sold_summary=[],
                               prev_month_year=prev_month_fallback.year, prev_month_num=prev_month_fallback.month,
                               next_month_year=next_month_fallback.year, next_month_num=next_month_fallback.month,
                               current_year=today_fallback.year, current_month=today_fallback.month
                               )


# --- Admin Routes ---
@app.route('/admin')
@login_required
def admin_index():
    """Displays the main admin panel page."""
    return render_template('admin/index.html', title="Admin Panel", BACKUP_DIR=BACKUP_DIR)


@app.route('/admin/backup_database')
@login_required
def backup_database():
    """Handles creating a backup of the database."""
    try:
        # Construct paths relative to the application root
        current_db_path = os.path.join(app.root_path, DATABASE_FILE)
        backup_db_dir_abs = os.path.join(app.root_path, BACKUP_DIR)  # Absolute path for makedirs

        if not os.path.exists(backup_db_dir_abs):
            os.makedirs(backup_db_dir_abs)
            app.logger.info(f"Created backup directory: {backup_db_dir_abs}")

        if os.path.exists(current_db_path):
            original_name, original_ext = os.path.splitext(DATABASE_FILE)
            backup_filename = f"{original_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db.bak"  # Consistent backup extension
            backup_path_abs = os.path.join(backup_db_dir_abs, backup_filename)

            shutil.copy2(current_db_path, backup_path_abs)
            flash(f'Successfully backed up database to {backup_filename} in {BACKUP_DIR}/', 'success')
            app.logger.info(f"Database backed up successfully to {backup_path_abs}")
        else:
            flash(f'Database file "{DATABASE_FILE}" not found. Cannot perform backup.', 'error');
            app.logger.error(f"DB file not found at {current_db_path} for backup.")
    except Exception as e:
        flash(f'Error during database backup: {str(e)}', 'error');
        app.logger.error(f"DB Backup Error: {e}", exc_info=True)
    return redirect(url_for('admin_index'))


@app.route('/admin/restore_database', methods=['GET', 'POST'])
@login_required
def restore_database():
    """Handles restoring the database from an uploaded file."""
    if request.method == 'POST':
        if 'database_file' not in request.files:
            flash('No file part selected for restore.', 'error');
            return redirect(request.url)
        file = request.files['database_file']
        if file.filename == '':
            flash('No file selected for restore.', 'error');
            return redirect(request.url)

        if file and (file.filename.endswith('.db') or file.filename.endswith('.sqlite') or file.filename.endswith(
                '.sqlite3')):
            filename = secure_filename(file.filename)  # Secure the filename
            try:
                current_db_path = os.path.join(app.root_path, DATABASE_FILE)
                backup_db_dir_abs = os.path.join(app.root_path, BACKUP_DIR)

                if not os.path.exists(backup_db_dir_abs):
                    os.makedirs(backup_db_dir_abs)
                    app.logger.info(f"Created backup directory for pre-restore backup: {backup_db_dir_abs}")

                # Backup current database before restoring
                if os.path.exists(current_db_path):
                    original_name, original_ext = os.path.splitext(DATABASE_FILE)
                    pre_restore_backup_filename = f"{original_name}_before_restore_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.db.bak"
                    pre_restore_backup_path = os.path.join(backup_db_dir_abs, pre_restore_backup_filename)
                    shutil.copy2(current_db_path, pre_restore_backup_path)
                    flash(f'Backed up current database to {pre_restore_backup_filename} before restoring.', 'info');
                    app.logger.info(f"Pre-restore DB backup created at {pre_restore_backup_path}")

                # Save the uploaded file, replacing the current database
                file.save(current_db_path)
                flash(f'Database successfully restored from {filename}! Please verify the data.', 'success');
                flash(
                    'It is recommended to RESTART the application for changes to take full effect, especially if the database schema changed.',
                    'warning');
                app.logger.info(f"Database restored from uploaded file: {filename}")
                return redirect(url_for('admin_index'))
            except Exception as e:
                flash(f'Error during database restore: {str(e)}', 'error');
                app.logger.error(f"DB Restore Error: {e}", exc_info=True);
        else:
            flash('Invalid file type. Only .db, .sqlite, or .sqlite3 files are allowed for restore.', 'error');
        return redirect(request.url)
    return render_template('admin/restore_db.html', title="Restore Database", BACKUP_DIR=BACKUP_DIR)


# --- API Endpoints ---
@app.route('/api/products', methods=['GET'])
@require_api_key
def api_get_products():
    """API endpoint to get all products."""
    try:
        products = db.get_all_products_db();
        # Convert sqlite3.Row objects to dictionaries for JSON serialization
        products_list = [dict(p) for p in products] if products else [];
        return jsonify(products_list)
    except Exception as e:
        app.logger.error(f"API Error getting products: {e}", exc_info=True)
        return jsonify({"error": "Internal server error fetching products"}), 500


@app.route('/api/products/<string:name>', methods=['GET'])
@require_api_key
def api_get_product_by_name(name):
    """API endpoint to get a specific product by name."""
    try:
        product = db.get_product_by_name_db(name);
        if product:
            return jsonify(dict(product))  # Convert sqlite3.Row to dict
        return jsonify({"error": "Product not found"}), 404  # HTTP 404 Not Found
    except Exception as e:
        app.logger.error(f"API Error getting product by name '{name}': {e}", exc_info=True)
        return jsonify({"error": "Internal server error fetching product"}), 500


@app.route('/api/sales', methods=['POST'])
@require_api_key
def api_sync_sale():
    """API endpoint to create/synchronize a new sale."""
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400  # HTTP 400 Bad Request
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided in JSON payload"}), 400

    # Validate required fields in the JSON payload
    if 'items' not in data or not isinstance(data['items'], list) or not data['items']:
        return jsonify({"error": "Missing or invalid 'items' list. Must be a non-empty list of sale items."}), 400

    customer_name = data.get('customer_name', 'N/A')  # Default to 'N/A' if not provided
    items_to_sync = data['items']
    sale_id = None  # Initialize sale_id

    try:
        sale_id = db.create_sale_db(customer_name=customer_name)
        if not sale_id:
            app.logger.error("API Sync Error: Failed to create sale record in database.")
            return jsonify({"error": "Failed to create sale record on server"}), 500  # HTTP 500 Internal Server Error

        # Process each item in the sale
        for item_data in items_to_sync:
            name = item_data.get('name')
            qty_str = item_data.get('quantity')
            price_str = item_data.get('price_at_sale')  # Price at the time of sale

            # Basic validation for each item's data
            if not all([name, qty_str is not None, price_str is not None]):
                app.logger.error(
                    f"API Sync Error: Invalid item data for SaleID {sale_id}: {item_data}. Skipping item.");
                continue  # Skip this item and proceed with others
            try:
                qty = int(qty_str)
                price = float(price_str)
                if qty <= 0 or price < 0:
                    app.logger.error(
                        f"API Sync Error: Invalid quantity/price for item '{name}' in SaleID {sale_id}. Skipping item.");
                    continue
                if not db.add_sale_item_db(sale_id, name, qty, price):
                    app.logger.error(f"API Sync Error: Failed to add item '{name}' to SaleID {sale_id} in DB.")
            except (ValueError, TypeError):
                app.logger.error(
                    f"API Sync Error: Invalid number format for quantity/price of item '{name}' in SaleID {sale_id}. Skipping item.");
                continue

        # After adding all items, update the final total amount in the Sales table
        conn = None
        try:
            conn = db.get_db_connection()
            cursor = conn.cursor()
            # Recalculate total from SaleItems table for accuracy
            cursor.execute("SELECT SUM(Subtotal) FROM SaleItems WHERE SaleID = ?", (sale_id,))
            db_total_row = cursor.fetchone()
            db_total = db_total_row[0] if db_total_row and db_total_row[0] is not None else 0.0

            cursor.execute("UPDATE Sales SET TotalAmount = ? WHERE SaleID = ?", (db_total, sale_id))
            conn.commit()
            app.logger.info(f"API Sync: Updated final total for SaleID {sale_id} to {db_total:.2f}")
        except sqlite3.Error as e:  # Catch specific sqlite3 error from the standard library
            app.logger.error(f"API Sync Error: Failed to update final total for SaleID {sale_id}: {e}", exc_info=True)
            # Even if total update fails, items might have been added.
            return jsonify(
                {"error": "Sale items may have been added but failed to update final total", "sale_id": sale_id}), 500
        finally:
            if conn: conn.close()

        return jsonify({"message": "Sale synchronized successfully", "sale_id": sale_id,
                        "total_amount_synced": round(db_total, 2)}), 201  # HTTP 201 Created

    except Exception as e:  # Catch any other unexpected errors during sale processing
        app.logger.error(f"API Sync Error: Unexpected error processing sale: {e}", exc_info=True)
        error_response = {"error": "An unexpected error occurred on the server"}
        if sale_id:  # If sale record was created before the error
            error_response["sale_id_created_but_incomplete"] = sale_id
        return jsonify(error_response), 500


# --- Main Execution Block ---
if __name__ == '__main__':
    # This block is typically used for local development.
    # For production, a WSGI server like Gunicorn or uWSGI is recommended.
    print("-" * 68);
    print("SEASIDE POS System Starting...")
    print(
        f"Database File: '{os.path.abspath(DATABASE_FILE)}'. Run 'python database_setup.py' if needed for initial setup.")
    print(f"Backup Directory: '{os.path.abspath(backup_dir_path)}'.")
    print(f"Application running on: http://127.0.0.1:5000 (Press CTRL+C to quit)");
    print("-" * 68)
    app.run(debug=True)  # debug=True is for development only, set to False in production.
