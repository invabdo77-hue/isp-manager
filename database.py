import sqlite3
import os
from datetime import datetime
from flask import g

DB_PATH = os.path.join(os.path.dirname(__file__), 'isp_manager.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            speed TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            cedula TEXT UNIQUE,
            phone TEXT,
            email TEXT,
            address TEXT,
            router_model TEXT,
            router_serial TEXT,
            router_mac TEXT,
            ip_address TEXT,
            nap_number TEXT,
            potencia TEXT,
            plan_id INTEGER REFERENCES plans(id),
            connection_status TEXT DEFAULT 'active' CHECK(connection_status IN ('active', 'suspended', 'inactive', 'cut')),
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS monthly_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            amount REAL NOT NULL,
            month TEXT NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            method TEXT DEFAULT 'efectivo',
            status TEXT DEFAULT 'paid' CHECK(status IN ('paid', 'pending')),
            notes TEXT
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS other_incomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'otro',
            income_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'otro',
            expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'technician' CHECK(role IN ('admin', 'technician')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute("DELETE FROM plans")
    cur.execute("INSERT INTO plans (name, speed, price, description) VALUES ('100 Mbps', '100 Mbps', 25.00, 'Plan 100 Mbps')")
    cur.execute("INSERT INTO plans (name, speed, price, description) VALUES ('200 Mbps', '200 Mbps', 30.00, 'Plan 200 Mbps')")
    cur.execute("INSERT INTO plans (name, speed, price, description) VALUES ('300 Mbps', '300 Mbps', 40.00, 'Plan 300 Mbps')")
    
    conn.commit()

def create_default_users():
    from werkzeug.security import generate_password_hash
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as count FROM users')
    if cur.fetchone()['count'] == 0:
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', generate_password_hash('admin123'), 'admin'))
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('tecnico1', generate_password_hash('tecnico123'), 'technician'))
        conn.commit()

def check_and_cut_clients():
    conn = get_db()
    cur = conn.cursor()
    current_month = datetime.now().strftime('%Y-%m')
    cur.execute('''
        SELECT c.id FROM clients c
        WHERE c.connection_status = 'active'
        AND c.id NOT IN (
            SELECT client_id FROM monthly_payments 
            WHERE month = ? AND status = 'paid'
        )
    ''', (current_month,))
    clients_to_cut = cur.fetchall()
    for client in clients_to_cut:
        cur.execute('UPDATE clients SET connection_status = ? WHERE id = ?', ('cut', client['id']))
    conn.commit()
    return len(clients_to_cut)

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")