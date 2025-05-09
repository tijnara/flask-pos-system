# app.py
# Description: The main Flask application file, configured for deployment.

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session  # Added session
import db_operations as db
import datetime
import os
import shutil
from werkzeug.utils import secure_filename
import math
import logging
from functools import wraps  # For login_required decorator

app = Flask(__name__)

# --- IMPORTANT: Secret Key Configuration ---
# MUST be set to a strong, random, secret value for sessions to be secure.
# Load from environment variable in production!
app.secret_key = os.environ.get("SECRET_KEY", "a_default_development_secret_key_123!@#")
if app.secret_key == "a_default_development_secret_key_123!@#" and os.environ.get("FLASK_ENV") != "development":
    # Use app.logger which is available after app is created
    with app.app_context():
        app.logger.warning(
            "SECURITY WARNING: Using default SECRET_KEY. Set the SECRET_KEY environment variable in production.")
# --- End Secret Key Configuration ---


# --- Hardcoded Password (INSECURE - FOR DEMO ONLY) ---
# Replace this with a proper user/password system in a real app
HARDCODED_PASSWORD = "password123"
# --- End Hardcoded Password ---


# --- Configuration for Database and Backups ---
DATABASE_FILE = "pos_system.db"
BACKUP_DIR = "db_backups"
ITEMS_PER_PAGE = 10
api_keys_str = os.environ.get("VALID_API_KEYS", "YOUR_SUPER_SECRET_API_KEY_12345")  # Default only for testing
VALID_API_KEYS = set(key.strip() for key in api_keys_str.split(',') if key.strip())
# Log warning if default/no API key is used
if not VALID_API_KEYS or "YOUR_SUPER_SECRET_API_KEY_12345" in VALID_API_KEYS:
    with app.app_context():
        app.logger.warning(
            "SECURITY WARNING: Using default or no API keys. Set the VALID_API_KEYS environment variable.")

# Configure basic logging for the Flask app itself
# Logs will go to the console where the app is running or captured by the server (like PythonAnywhere).
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create backup directory if it doesn't exist
# Use absolute path based on app.root_path for reliability on server
backup_dir_path = os.path.join(app.root_path, BACKUP_DIR)
if not os.path.exists(backup_dir_path):
    try:
        os.makedirs(backup_dir_path)
        # Use Flask's built-in logger after app is initialized
        with app.app_context():
            app.logger.info(f"Created backup directory at: {backup_dir_path}")
    except OSError as e:
        # Use Flask's logger here too
        with app.app_context():
            app.logger.error(f"Could not create backup directory {backup_dir_path}: {e}")


# --- Context Processors ---
@app.context_processor
def utility_processor():
    """Injects utility functions into the template context."""
    # Make the 'now' function (for local time), 'min', and 'max' functions available in templates
    return {'now': datetime.datetime.now,
            'min': min,
            'max': max,
            'logged_in': session.get('logged_in', False)}  # Make login status available


# --- Login Required Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))  # Redirect to login, remember where user was going
        return f(*args, **kwargs)

    return decorated_function


# --- API Key Decorator ---
def require_api_key(f):
    """Decorator to protect API routes with a simple key check."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = None
        # Check for key in headers (common practice) or request data/args
        if 'X-API-KEY' in request.headers:
            api_key = request.headers['X-API-KEY']
        elif 'api_key' in request.args:
            api_key = request.args['api_key']
        elif request.is_json and 'api_key' in request.json:
            api_key = request.json['api_key']
        elif 'api_key' in request.form:
            api_key = request.form['api_key']
        if not api_key or api_key not in VALID_API_KEYS:
            app.logger.warning(f"Unauthorized API access attempt. Key used: {api_key}")
            return jsonify({"error": "Unauthorized - Invalid or missing API key"}), 401
        return f(*args, **kwargs)

    return decorated_function


# --- Main Routes ---
@app.route('/')
def index():
    """Displays dashboard if logged in, otherwise login page."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))  # Go to login page if not logged in

    # If logged in, show dashboard
    try:
        total_sales_today = db.get_total_sales_today_db()
        total_sales_weekly = db.get_total_sales_current_week_db()
    except Exception as e:
        app.logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        flash("Could not load dashboard data.", "error")
        total_sales_today = 0.0
        total_sales_weekly = 0.0

    return render_template('index.html',
                           title="POS Home / Dashboard",
                           total_sales_today=total_sales_today,
                           total_sales_weekly=total_sales_weekly)


# --- Login/Logout Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if session.get('logged_in'):
        return redirect(url_for('index'))  # Already logged in, go to dashboard

    if request.method == 'POST':
        password_attempt = request.form.get('password')
        # --- INSECURE PASSWORD CHECK ---
        if password_attempt == HARDCODED_PASSWORD:
            session['logged_in'] = True  # Mark user as logged in
            session.permanent = True  # Make session last longer (optional)
            app.logger.info("Login successful.")
            flash("Login successful!", "success")
            # Redirect to the page user was trying to access, or dashboard
            next_url = request.args.get('next')
            return redirect(next_url or url_for('index'))
        else:
            app.logger.warning("Failed login attempt.")
            flash("Incorrect password.", "error")

    # For GET request or failed POST, show login page
    return render_template('login.html', title="Login")


@app.route('/logout')
def logout():
    """Logs the user out."""
    session.pop('logged_in', None)  # Remove logged_in status from session
    session.pop('current_sale', None)  # Also clear any pending sale on logout
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


# --- Protected Routes ---
# Apply the @login_required decorator to all routes needing protection

@app.route('/products')
@login_required
def list_products():
    products = db.get_all_products_db()
    return render_template('products/list.html', products=products, title="Manage Products")


@app.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    # ... (keep existing add_product logic) ...
    if request.method == 'POST':
        name = request.form.get('name')
        price_str = request.form.get('price')
        if not name or not price_str:
            flash("Product Name and Price are required.", "error")
            return render_template('products/add_edit.html', title="Add Product", product=None, form_data=request.form)
        try:
            price = float(price_str)
            if price < 0:
                flash("Price must be a non-negative number.", "error")
                return render_template('products/add_edit.html', title="Add Product", product=None,
                                       form_data=request.form)
        except ValueError:
            flash("Invalid price format. Please enter a number.", "error")
            return render_template('products/add_edit.html', title="Add Product", product=None, form_data=request.form)
        product_id = db.add_product_db(name, price)
        if product_id:
            flash(f"Product '{name}' added successfully!", "success")
            return redirect(url_for('list_products'))
        else:
            flash(f"Failed to add product '{name}'. It might already exist or there was a database error.", "error")
            return render_template('products/add_edit.html', title="Add Product", product=None, form_data=request.form)
    return render_template('products/add_edit.html', title="Add Product", product=None)


@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    # ... (keep existing edit_product logic) ...
    product = db.get_product_by_id_db(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('list_products'))
    if request.method == 'POST':
        name = request.form.get('name')
        price_str = request.form.get('price')
        if not name or not price_str:
            flash("Product Name and Price are required.", "error")
            return render_template('products/add_edit.html', title="Edit Product", product=product)
        try:
            price = float(price_str)
            if price < 0:
                flash("Price must be a non-negative number.", "error")
                return render_template('products/add_edit.html', title="Edit Product", product=product)
        except ValueError:
            flash("Invalid price format. Please enter a number.", "error")
            return render_template('products/add_edit.html', title="Edit Product", product=product)
        if db.update_product_db(product_id, name, price):
            flash(f"Product '{name}' updated successfully!", "success")
            return redirect(url_for('list_products'))
        else:
            flash(f"Failed to update product '{name}'. Name might already exist or database error.", "error")
            return render_template('products/add_edit.html', title="Edit Product", product=product)
    return render_template('products/add_edit.html', title="Edit Product", product=product)


@app.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    # ... (keep existing delete_product logic) ...
    product = db.get_product_by_id_db(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('list_products'))
    if db.delete_product_db(product_id):
        flash(f"Product '{product['ProductName']}' deleted successfully!", "success")
    else:
        flash(f"Failed to delete product '{product['ProductName']}'. It might be part of a sale.", "error")
    return redirect(url_for('list_products'))


@app.route('/customers')
@app.route('/customers/page/<int:page_num>')
@login_required
def list_customers(page_num=1):
    # ... (keep existing list_customers logic) ...
    total_customers = db.count_total_customers_db()
    customers_on_page = db.get_customers_paginated_db(page=page_num, per_page=ITEMS_PER_PAGE)
    if not customers_on_page and page_num > 1 and total_customers > 0:
        flash(f"No customers found on page {page_num}. Showing last available page.", "info")
        last_page = math.ceil(total_customers / ITEMS_PER_PAGE)
        return redirect(url_for('list_customers', page_num=last_page if last_page > 0 else 1))
    total_pages = math.ceil(total_customers / ITEMS_PER_PAGE) if total_customers > 0 else 0
    return render_template('customers/list.html',
                           customers=customers_on_page, title="Manage Customers",
                           current_page=page_num, total_pages=total_pages,
                           total_items=total_customers, per_page=ITEMS_PER_PAGE)


@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    # ... (keep existing add_customer logic) ...
    if request.method == 'POST':
        name = request.form.get('name')
        contact = request.form.get('contact')
        address = request.form.get('address')
        if not name:
            flash("Customer Name is required.", "error")
            return render_template('customers/add_edit.html', title="Add Customer", customer=None,
                                   form_data=request.form)
        customer_id = db.add_customer_db(name, contact, address)
        if customer_id:
            flash(f"Customer '{name}' added successfully!", "success")
            return redirect(url_for('list_customers'))
        else:
            flash(f"Failed to add customer '{name}'. Name might already exist or database error.", "error")
            return render_template('customers/add_edit.html', title="Add Customer", customer=None,
                                   form_data=request.form)
    return render_template('customers/add_edit.html', title="Add Customer", customer=None)


@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    # ... (keep existing edit_customer logic) ...
    customer = db.get_customer_by_id_db(customer_id)
    if not customer:
        flash("Customer not found.", "error")
        return redirect(url_for('list_customers'))
    if request.method == 'POST':
        name = request.form.get('name')
        contact = request.form.get('contact')
        address = request.form.get('address')
        if not name:
            flash("Customer Name is required.", "error")
            return render_template('customers/add_edit.html', title="Edit Customer", customer=customer)
        if db.update_customer_db(customer_id, name, contact, address):
            flash(f"Customer '{name}' updated successfully!", "success")
            return redirect(url_for('list_customers'))
        else:
            flash(f"Failed to update customer '{name}'. Name might already exist or database error.", "error")
            return render_template('customers/add_edit.html', title="Edit Customer", customer=customer)
    return render_template('customers/add_edit.html', title="Edit Customer", customer=customer)


@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    # ... (keep existing delete_customer logic) ...
    customer = db.get_customer_by_id_db(customer_id)
    if not customer:
        flash("Customer not found to delete.", "error")
        return redirect(url_for('list_customers'))
    if db.delete_customer_db(customer_id):
        flash(f"Customer '{customer['CustomerName']}' deleted successfully!", "success")
    else:
        flash(f"Failed to delete customer '{customer['CustomerName']}'. Check if they are linked to sales.", "error")
    return redirect(url_for('list_customers'))


@app.route('/pos', methods=['GET', 'POST'])
@login_required
def pos_interface():
    """Point of Sale interface for creating new sales."""
    # --- Use session for current sale ---
    current_sale = session.get('current_sale', {"items": [], "customer_name": "N/A", "total": 0.0})
    # --- End session usage ---

    all_products = db.get_all_products_db()
    customers = db.get_all_customers_db()
    prioritized_product_names = ["Refill (20)", "Refill (25)"]
    prioritized_products = []
    other_products = []
    for p in all_products:
        if p['ProductName'] in prioritized_product_names:
            prioritized_products.append(p)
        else:
            other_products.append(p)

    if request.method == 'POST':
        action = request.form.get('action')

        # Modify current_sale dictionary directly (it's a copy from session)
        if action == 'add_item':
            # ... (keep logic, but modify 'current_sale' instead of global) ...
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
                            if item["name"] == product_name:
                                item["quantity"] += quantity
                                item["subtotal"] = item["quantity"] * item["price"]
                                found = True;
                                break
                        if not found:
                            current_sale["items"].append({
                                "name": product_name, "price": product['Price'],
                                "quantity": quantity, "subtotal": product['Price'] * quantity
                            })
                        current_sale["total"] = sum(item['subtotal'] for item in current_sale['items'])
                        flash(f"Added {quantity} x {product_name}.", "info")
                    else:
                        flash(f"Product '{product_name}' not found.", "error")
            except ValueError:
                flash("Invalid quantity.", "error")

        elif action == 'add_custom_item':
            # ... (keep logic, but modify 'current_sale') ...
            custom_name = request.form.get('custom_product_name', 'Custom Item').strip()
            custom_price_str = request.form.get('custom_price')
            custom_quantity_str = request.form.get('custom_quantity', '1')
            if not custom_name: custom_name = "Custom Item"
            try:
                custom_price = float(custom_price_str if custom_price_str else 0)
                custom_quantity = int(custom_quantity_str if custom_quantity_str else 1)
                if custom_price < 0:
                    flash("Custom price must be non-negative.", "error")
                elif custom_quantity <= 0:
                    flash("Custom quantity must be positive.", "error")
                else:
                    found = False
                    for item in current_sale["items"]:
                        if item["name"] == custom_name and item["price"] == custom_price:
                            item["quantity"] += custom_quantity
                            item["subtotal"] = item["quantity"] * item["price"]
                            found = True;
                            break
                    if not found:
                        current_sale["items"].append({
                            "name": custom_name, "price": custom_price,
                            "quantity": custom_quantity, "subtotal": custom_price * custom_quantity
                        })
                    current_sale["total"] = sum(item['subtotal'] for item in current_sale['items'])
                    flash(f"Added {custom_quantity} x {custom_name} (Custom).", "info")
            except ValueError:
                flash("Invalid custom price or quantity.", "error")
            except TypeError:
                flash("Missing custom price or quantity.", "error")

        elif action == 'set_customer':
            # ... (keep logic, but modify 'current_sale') ...
            customer_name_from_form = request.form.get('customer_name_select')
            if customer_name_from_form is not None:
                if not customer_name_from_form.strip():
                    current_sale["customer_name"] = "N/A"
                    flash(f"Customer set to N/A (Walk-in).", "info")
                else:
                    cust = db.get_customer_by_name_db(customer_name_from_form)
                    if cust or customer_name_from_form == 'N/A':
                        current_sale["customer_name"] = customer_name_from_form
                        flash(f"Customer set to '{customer_name_from_form}'.", "info")
                    else:
                        current_sale["customer_name"] = customer_name_from_form
                        flash(
                            f"Customer set to '{customer_name_from_form}' (new or unlisted). Consider adding to customer list.",
                            "info")
            else:
                current_sale["customer_name"] = "N/A"
                flash("No customer name provided, set to N/A.", "warning")

        elif action == 'remove_item':
            # ... (keep logic, but modify 'current_sale') ...
            item_name_to_remove = request.form.get('item_name')
            item_price_to_remove_str = request.form.get('item_price')
            try:
                item_price_to_remove = float(item_price_to_remove_str)
                initial_length = len(current_sale["items"])
                current_sale["items"] = [item for item in current_sale["items"] if not (
                            item["name"] == item_name_to_remove and item["price"] == item_price_to_remove)]
                if len(current_sale["items"]) < initial_length:
                    current_sale["total"] = sum(item['subtotal'] for item in current_sale['items'])
                    flash(f"Removed {item_name_to_remove} from sale.", "info")
                else:
                    flash(f"Could not find exact item '{item_name_to_remove}' to remove.", "warning")
            except (ValueError, TypeError):
                flash(f"Error removing item '{item_name_to_remove}'. Invalid price data.", "error")

        elif action == 'increase_qty' or action == 'decrease_qty':
            # ... (keep logic, but modify 'current_sale') ...
            item_name = request.form.get('item_name')
            item_price_str = request.form.get('item_price')
            item_found = False
            try:
                item_price = float(item_price_str)
                for i, item in enumerate(current_sale["items"]):
                    if item["name"] == item_name and item["price"] == item_price:
                        if action == 'increase_qty':
                            item["quantity"] += 1;
                            flash(f"Increased quantity for {item_name}.", "info")
                        elif action == 'decrease_qty':
                            item["quantity"] -= 1
                            if item["quantity"] <= 0:
                                current_sale["items"].pop(i); flash(f"Removed {item_name}.", "info")
                            else:
                                flash(f"Decreased quantity for {item_name}.", "info")
                        if i < len(current_sale["items"]) and current_sale["items"][i]["name"] == item_name and \
                                current_sale["items"][i]["price"] == item_price:
                            current_sale["items"][i]["subtotal"] = current_sale["items"][i]["quantity"] * \
                                                                   current_sale["items"][i]["price"]
                        item_found = True;
                        break
                if item_found:
                    current_sale["total"] = sum(it['subtotal'] for it in current_sale['items'])
                else:
                    flash(f"Could not find exact item '{item_name}' to adjust quantity.", "warning")
            except (ValueError, TypeError):
                flash(f"Error adjusting quantity for '{item_name}'. Invalid price data.", "error")

        elif action == 'clear_sale':
            # --- Clear session variable ---
            session.pop('current_sale', None)
            current_sale = {"items": [], "customer_name": "N/A",
                            "total": 0.0}  # Also reset local copy for immediate render
            flash("Sale cleared.", "info")
            # --- End clear session ---

        elif action == 'finalize_sale':
            if not current_sale["items"]:
                flash("Cannot finalize an empty sale.", "error")
            else:
                # Use the current_sale data from session (or the local copy modified in this request)
                sale_id = db.create_sale_db(customer_name=current_sale["customer_name"])
                if sale_id:
                    all_items_added = True
                    for item in current_sale["items"]:
                        if not db.add_sale_item_db(sale_id, item["name"], item["quantity"], item["price"]):
                            all_items_added = False;
                            flash(f"Failed to add item '{item['name']}'.", "error");
                            break
                    if all_items_added:
                        conn = None
                        try:
                            conn = db.get_db_connection();
                            cursor = conn.cursor()
                            cursor.execute("SELECT SUM(Subtotal) FROM SaleItems WHERE SaleID = ?", (sale_id,))
                            final_total = cursor.fetchone()[0] or 0.0
                            cursor.execute("UPDATE Sales SET TotalAmount = ? WHERE SaleID = ?", (final_total, sale_id))
                            conn.commit();
                            app.logger.info(f"Final total {final_total} updated for SaleID {sale_id}")
                            flash(f"Sale #{sale_id} finalized successfully for ₱{final_total:.2f}!", "success")
                            # --- Clear session variable on success ---
                            session.pop('current_sale', None)
                            # --- End clear session ---
                            return redirect(url_for('view_sale', sale_id=sale_id))
                        except db.sqlite3.Error as e:
                            app.logger.error(f"DB Error updating final total: {e}", exc_info=True)
                            flash(f"DB Error updating final total for Sale #{sale_id}.", "error")
                            session[
                                'current_sale'] = current_sale  # Save potentially modified sale back to session on error
                            return redirect(url_for('pos_interface'))
                        finally:
                            if conn: conn.close()
                    else:
                        flash(f"Sale #{sale_id} created, but item saving failed.", "error")
                        session[
                            'current_sale'] = current_sale  # Save potentially modified sale back to session on error
                        return redirect(url_for('pos_interface'))
                else:
                    flash("Failed to create sale record.", "error")
                    session['current_sale'] = current_sale  # Save potentially modified sale back to session on error
            # Save potentially modified sale back to session before redirecting on failure/empty sale
            session['current_sale'] = current_sale
            return redirect(url_for('pos_interface'))

        # --- Save modified sale back to session after POST actions ---
        session['current_sale'] = current_sale
        return redirect(url_for('pos_interface'))
        # --- End save session ---

    # GET request: Render using the sale data retrieved from session
    return render_template('pos/interface.html',
                           title="New Sale",
                           prioritized_products=prioritized_products,
                           other_products=other_products,
                           customers=customers,
                           # Pass data from the session-retrieved dictionary
                           current_sale_items=current_sale["items"],
                           current_customer=current_sale["customer_name"],
                           current_total=current_sale["total"])


# --- Sales History Routes ---
# (Keep existing sales routes)
@app.route('/sales')
@app.route('/sales/page/<int:page_num>')
@login_required
def list_sales(page_num=1):
    total_sales = db.count_total_sales_db()
    sales_on_page = db.get_sales_paginated_db(page=page_num, per_page=ITEMS_PER_PAGE)
    if not sales_on_page and page_num > 1 and total_sales > 0:
        flash(f"No sales found on page {page_num}. Showing last available page.", "info")
        last_page = math.ceil(total_sales / ITEMS_PER_PAGE)
        return redirect(url_for('list_sales', page_num=last_page if last_page > 0 else 1))
    total_pages = math.ceil(total_sales / ITEMS_PER_PAGE) if total_sales > 0 else 0
    return render_template('sales/list.html',
                           sales=sales_on_page, title="Sales History",
                           current_page=page_num, total_pages=total_pages,
                           total_items=total_sales, per_page=ITEMS_PER_PAGE)


@app.route('/sales/<int:sale_id>')
@login_required
def view_sale(sale_id):
    sale_details = db.get_sale_details_db(sale_id)
    if not sale_details:
        flash(f"Sale with ID {sale_id} not found.", "error")
        return redirect(url_for('list_sales', page_num=1))
    return render_template('sales/details.html', sale=sale_details["info"], items=sale_details["items"],
                           title=f"Sale #{sale_id} Details")


@app.route('/sales/delete/<int:sale_id>', methods=['POST'])
@login_required
def delete_sale(sale_id):
    page = request.form.get('page', 1, type=int)
    if db.delete_sale_db(sale_id):
        flash(f"Sale #{sale_id} deleted successfully!", "success")
    else:
        flash(f"Failed to delete Sale #{sale_id}.", "error")
    return redirect(url_for('list_sales', page_num=page))


# --- Admin Routes ---
# (Keep existing admin routes)
@app.route('/admin')
@login_required
def admin_index():
    return render_template('admin/index.html', title="Admin Panel", BACKUP_DIR=BACKUP_DIR)


@app.route('/admin/restore_database', methods=['GET', 'POST'])
@login_required
def restore_database():
    if request.method == 'POST':
        if 'database_file' not in request.files:
            flash('No file part.', 'error');
            return redirect(request.url)
        file = request.files['database_file']
        if file.filename == '':
            flash('No selected file.', 'error');
            return redirect(request.url)
        if file and (file.filename.endswith('.db') or file.filename.endswith('.sqlite') or file.filename.endswith(
                '.sqlite3')):
            filename = secure_filename(file.filename)
            try:
                current_db_path = os.path.join(app.root_path, DATABASE_FILE)
                backup_db_dir_path = os.path.join(app.root_path, BACKUP_DIR)
                if not os.path.exists(backup_db_dir_path): os.makedirs(backup_db_dir_path)
                if os.path.exists(current_db_path):
                    original_name, original_ext = os.path.splitext(DATABASE_FILE)
                    backup_filename = f"{original_name}.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{original_ext}.bak"
                    backup_path = os.path.join(backup_db_dir_path, backup_filename)
                    shutil.copy2(current_db_path, backup_path)
                    flash(f'Backed up current database to {backup_path}', 'info');
                    app.logger.info(f"DB backed up to {backup_path}")
                else:
                    flash('No existing database to back up.', 'info');
                    app.logger.info(f"No existing DB file at {current_db_path}")
                file.save(current_db_path)
                flash(f'Database successfully restored from {filename}!', 'success');
                flash('RESTART the application.', 'warning');
                app.logger.info(f"DB restored from {filename}")
                return redirect(url_for('restore_database'))
            except Exception as e:
                flash(f'Error during restore: {str(e)}', 'error');
                app.logger.error(f"DB Restore Error: {e}", exc_info=True);
                return redirect(request.url)
        else:
            flash('Invalid file type.', 'error');
            return redirect(request.url)
    return render_template('admin/restore_db.html', title="Restore Database", BACKUP_DIR=BACKUP_DIR)


@app.route('/admin/backup_database')
@login_required
def backup_database():
    try:
        current_db_path = os.path.join(app.root_path, DATABASE_FILE)
        backup_db_dir_path = os.path.join(app.root_path, BACKUP_DIR)
        if not os.path.exists(backup_db_dir_path): os.makedirs(backup_db_dir_path)
        if os.path.exists(current_db_path):
            original_name, original_ext = os.path.splitext(DATABASE_FILE)
            backup_filename = f"{original_name}.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{original_ext}"
            backup_path = os.path.join(backup_db_dir_path, backup_filename)
            shutil.copy2(current_db_path, backup_path)
            flash(f'Successfully backed up database to {backup_path}', 'success')
            app.logger.info(f"Database backed up successfully to {backup_path}")
        else:
            flash('Database file not found.', 'error');
            app.logger.error(f"DB file not found at {current_db_path}")
    except Exception as e:
        flash(f'Error during backup: {str(e)}', 'error');
        app.logger.error(f"DB Backup Error: {e}", exc_info=True)
    return redirect(url_for('admin_index'))


# --- API Endpoints ---
# (Keep existing API endpoints)
@app.route('/api/products', methods=['GET'])
@require_api_key
def api_get_products():
    try:
        products = db.get_all_products_db();
        products_list = [dict(p) for p in products];
        return jsonify(products_list)
    except Exception as e:
        app.logger.error(f"API Error getting products: {e}", exc_info=True)
        return jsonify({"error": "Internal server error fetching products"}), 500


@app.route('/api/products/<string:name>', methods=['GET'])
@require_api_key
def api_get_product_by_name(name):
    try:
        product = db.get_product_by_name_db(name);
        if product: return jsonify(dict(product))
        return jsonify({"error": "Product not found"}), 404
    except Exception as e:
        app.logger.error(f"API Error getting product by name '{name}': {e}", exc_info=True)
        return jsonify({"error": "Internal server error fetching product"}), 500


@app.route('/api/sales', methods=['POST'])
@require_api_key
def api_sync_sale():
    if not request.is_json: return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    if not data: return jsonify({"error": "No data provided"}), 400
    if 'items' not in data or not isinstance(data['items'], list) or not data['items']:
        return jsonify({"error": "Missing or invalid 'items' list"}), 400
    customer_name = data.get('customer_name', 'N/A')
    items = data['items']
    sale_id = None
    try:
        sale_id = db.create_sale_db(customer_name=customer_name)
        if not sale_id: return jsonify({"error": "Failed to create sale record on server"}), 500
        total_calculated = 0.0
        for item_data in items:
            name = item_data.get('name');
            qty_str = item_data.get('quantity');
            price_str = item_data.get('price_at_sale')
            if not name or qty_str is None or price_str is None:
                app.logger.error(f"API Sync Error: Invalid item data for SaleID {sale_id}: {item_data}");
                continue
            try:
                qty = int(qty_str);
                price = float(price_str)
                if qty <= 0 or price < 0:
                    app.logger.error(f"API Sync Error: Invalid qty/price for item '{name}' in SaleID {sale_id}");
                    continue
                if not db.add_sale_item_db(sale_id, name, qty, price):
                    app.logger.error(f"API Sync Error: Failed to add item '{name}' to SaleID {sale_id} in DB.")
                else:
                    total_calculated += qty * price
            except (ValueError, TypeError):
                app.logger.error(f"API Sync Error: Invalid number format for item '{name}' in SaleID {sale_id}");
                continue
        conn = None
        try:
            conn = db.get_db_connection();
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(Subtotal) FROM SaleItems WHERE SaleID = ?", (sale_id,))
            db_total = cursor.fetchone()[0] or 0.0
            cursor.execute("UPDATE Sales SET TotalAmount = ? WHERE SaleID = ?", (db_total, sale_id))
            conn.commit();
            app.logger.info(f"API Sync: Updated final total for SaleID {sale_id} to {db_total}")
        except db.sqlite3.Error as e:
            app.logger.error(f"API Sync Error: Failed to update final total for SaleID {sale_id}: {e}", exc_info=True)
            return jsonify({"error": "Sale items added but failed to update final total", "sale_id": sale_id}), 500
        finally:
            if conn: conn.close()
        return jsonify({"message": "Sale synchronized successfully", "sale_id": sale_id}), 201
    except Exception as e:
        app.logger.error(f"API Sync Error: Unexpected error processing sale: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred on the server"}), 500


# --- Re-added __main__ block for local debugging ---
if __name__ == '__main__':
    print("-" * 68);
    print("POS System Starting...")
    print(f"DB: '{DATABASE_FILE}'. Run 'python database_setup.py' if needed.")
    print(f"Backups: '{os.path.abspath(BACKUP_DIR)}'.")
    print(f"URL: http://127.0.0.1:5000");
    print("-" * 68)
     #Ensure debug is True for local development/testing
    app.run(debug=True)
# --- End Re-added block ---
