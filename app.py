# app.py
# Description: The main Flask application file.

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import db_operations as db  # Assuming db_operations.py is in the same directory
import datetime  # Import the datetime module
import os
import shutil
from werkzeug.utils import secure_filename
import math  # For math.ceil
import logging  # Import logging module

app = Flask(__name__)
app.secret_key = "your_very_secret_key"  # Important for session management and flash messages

# --- Configuration for Database and Backups ---
DATABASE_FILE = "pos_system.db"  # Name of your SQLite database file
BACKUP_DIR = "db_backups"  # Directory to store database backups
ITEMS_PER_PAGE = 10  # Number of items (sales, customers, etc.) to display per page

# Configure basic logging for the Flask app itself
# Logs will go to the console where the app is running.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create backup directory if it doesn't exist
# This will be created in the same directory where app.py is run.
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)
    # Use Flask's built-in logger after app is initialized
    with app.app_context():
        app.logger.info(f"Created backup directory at: {os.path.abspath(BACKUP_DIR)}")


# --- Context Processors ---
@app.context_processor
def utility_processor():
    """Injects utility functions into the template context."""
    # Make the 'now' function (for local time), 'min', and 'max' functions available in templates
    return {'now': datetime.datetime.now, 'min': min, 'max': max}


# --- Helper Functions ---
def flash_errors(form):
    """Flashes form errors (if you were using Flask-WTF or similar)."""
    # This function is a placeholder if you're not using a form library that populates form.errors
    # If using request.form directly, error handling is done within routes.
    pass  # Currently not used with direct request.form handling


# --- Main Routes ---
@app.route('/')
def index():
    """Main page, could be a dashboard or the POS interface."""
    return render_template('index.html', title="POS Home")


# --- Product Routes ---
@app.route('/products')
def list_products():
    """Displays a list of all products."""
    # Note: Products are not paginated in this example, but could be if needed.
    products = db.get_all_products_db()
    return render_template('products/list.html', products=products, title="Manage Products")


@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    """Handles adding a new product."""
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
def edit_product(product_id):
    """Handles editing an existing product."""
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
def delete_product(product_id):
    """Handles deleting a product."""
    product = db.get_product_by_id_db(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for('list_products'))
    if db.delete_product_db(product_id):
        flash(f"Product '{product['ProductName']}' deleted successfully!", "success")
    else:
        flash(f"Failed to delete product '{product['ProductName']}'. It might be part of a sale.", "error")
    return redirect(url_for('list_products'))


# --- Customer Routes ---
@app.route('/customers')
@app.route('/customers/page/<int:page_num>')
def list_customers(page_num=1):
    """Displays a list of all customers, paginated."""
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
def add_customer():
    """Handles adding a new customer."""
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
            return redirect(url_for('list_customers'))  # Redirect to first page of customers
        else:
            flash(f"Failed to add customer '{name}'. Name might already exist or database error.", "error")
            return render_template('customers/add_edit.html', title="Add Customer", customer=None,
                                   form_data=request.form)
    return render_template('customers/add_edit.html', title="Add Customer", customer=None)


@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    """Handles editing an existing customer."""
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
            # Redirect back to the customer list (consider preserving page number if needed)
            return redirect(url_for('list_customers'))
        else:
            flash(f"Failed to update customer '{name}'. Name might already exist or database error.", "error")
            return render_template('customers/add_edit.html', title="Edit Customer", customer=customer)
    return render_template('customers/add_edit.html', title="Edit Customer", customer=customer)


@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    """Handles deleting a customer."""
    customer = db.get_customer_by_id_db(customer_id)
    if not customer:
        flash("Customer not found to delete.", "error")
        return redirect(url_for('list_customers'))
    if db.delete_customer_db(customer_id):
        flash(f"Customer '{customer['CustomerName']}' deleted successfully!", "success")
    else:
        flash(f"Failed to delete customer '{customer['CustomerName']}'. Check if they are linked to sales.", "error")
    # Redirect back to the customer list (consider preserving page number if needed)
    return redirect(url_for('list_customers'))


# --- POS / New Sale Route ---
# In-memory representation of current sale.
# For a multi-user or more robust system, this should be stored in the session or database.
current_sale = {"items": [], "customer_name": "N/A", "total": 0.0}


@app.route('/pos', methods=['GET', 'POST'])
def pos_interface():
    """Point of Sale interface for creating new sales."""
    global current_sale  # Use global for this simple example; consider session for multi-user
    all_products = db.get_all_products_db()  # Get all products first
    customers = db.get_all_customers_db()  # Get all customers for datalist

    # --- Prioritize specific products ---
    prioritized_product_names = ["Refill (20)", "Refill (25)"]  # Add names to prioritize here
    prioritized_products = []
    other_products = []

    for p in all_products:
        if p['ProductName'] in prioritized_product_names:
            prioritized_products.append(p)
        else:
            other_products.append(p)
    # --- End Prioritization ---

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
                    # Find product in the combined list (or just use db function)
                    product = db.get_product_by_name_db(product_name)
                    if product:
                        found = False
                        # Check if item already in sale to update quantity
                        for item in current_sale["items"]:
                            # Match by name only for standard items added this way
                            if item["name"] == product_name:
                                item["quantity"] += quantity
                                item["subtotal"] = item["quantity"] * item["price"]
                                found = True;
                                break
                        if not found:  # Add as new item
                            current_sale["items"].append({
                                "name": product_name, "price": product['Price'],
                                "quantity": quantity, "subtotal": product['Price'] * quantity
                            })
                        # Recalculate total
                        current_sale["total"] = sum(item['subtotal'] for item in current_sale['items'])
                        flash(f"Added {quantity} x {product_name}.", "info")
                    else:
                        flash(f"Product '{product_name}' not found.", "error")
            except ValueError:
                flash("Invalid quantity.", "error")

        elif action == 'add_custom_item':
            custom_name = request.form.get('custom_product_name', 'Custom Item').strip()
            custom_price_str = request.form.get('custom_price')
            custom_quantity_str = request.form.get('custom_quantity', '1')
            if not custom_name: custom_name = "Custom Item"  # Default name if empty
            try:
                custom_price = float(custom_price_str if custom_price_str else 0)
                custom_quantity = int(custom_quantity_str if custom_quantity_str else 1)
                if custom_price < 0:
                    flash("Custom price must be non-negative.", "error")
                elif custom_quantity <= 0:
                    flash("Custom quantity must be positive.", "error")
                else:
                    found = False
                    # Check if an item with the exact same custom name AND price already exists
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
                        # Allow setting unlisted customer name
                        current_sale["customer_name"] = customer_name_from_form
                        flash(
                            f"Customer set to '{customer_name_from_form}' (new or unlisted). Consider adding to customer list.",
                            "info")
            else:  # Should not happen with current form, but defensive
                current_sale["customer_name"] = "N/A"
                flash("No customer name provided, set to N/A.", "warning")

        elif action == 'remove_item':
            item_name_to_remove = request.form.get('item_name')
            item_price_to_remove_str = request.form.get('item_price')
            try:
                item_price_to_remove = float(item_price_to_remove_str)
                initial_length = len(current_sale["items"])
                # Remove item matching name AND price
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
                flash(f"Error removing item '{item_name_to_remove}'. Invalid price data.", "error")

        elif action == 'increase_qty' or action == 'decrease_qty':
            item_name = request.form.get('item_name')
            item_price_str = request.form.get('item_price')
            item_found = False
            try:
                item_price = float(item_price_str)
                for i, item in enumerate(current_sale["items"]):
                    # Find item matching name AND price
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
                        # Update subtotal only if item still exists (check index before accessing)
                        # This check is important because pop(i) changes the list length
                        if i < len(current_sale["items"]) and current_sale["items"][i]["name"] == item_name and \
                                current_sale["items"][i]["price"] == item_price:
                            current_sale["items"][i]["subtotal"] = current_sale["items"][i]["quantity"] * \
                                                                   current_sale["items"][i]["price"]
                        item_found = True;
                        break

                if item_found:
                    current_sale["total"] = sum(it['subtotal'] for it in current_sale['items'])  # Recalculate total
                else:
                    flash(f"Could not find exact item '{item_name}' to adjust quantity.", "warning")

            except (ValueError, TypeError):
                flash(f"Error adjusting quantity for '{item_name}'. Invalid price data.", "error")

        elif action == 'clear_sale':
            current_sale = {"items": [], "customer_name": "N/A", "total": 0.0};
            flash("Sale cleared.", "info")

        elif action == 'finalize_sale':
            if not current_sale["items"]:
                flash("Cannot finalize an empty sale.", "error")
            else:
                sale_id = db.create_sale_db(customer_name=current_sale["customer_name"])
                if sale_id:
                    all_items_added = True
                    # Iterate through items and call the modified add_sale_item_db
                    for item in current_sale["items"]:
                        # Pass the price stored in the current_sale item
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
                            final_total = cursor.fetchone()[0] or 0.0  # Handle case where SUM is NULL
                            cursor.execute("UPDATE Sales SET TotalAmount = ? WHERE SaleID = ?", (final_total, sale_id))
                            conn.commit();
                            app.logger.info(f"Final total {final_total} updated for SaleID {sale_id}")
                            flash(f"Sale #{sale_id} finalized successfully for ₱{final_total:.2f}!",
                                  "success")  # Using PHP currency
                            current_sale = {"items": [], "customer_name": "N/A", "total": 0.0}  # Reset for next sale
                            return redirect(url_for('view_sale', sale_id=sale_id))  # Redirect to sale details page
                        except db.sqlite3.Error as e:
                            app.logger.error(f"DB Error updating final total: {e}", exc_info=True)
                            flash(f"DB Error updating final total for Sale #{sale_id}.", "error")
                            return redirect(url_for('pos_interface'))
                        finally:
                            if conn: conn.close()
                    else:
                        # Sale record created, but items might be missing. Needs admin review.
                        flash(
                            f"Sale #{sale_id} created, but one or more items failed to save. Please review sale details and logs.",
                            "error")
                        return redirect(url_for('pos_interface'))
                else:
                    # create_sale_db failed, flash message already set by it (due to logging)
                    flash("Failed to create sale record in database. Please try again.", "error")  # Keep flash for user
            # If finalize failed or was empty, redirect back to POS interface to show messages
            return redirect(url_for('pos_interface'))

        # Redirect back to POS interface for most actions to show updates/messages
        return redirect(url_for('pos_interface'))

    # GET request
    return render_template('pos/interface.html',
                           title="New Sale",
                           # Pass prioritized and other products separately
                           prioritized_products=prioritized_products,
                           other_products=other_products,
                           customers=customers,
                           current_sale_items=current_sale["items"],
                           current_customer=current_sale["customer_name"],
                           current_total=current_sale["total"])


# --- Sales History Routes ---
@app.route('/sales')
@app.route('/sales/page/<int:page_num>')
def list_sales(page_num=1):
    """Displays a list of all sales, paginated."""
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
def view_sale(sale_id):
    """Displays details of a specific sale."""
    sale_details = db.get_sale_details_db(sale_id)
    if not sale_details:
        flash(f"Sale with ID {sale_id} not found.", "error")
        return redirect(url_for('list_sales', page_num=1))  # Redirect to first page of sales list
    return render_template('sales/details.html', sale=sale_details["info"], items=sale_details["items"],
                           title=f"Sale #{sale_id} Details")


@app.route('/sales/delete/<int:sale_id>', methods=['POST'])
def delete_sale(sale_id):
    """Handles deleting a sale record."""
    # Optionally, retrieve current page number if passed from form to redirect back
    page = request.form.get('page', 1, type=int)

    if db.delete_sale_db(sale_id):
        flash(f"Sale #{sale_id} deleted successfully!", "success")
    else:
        flash(f"Failed to delete Sale #{sale_id}. It might have already been deleted or a database error occurred.",
              "error")

    # Redirect back to the sales list, potentially to the same page number
    return redirect(url_for('list_sales', page_num=page))


# --- Admin Routes ---
@app.route('/admin')
def admin_index():
    """Displays the main admin page."""
    # Add authorization checks here in a real application
    return render_template('admin/index.html', title="Admin Panel", BACKUP_DIR=BACKUP_DIR)


@app.route('/admin/restore_database', methods=['GET', 'POST'])
def restore_database():
    """
    Allows uploading a .db file to restore the database.
    WARNING: This overwrites the current database.
    Ensure this route is properly secured in a production environment.
    """
    # Add authorization checks here in a real application
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
                    backup_filename = f"{original_name}.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{original_ext}.bak"  # Keep .bak for restore backups
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
def backup_database():
    """Creates a timestamped backup of the current database file."""
    # Add authorization checks here in a real application
    try:
        current_db_path = os.path.join(app.root_path, DATABASE_FILE)
        backup_db_dir_path = os.path.join(app.root_path, BACKUP_DIR)

        if not os.path.exists(backup_db_dir_path):
            os.makedirs(backup_db_dir_path)
            app.logger.info(f"Created backup directory at {backup_db_dir_path}")

        if os.path.exists(current_db_path):
            original_name, original_ext = os.path.splitext(DATABASE_FILE)
            # Creates backup as: original_name.YYYYMMDDHHMMSS.original_ext
            backup_filename = f"{original_name}.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{original_ext}"
            backup_path = os.path.join(backup_db_dir_path, backup_filename)

            shutil.copy2(current_db_path, backup_path)

            flash(f'Successfully backed up database to {backup_path}', 'success')
            app.logger.info(f"Database backed up successfully to {backup_path}")
        else:
            flash('Database file not found. Cannot create backup.', 'error')
            app.logger.error(f"Database file not found at {current_db_path}, backup failed.")

    except Exception as e:
        flash(f'An error occurred during database backup: {str(e)}', 'error')
        app.logger.error(f"DB Backup Error: {e}", exc_info=True)

    # Redirect back to the admin index page after backup
    return redirect(url_for('admin_index'))


# --- API Endpoints ---
@app.route('/api/products', methods=['GET'])
def api_get_products():
    """Returns a list of all products in JSON format."""
    products = db.get_all_products_db();
    products_list = [dict(p) for p in products];
    return jsonify(products_list)


@app.route('/api/products/<string:name>', methods=['GET'])
def api_get_product_by_name(name):
    """Returns a specific product by name in JSON format."""
    product = db.get_product_by_name_db(name);
    if product: return jsonify(dict(product))
    return jsonify({"error": "Product not found"}), 404


if __name__ == '__main__':
    print("-" * 68);
    print("POS System Starting...")
    print(f"DB: '{DATABASE_FILE}'. Run 'python database_setup.py' if needed.")
    print(f"Backups: '{os.path.abspath(BACKUP_DIR)}'.")
    print(f"URL: http://127.0.0.1:5000");
    print("-" * 68)
    app.run(debug=True)  # debug=True is for development, set to False for production
