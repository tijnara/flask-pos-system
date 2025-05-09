# app.py
# Description: The main Flask application file, configured for deployment.

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import db_operations as db
import datetime
from dateutil.relativedelta import relativedelta
import os
import shutil
from werkzeug.utils import secure_filename
import math
import logging
from functools import wraps
import calendar
import json  # Import json for explicit stringification if needed

app = Flask(__name__)

# --- IMPORTANT: Secret Key Configuration ---
app.secret_key = os.environ.get("SECRET_KEY", "a_default_development_secret_key_123!@#")
if app.secret_key == "a_default_development_secret_key_123!@#" and os.environ.get("FLASK_ENV") != "development":
    with app.app_context():
        app.logger.warning(
            "SECURITY WARNING: Using default SECRET_KEY. Set the SECRET_KEY environment variable in production.")

# --- Hardcoded Password (INSECURE - FOR DEMO ONLY) ---
HARDCODED_PASSWORD = "password123"

# --- Configuration for Database and Backups ---
DATABASE_FILE = "pos_system.db"
BACKUP_DIR = "db_backups"
ITEMS_PER_PAGE = 10
api_keys_str = os.environ.get("VALID_API_KEYS", "YOUR_SUPER_SECRET_API_KEY_12345")
VALID_API_KEYS = set(key.strip() for key in api_keys_str.split(',') if key.strip())
if not VALID_API_KEYS or "YOUR_SUPER_SECRET_API_KEY_12345" in VALID_API_KEYS:
    with app.app_context():
        app.logger.warning(
            "SECURITY WARNING: Using default or no API keys. Set the VALID_API_KEYS environment variable.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

backup_dir_path = os.path.join(app.root_path, BACKUP_DIR)
if not os.path.exists(backup_dir_path):
    try:
        os.makedirs(backup_dir_path)
        with app.app_context():
            app.logger.info(f"Created backup directory at: {backup_dir_path}")
    except OSError as e:
        with app.app_context():
            app.logger.error(f"Could not create backup directory {backup_dir_path}: {e}")


# --- Context Processors ---
@app.context_processor
def utility_processor():
    return {'now': datetime.datetime.now,
            'min': min,
            'max': max,
            'logged_in': session.get('logged_in', False),
            'calendar': calendar
            }


# --- Login Required Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


# --- API Key Decorator ---
# ... (your existing require_api_key decorator) ...
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY') or \
                  request.args.get('api_key') or \
                  (request.is_json and request.json.get('api_key')) or \
                  request.form.get('api_key')
        if not api_key or api_key not in VALID_API_KEYS:
            app.logger.warning(f"Unauthorized API access attempt. Key used: {api_key}")
            return jsonify({"error": "Unauthorized - Invalid or missing API key"}), 401
        return f(*args, **kwargs)

    return decorated_function


# --- Main Routes ---
# ... (your existing index, login, logout, product, customer, POS, sales history routes) ...
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
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
    if session.get('logged_in'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        password_attempt = request.form.get('password')
        if password_attempt == HARDCODED_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            app.logger.info("Login successful.")
            flash("Login successful!", "success")
            next_url = request.args.get('next')
            return redirect(next_url or url_for('index'))
        else:
            app.logger.warning("Failed login attempt.")
            flash("Incorrect password.", "error")
    return render_template('login.html', title="Login")


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('current_sale', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


# --- Product Routes ---
@app.route('/products')
@login_required
def list_products():
    products = db.get_all_products_db()
    return render_template('products/list.html', products=products, title="Manage Products")


@app.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
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
    product = db.get_product_by_id_db(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('list_products'))
    if db.delete_product_db(product_id):
        flash(f"Product '{product['ProductName']}' deleted successfully!", "success")
    else:
        flash(
            f"Failed to delete product '{product['ProductName']}'. It might be part of a sale or a database error occurred.",
            "error")
    return redirect(url_for('list_products'))


# --- Customer Routes ---
@app.route('/customers')
@app.route('/customers/page/<int:page_num>')
@login_required
def list_customers(page_num=1):
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
            flash(f"Failed to add customer '{name}'. Name might already exist or there was a database error.", "error")
            return render_template('customers/add_edit.html', title="Add Customer", customer=None,
                                   form_data=request.form)
    return render_template('customers/add_edit.html', title="Add Customer", customer=None)


@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
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
    customer = db.get_customer_by_id_db(customer_id)
    if not customer:
        flash("Customer not found to delete.", "error")
        return redirect(url_for('list_customers'))
    if db.delete_customer_db(customer_id):
        flash(f"Customer '{customer['CustomerName']}' deleted successfully!", "success")
    else:
        flash(f"Failed to delete customer '{customer['CustomerName']}'. Check if they are linked to sales.", "error")
    return redirect(url_for('list_customers'))


# --- POS Interface Route ---
@app.route('/pos', methods=['GET', 'POST'])
@login_required
def pos_interface():
    current_sale = session.get('current_sale', {"items": [], "customer_name": "N/A", "total": 0.0})
    all_products = db.get_all_products_db()
    customers = db.get_all_customers_db()
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
                            if item["name"] == product_name and item["price"] == product['Price']:
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
            selected_product_name = request.form.get('custom_product_name')
            manual_product_name = request.form.get('custom_product_name_override')

            custom_name_to_use = selected_product_name
            if selected_product_name == 'Custom Item/Service':
                if manual_product_name and manual_product_name.strip():
                    custom_name_to_use = manual_product_name.strip()
                else:
                    custom_name_to_use = "Custom Item"

            custom_price_str = request.form.get('custom_price')
            custom_quantity_str = request.form.get('custom_quantity', '1')
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
                        if item["name"] == custom_name_to_use and item["price"] == custom_price:
                            item["quantity"] += custom_quantity
                            item["subtotal"] = item["quantity"] * item["price"]
                            found = True;
                            break
                    if not found:
                        current_sale["items"].append({
                            "name": custom_name_to_use, "price": custom_price,
                            "quantity": custom_quantity, "subtotal": custom_price * custom_quantity
                        })
                    current_sale["total"] = sum(item['subtotal'] for item in current_sale['items'])
                    flash(f"Added {custom_quantity} x {custom_name_to_use}.", "info")
            except (ValueError, TypeError):
                flash("Invalid custom price or quantity.", "error")

        elif action == 'set_customer':
            customer_name_from_form = request.form.get('customer_name_select', "N/A").strip()
            current_sale["customer_name"] = customer_name_from_form or "N/A"
            flash(f"Customer set to '{current_sale['customer_name']}'.", "info")

        elif action == 'remove_item':
            item_name_to_remove = request.form.get('item_name')
            item_price_to_remove_str = request.form.get('item_price')
            try:
                item_price_to_remove = float(item_price_to_remove_str)
                initial_length = len(current_sale["items"])
                current_sale["items"] = [
                    item for item in current_sale["items"]
                    if not (item["name"] == item_name_to_remove and item["price"] == item_price_to_remove)
                ]
                if len(current_sale["items"]) < initial_length:
                    current_sale["total"] = sum(item['subtotal'] for item in current_sale['items'])
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
                    if item["name"] == item_name and item["price"] == item_price:
                        if action == 'increase_qty':
                            item["quantity"] += 1
                        elif action == 'decrease_qty':
                            item["quantity"] -= 1

                        if item["quantity"] <= 0:
                            current_sale["items"].pop(i)
                        else:
                            item["subtotal"] = item["quantity"] * item["price"]

                        flash(f"Adjusted quantity for {item_name}.", "info")
                        item_found_for_qty_adj = True;
                        break
                if item_found_for_qty_adj:
                    current_sale["total"] = sum(it['subtotal'] for it in current_sale['items'])
                else:
                    flash(f"Could not find '{item_name}' to adjust quantity.", "warning")
            except (ValueError, TypeError):
                flash(f"Error adjusting quantity for '{item_name}'. Invalid data.", "error")

        elif action == 'clear_sale':
            session.pop('current_sale', None)
            flash("Sale cleared.", "info")
            return redirect(url_for('pos_interface'))

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
                            break
                    if all_items_added:
                        conn = None
                        try:
                            conn = db.get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT SUM(Subtotal) FROM SaleItems WHERE SaleID = ?", (sale_id,))
                            final_total_row = cursor.fetchone()
                            final_total = final_total_row[0] if final_total_row and final_total_row[
                                0] is not None else 0.0

                            cursor.execute("UPDATE Sales SET TotalAmount = ? WHERE SaleID = ?", (final_total, sale_id))
                            conn.commit()
                            app.logger.info(f"Final total {final_total} updated for SaleID {sale_id}")
                            flash(f"Sale #{sale_id} finalized successfully for ₱{final_total:.2f}!", "success")
                            session.pop('current_sale', None)
                            return redirect(url_for('view_sale', sale_id=sale_id))
                        except sqlite3.Error as e:
                            app.logger.error(f"DB Error updating final total for SaleID {sale_id}: {e}", exc_info=True)
                            flash(f"DB Error updating final total for Sale #{sale_id}. Items saved.", "error")
                        finally:
                            if conn: conn.close()
                else:
                    flash("Failed to create sale record in database.", "error")

        session['current_sale'] = current_sale
        return redirect(url_for('pos_interface'))

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
        return redirect(url_for('list_sales'))
    return render_template('sales/details.html',
                           sale=sale_details["info"],
                           items=sale_details["items"],
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


# --- WEEKLY REPORTS ROUTE ---
@app.route('/reports/weekly')
@login_required
def weekly_reports_page():
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

        if chart_info and isinstance(chart_info, dict):
            if chart_info.get('error'):
                app.logger.error(f"Error from get_weekly_sales_chart_data_db: {chart_info.get('error')}")
                page_error_message = "Could not load weekly sales chart data due to a database error."
            chart_labels_for_template = chart_info.get('labels', [])
            chart_data_for_template = chart_info.get('data', [])
            total_sales_for_period = chart_info.get('total', 0.0)
            if not isinstance(chart_labels_for_template, list): chart_labels_for_template = []
            if not isinstance(chart_data_for_template, list): chart_data_for_template = []
        else:
            app.logger.error(f"Unexpected chart_info structure for weekly report: {chart_info}")
            page_error_message = "Failed to retrieve weekly sales chart data."

        if items_summary is None:
            app.logger.warning("Items summary for weekly report was None.")
            items_summary_for_template = []
            if not page_error_message:
                page_error_message = "Could not load weekly item summary."
            else:
                page_error_message += " Also, could not load item summary."
        elif isinstance(items_summary, list):
            items_summary_for_template = items_summary
        else:
            app.logger.error(f"Unexpected items_summary structure for weekly report: {items_summary}")
            items_summary_for_template = []
            if not page_error_message: page_error_message = "Failed to retrieve item summary."

        app.logger.info(f"WEEKLY REPORT: Labels: {chart_labels_for_template}, Data: {chart_data_for_template}")
        return render_template('reports.html',
                               title="Weekly Sales Report",
                               week_start_date=week_start_date.strftime('%Y-%m-%d'),
                               week_end_date=week_end_date.strftime('%Y-%m-%d'),
                               total_sales_for_chart_week=total_sales_for_period,
                               chart_labels=chart_labels_for_template,
                               chart_data=chart_data_for_template,
                               items_sold_summary=items_summary_for_template,
                               error_message=page_error_message
                               )
    except Exception as e:
        app.logger.error(f"Error generating weekly reports page: {e}", exc_info=True)
        flash("An unexpected error occurred while generating the weekly report.", "error")
        return render_template('reports.html',
                               title="Weekly Sales Report",
                               error_message="Could not load report data due to an unexpected error.",
                               week_start_date="N/A", week_end_date="N/A",
                               total_sales_for_chart_week=0.0, chart_labels=[], chart_data=[],
                               items_sold_summary=[])


# --- MONTHLY REPORTS ROUTE ---
@app.route('/reports/monthly')
@app.route('/reports/monthly/<int:year>/<int:month>')
@login_required
def monthly_reports_page(year=None, month=None):
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
            flash("Invalid month selected. Showing current month.", "warning")
            year, month = today.year, today.month
        if not (today.year - 50 <= year <= today.year + 5):
            flash("Invalid year selected. Showing current month.", "warning")
            year, month = today.year, today.month

        month_name_str_val = calendar.month_name[month]

        chart_info = db.get_monthly_sales_chart_data_db(year, month)
        items_summary = db.get_items_sold_summary_for_month_db(year, month)

        if chart_info and isinstance(chart_info, dict):
            if chart_info.get('error'):
                app.logger.error(
                    f"Error from get_monthly_sales_chart_data_db for {year}-{month}: {chart_info.get('error')}")
                page_error_message = f"Could not load sales chart data for {month_name_str_val} {year} due to a database error."
            chart_labels_for_template = chart_info.get('labels', [])
            chart_data_for_template = chart_info.get('data', [])
            total_sales_for_month_val = chart_info.get('total', 0.0)
            # Ensure month_name is also correctly fetched or defaulted from chart_info if it provides it
            month_name_str_val = chart_info.get('month_name', month_name_str_val)
            if not isinstance(chart_labels_for_template, list): chart_labels_for_template = []
            if not isinstance(chart_data_for_template, list): chart_data_for_template = []
        else:
            app.logger.error(f"Unexpected chart_info structure for monthly report ({year}-{month}): {chart_info}")
            page_error_message = f"Failed to retrieve sales chart data for {month_name_str_val} {year}."

        if items_summary is None:
            app.logger.warning(f"Items summary for monthly report ({year}-{month}) was None.")
            items_summary_for_template = []
            if not page_error_message:
                page_error_message = f"Could not load item summary for {month_name_str_val} {year}."
            else:
                page_error_message += " Also, could not load item summary."
        elif isinstance(items_summary, list):
            items_summary_for_template = items_summary
        else:
            app.logger.error(f"Unexpected items_summary structure for monthly report ({year}-{month}): {items_summary}")
            items_summary_for_template = []
            if not page_error_message: page_error_message = f"Failed to retrieve item summary for {month_name_str_val} {year}."

        current_month_date = datetime.date(year, month, 1)
        prev_month_date = current_month_date - relativedelta(months=1)
        next_month_date = current_month_date + relativedelta(months=1)

        app.logger.info(
            f"MONTHLY REPORT ({year}-{month}): Labels: {chart_labels_for_template}, Data: {chart_data_for_template}")
        return render_template('monthly_report.html',
                               title=f"Monthly Sales Report - {month_name_str_val} {year}",
                               report_year=year,
                               report_month_num=month,
                               report_month_name=month_name_str_val,
                               total_sales_for_month=total_sales_for_month_val,
                               chart_labels=chart_labels_for_template,
                               chart_data=chart_data_for_template,
                               items_sold_summary=items_summary_for_template,
                               prev_month_year=prev_month_date.year,
                               prev_month_num=prev_month_date.month,
                               next_month_year=next_month_date.year,
                               next_month_num=next_month_date.month,
                               current_year=today.year,
                               current_month=today.month,
                               error_message=page_error_message
                               )
    except ValueError:
        app.logger.error(f"Invalid date for monthly report: year={year}, month={month}", exc_info=True)
        flash("Invalid date parameters for the monthly report.", "error")
        return redirect(url_for('monthly_reports_page'))
    except Exception as e:
        app.logger.error(f"Error generating monthly reports page for {year}-{month}: {e}", exc_info=True)
        flash("An unexpected error occurred while generating the monthly report.", "error")
        today_fallback = datetime.date.today()
        prev_month_fallback = today_fallback - relativedelta(months=1)
        next_month_fallback = today_fallback + relativedelta(months=1)
        return render_template('monthly_report.html',
                               title="Monthly Sales Report",
                               error_message="Could not load report data due to an unexpected error.",
                               report_year=today_fallback.year, report_month_num=today_fallback.month,
                               report_month_name=calendar.month_name[today_fallback.month],
                               total_sales_for_month=0.0, chart_labels=[], chart_data=[], items_sold_summary=[],
                               prev_month_year=prev_month_fallback.year, prev_month_num=prev_month_fallback.month,
                               next_month_year=next_month_fallback.year, next_month_num=next_month_fallback.month,
                               current_year=today_fallback.year, current_month=today_fallback.month
                               )


# --- Admin Routes ---
# ... (your existing admin routes) ...
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

                file.save(current_db_path)
                flash(f'Database successfully restored from {filename}!', 'success');
                flash('RESTART the application for changes to take full effect.', 'warning');
                app.logger.info(f"DB restored from {filename}")
                return redirect(url_for('admin_index'))
            except Exception as e:
                flash(f'Error during restore: {str(e)}', 'error');
                app.logger.error(f"DB Restore Error: {e}", exc_info=True);
        else:
            flash('Invalid file type. Only .db, .sqlite, .sqlite3 are allowed.', 'error');
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
            backup_filename = f"{original_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db.bak"
            backup_path = os.path.join(backup_db_dir_path, backup_filename)
            shutil.copy2(current_db_path, backup_path)
            flash(f'Successfully backed up database to {backup_path}', 'success')
            app.logger.info(f"Database backed up successfully to {backup_path}")
        else:
            flash('Database file not found. Cannot perform backup.', 'error');
            app.logger.error(f"DB file not found at {current_db_path} for backup.")
    except Exception as e:
        flash(f'Error during backup: {str(e)}', 'error');
        app.logger.error(f"DB Backup Error: {e}", exc_info=True)
    return redirect(url_for('admin_index'))


# --- API Endpoints ---
# ... (your existing API endpoints) ...
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

    required_fields = ['items']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields in JSON payload (e.g., 'items')"}), 400
    if not isinstance(data['items'], list) or not data['items']:
        return jsonify({"error": "Invalid 'items' list. Must be a non-empty list."}), 400

    customer_name = data.get('customer_name', 'N/A')
    items_to_sync = data['items']
    sale_id = None

    try:
        sale_id = db.create_sale_db(customer_name=customer_name)
        if not sale_id:
            return jsonify({"error": "Failed to create sale record on server"}), 500

        for item_data in items_to_sync:
            name = item_data.get('name')
            qty_str = item_data.get('quantity')
            price_str = item_data.get('price_at_sale')

            if not all([name, qty_str is not None, price_str is not None]):
                app.logger.error(
                    f"API Sync Error: Invalid item data for SaleID {sale_id}: {item_data}. Skipping item.");
                continue
            try:
                qty = int(qty_str)
                price = float(price_str)
                if qty <= 0 or price < 0:
                    app.logger.error(
                        f"API Sync Error: Invalid qty/price for item '{name}' in SaleID {sale_id}. Skipping item.");
                    continue
                if not db.add_sale_item_db(sale_id, name, qty, price):
                    app.logger.error(f"API Sync Error: Failed to add item '{name}' to SaleID {sale_id} in DB.")
            except (ValueError, TypeError):
                app.logger.error(
                    f"API Sync Error: Invalid number format for item '{name}' in SaleID {sale_id}. Skipping item.");
                continue

        conn = None
        try:
            conn = db.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(Subtotal) FROM SaleItems WHERE SaleID = ?", (sale_id,))
            db_total_row = cursor.fetchone()
            db_total = db_total_row[0] if db_total_row and db_total_row[0] is not None else 0.0

            cursor.execute("UPDATE Sales SET TotalAmount = ? WHERE SaleID = ?", (db_total, sale_id))
            conn.commit()
            app.logger.info(f"API Sync: Updated final total for SaleID {sale_id} to {db_total}")
        except sqlite3.Error as e:
            app.logger.error(f"API Sync Error: Failed to update final total for SaleID {sale_id}: {e}", exc_info=True)
            return jsonify(
                {"error": "Sale items may have been added but failed to update final total", "sale_id": sale_id}), 500
        finally:
            if conn: conn.close()

        return jsonify(
            {"message": "Sale synchronized successfully", "sale_id": sale_id, "total_amount_synced": db_total}), 201

    except Exception as e:
        app.logger.error(f"API Sync Error: Unexpected error processing sale: {e}", exc_info=True)
        error_response = {"error": "An unexpected error occurred on the server"}
        if sale_id: error_response["sale_id_created"] = sale_id
        return jsonify(error_response), 500


if __name__ == '__main__':
    print("-" * 68);
    print("POS System Starting...")
    print(f"DB: '{DATABASE_FILE}'. Run 'python database_setup.py' if needed.")
    print(f"Backups: '{os.path.abspath(BACKUP_DIR)}'.")
    print(f"URL: http://127.0.0.1:5000");
    print("-" * 68)
    app.run(debug=True)
