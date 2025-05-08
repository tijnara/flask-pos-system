# Description: This script creates the SQLite database and tables if they don't already exist.
# Run this script once initially to set up your database.

import sqlite3

def create_connection(db_file):
    """ Create a database connection to the SQLite database specified by db_file """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"SQLite version: {sqlite3.sqlite_version}")
        print(f"Successfully connected to {db_file}")
    except sqlite3.Error as e:
        print(e)
    return conn

def create_tables(conn):
    """ Create tables from the schema """
    sql_create_customers_table = """
    CREATE TABLE IF NOT EXISTS Customers (
        CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
        CustomerName TEXT NOT NULL UNIQUE COLLATE NOCASE,
        ContactNumber TEXT,
        Address TEXT,
        DateAdded TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """

    sql_create_products_table = """
    CREATE TABLE IF NOT EXISTS Products (
        ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
        ProductName TEXT NOT NULL UNIQUE,
        Price REAL NOT NULL CHECK (Price >= 0)
    );
    """

    sql_create_sales_table = """
    CREATE TABLE IF NOT EXISTS Sales (
        SaleID INTEGER PRIMARY KEY AUTOINCREMENT,
        SaleTimestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        TotalAmount REAL NOT NULL CHECK (TotalAmount >= 0),
        CustomerName TEXT DEFAULT 'N/A',
        FOREIGN KEY (CustomerName) REFERENCES Customers (CustomerName) ON DELETE SET DEFAULT ON UPDATE CASCADE
    );
    """
    # Note: For CustomerName in Sales, if you want to link to CustomerID,
    # it should be CustomerID INTEGER and then a FOREIGN KEY to Customers(CustomerID).
    # Using CustomerName as a foreign key is possible but less robust than using an ID.
    # For simplicity with the provided schema, I'm keeping it as CustomerName.

    sql_create_sale_items_table = """
    CREATE TABLE IF NOT EXISTS SaleItems (
        SaleItemID INTEGER PRIMARY KEY AUTOINCREMENT,
        SaleID INTEGER NOT NULL,
        ProductName TEXT NOT NULL,
        Quantity INTEGER NOT NULL CHECK (Quantity > 0),
        PriceAtSale REAL NOT NULL,
        Subtotal REAL NOT NULL,
        FOREIGN KEY (SaleID) REFERENCES Sales (SaleID) ON DELETE CASCADE,
        FOREIGN KEY (ProductName) REFERENCES Products (ProductName) ON UPDATE CASCADE
    );
    """
    # Note: Similar to Sales.CustomerName, SaleItems.ProductName as a FOREIGN KEY
    # refers to Products.ProductName. Using ProductID would be more standard.

    try:
        cursor = conn.cursor()
        print("Creating table Customers...")
        cursor.execute(sql_create_customers_table)
        print("Creating table Products...")
        cursor.execute(sql_create_products_table)
        print("Creating table Sales...")
        cursor.execute(sql_create_sales_table)
        print("Creating table SaleItems...")
        cursor.execute(sql_create_sale_items_table)
        conn.commit()
        print("Tables created successfully.")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")

if __name__ == '__main__':
    db_file = "pos_system.db"
    conn = create_connection(db_file)
    if conn is not None:
        create_tables(conn)
        conn.close()
    else:
        print("Error! Cannot create the database connection.")