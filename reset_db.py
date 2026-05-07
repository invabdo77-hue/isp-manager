import sqlite3
import os

DB_PATH = 'isp_manager.db'
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("Deleted old DB")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute('''CREATE TABLE plans (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    speed TEXT NOT NULL,
    price REAL NOT NULL,
    description TEXT
)''')

c.execute('''CREATE TABLE clients (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    cedula TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    router_model TEXT,
    router_serial TEXT,
    router_mac TEXT,
    ip_address TEXT,
    nap_number TEXT,
    potencia TEXT,
    plan_id INTEGER,
    connection_status TEXT DEFAULT 'active',
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

c.execute('''CREATE TABLE monthly_payments (
    id INTEGER PRIMARY KEY,
    client_id INTEGER,
    amount REAL,
    month TEXT,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    method TEXT DEFAULT 'efectivo',
    status TEXT DEFAULT 'paid',
    notes TEXT
)''')

c.execute('''CREATE TABLE other_incomes (
    id INTEGER PRIMARY KEY,
    description TEXT,
    amount REAL,
    category TEXT,
    income_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
)''')

c.execute('''CREATE TABLE expenses (
    id INTEGER PRIMARY KEY,
    description TEXT,
    amount REAL,
    category TEXT,
    expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
)''')

c.execute("INSERT INTO plans VALUES (NULL, '100 Mbps', '100 Mbps', 25, 'Plan 100 Mbps')")
c.execute("INSERT INTO plans VALUES (NULL, '200 Mbps', '200 Mbps', 30, 'Plan 200 Mbps')")
c.execute("INSERT INTO plans VALUES (NULL, '300 Mbps', '300 Mbps', 40, 'Plan 300 Mbps')")

conn.commit()
conn.close()
print("Database created OK")