import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'isp_manager.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def check_and_cut_clients():
    conn = get_db()
    cursor = conn.cursor()
    
    current_month = datetime.now().strftime('%Y-%m')
    
    cursor.execute('''
        SELECT c.id
        FROM clients c
        WHERE c.connection_status = 'active'
        AND c.id NOT IN (
            SELECT client_id FROM monthly_payments 
            WHERE month = ? AND status = 'paid'
        )
    ''', (current_month,))
    
    clients_to_cut = cursor.fetchall()
    
    for client in clients_to_cut:
        cursor.execute('UPDATE clients SET connection_status = ? WHERE id = ?', ('cut', client['id']))
    
    conn.commit()
    conn.close()
    return len(clients_to_cut)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            speed TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
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
            plan_id INTEGER,
            connection_status TEXT DEFAULT 'active' CHECK(connection_status IN ('active', 'suspended', 'inactive', 'cut')),
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        );
        
        CREATE TABLE IF NOT EXISTS monthly_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            month TEXT NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            method TEXT DEFAULT 'efectivo',
            status TEXT DEFAULT 'paid' CHECK(status IN ('paid', 'pending')),
            notes TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
        
        CREATE TABLE IF NOT EXISTS other_incomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'otro',
            income_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );
        
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT DEFAULT 'otro',
            expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );
        
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'technician' CHECK(role IN ('admin', 'technician')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    cursor.executescript('''
        DELETE FROM plans;
        INSERT INTO plans (name, speed, price, description) VALUES
            ('100 Mbps', '100 Mbps', 25.00, 'Plan 100 Mbps'),
            ('200 Mbps', '200 Mbps', 30.00, 'Plan 200 Mbps'),
            ('300 Mbps', '300 Mbps', 40.00, 'Plan 300 Mbps');
    ''')
    
    conn.commit()
    conn.close()

def create_default_users():
    from werkzeug.security import generate_password_hash
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM users')
    if cursor.fetchone()['count'] == 0:
        cursor.execute('''
            INSERT INTO users (username, password, role) VALUES (?, ?, ?)
        ''', ('admin', generate_password_hash('admin123'), 'admin'))
        cursor.execute('''
            INSERT INTO users (username, password, role) VALUES (?, ?, ?)
        ''', ('tecnico1', generate_password_hash('tecnico123'), 'technician'))
        conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")