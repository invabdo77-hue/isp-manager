from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'isp_manager_secret_key_2024')

DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)

print(f"[DEBUG] DATABASE_URL exists: {bool(DATABASE_URL)}")
print(f"[DEBUG] USE_POSTGRES: {USE_POSTGRES}")

def get_db():
    if USE_POSTGRES:
        import psycopg2
        import psycopg2.extras
        url = DATABASE_URL
        if 'sslmode' not in url.lower():
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}sslmode=require"
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        DATABASE = os.path.join(os.path.dirname(__file__), 'isp_manager.db')
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn

def get_placeholder():
    return '%s' if USE_POSTGRES else '?'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()
        cur.execute(f'SELECT * FROM users WHERE id = {ph}', (user_id,))
        user = cur.fetchone()
        conn.close()
        if user:
            print(f"[DEBUG] User loaded: {user['username']}, role: {user['role']}")
            return User(user['id'], user['username'], user['role'])
    except Exception as e:
        print(f"[ERROR] load_user: {e}")
    return None

def require_admin(f):
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acceso solo para administradores', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@app.route('/setup')
def setup():
    try:
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()

        if USE_POSTGRES:
            cur.execute('''CREATE TABLE IF NOT EXISTS plans (
                id SERIAL PRIMARY KEY, name TEXT NOT NULL, speed TEXT NOT NULL,
                price REAL NOT NULL, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL, role TEXT DEFAULT 'technician',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS clients (
                id SERIAL PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
                cedula TEXT, phone TEXT, email TEXT, address TEXT, router_model TEXT,
                router_serial TEXT, router_mac TEXT, ip_address TEXT, nap_number TEXT,
                potencia TEXT, plan_id INTEGER, connection_status TEXT DEFAULT 'active',
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS monthly_payments (
                id SERIAL PRIMARY KEY, client_id INTEGER NOT NULL, amount REAL NOT NULL,
                month TEXT NOT NULL, payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                method TEXT DEFAULT 'efectivo', status TEXT DEFAULT 'paid', notes TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS other_incomes (
                id SERIAL PRIMARY KEY, description TEXT NOT NULL, amount REAL NOT NULL,
                category TEXT DEFAULT 'otro', income_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notes TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY, description TEXT NOT NULL, amount REAL NOT NULL,
                category TEXT DEFAULT 'otro', expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notes TEXT)''')
        else:
            cur.execute('''CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, speed TEXT NOT NULL,
                price REAL NOT NULL, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL, role TEXT DEFAULT 'technician',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
                cedula TEXT, phone TEXT, email TEXT, address TEXT, router_model TEXT,
                router_serial TEXT, router_mac TEXT, ip_address TEXT, nap_number TEXT,
                potencia TEXT, plan_id INTEGER, connection_status TEXT DEFAULT 'active',
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS monthly_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, amount REAL NOT NULL,
                month TEXT NOT NULL, payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                method TEXT DEFAULT 'efectivo', status TEXT DEFAULT 'paid', notes TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS other_incomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT NOT NULL, amount REAL NOT NULL,
                category TEXT DEFAULT 'otro', income_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notes TEXT)''')
            cur.execute('''CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT NOT NULL, amount REAL NOT NULL,
                category TEXT DEFAULT 'otro', expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notes TEXT)''')

        cur.execute(f'SELECT COUNT(*) FROM users')
        if cur.fetchone()[0] == 0:
            password_hash = generate_password_hash('admin123')
            cur.execute(f"INSERT INTO users (username, password, role) VALUES ({ph}, {ph}, {ph})",
                       ('admin', password_hash, 'admin'))
            password_hash2 = generate_password_hash('tecnico123')
            cur.execute(f"INSERT INTO users (username, password, role) VALUES ({ph}, {ph}, {ph})",
                       ('tecnico1', password_hash2, 'technician'))

        cur.execute(f'SELECT COUNT(*) FROM plans')
        if cur.fetchone()[0] == 0:
            cur.execute(f"INSERT INTO plans (name, speed, price, description) VALUES ({ph}, {ph}, {ph}, {ph})", ('100 Mbps', '100 Mbps', 25.00, 'Plan 100 Mbps'))
            cur.execute(f"INSERT INTO plans (name, speed, price, description) VALUES ({ph}, {ph}, {ph}, {ph})", ('200 Mbps', '200 Mbps', 30.00, 'Plan 200 Mbps'))
            cur.execute(f"INSERT INTO plans (name, speed, price, description) VALUES ({ph}, {ph}, {ph}, {ph})", ('300 Mbps', '300 Mbps', 40.00, 'Plan 300 Mbps'))

        conn.commit()
        conn.close()
        return f"OK! DB initialized (PostgreSQL: {USE_POSTGRES})", 200
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/reset-users')
def reset_users():
    try:
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()
        cur.execute(f"DELETE FROM users")
        password_hash = generate_password_hash('admin123')
        cur.execute(f"INSERT INTO users (username, password, role) VALUES ({ph}, {ph}, {ph})",
                   ('admin', password_hash, 'admin'))
        password_hash2 = generate_password_hash('tecnico123')
        cur.execute(f"INSERT INTO users (username, password, role) VALUES ({ph}, {ph}, {ph})",
                   ('tecnico1', password_hash2, 'technician'))
        conn.commit()
        conn.close()
        return "OK! Users created: admin/admin123 y tecnico1/tecnico123"
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/debug-db')
def debug_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT id, username, role FROM users')
        users = cur.fetchall()
        conn.close()
        html = '<h1>Users in DB:</h1><ul>'
        for u in users:
            html += f"<li>ID: {u['id']}, User: {u['username']}, Role: {u['role']}</li>"
        html += '</ul>'
        return html
    except Exception as e:
        return f"Error: {e}"

@app.route('/')
@login_required
def index():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM clients')
    total_clients = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clients WHERE connection_status = 'active'")
    active_clients = cur.fetchone()[0]
    cur.execute('''SELECT c.*, p.name as plan_name, p.price as plan_price
        FROM clients c LEFT JOIN plans p ON c.plan_id = p.id
        ORDER BY c.registration_date DESC LIMIT 5''')
    recent_clients = cur.fetchall()
    conn.close()
    return render_template('index.html', total_clients=total_clients, active_clients=active_clients, recent_clients=recent_clients)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        print(f"[DEBUG] Login attempt: {username}")
        try:
            conn = get_db()
            cur = conn.cursor()
            ph = get_placeholder()
            cur.execute(f"SELECT * FROM users WHERE username = {ph}", (username,))
            user = cur.fetchone()
            conn.close()
            print(f"[DEBUG] User found: {user is not None}")
            if user:
                print(f"[DEBUG] Stored hash: {user['password'][:50]}...")
                print(f"[DEBUG] check_password_hash result: {check_password_hash(user['password'], password)}")
            if user and check_password_hash(user['password'], password):
                login_user(User(user['id'], user['username'], user['role']))
                return redirect(url_for('index'))
            flash('Usuario o contraseña incorrectos', 'danger')
        except Exception as e:
            print(f"[ERROR] Login: {e}")
            flash(f'Error: {e}', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/clients')
@login_required
def clients_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''SELECT c.*, p.name as plan_name, p.speed as plan_speed, p.price as plan_price
        FROM clients c LEFT JOIN plans p ON c.plan_id = p.id
        ORDER BY c.first_name, c.last_name''')
    clients = cur.fetchall()
    conn.close()
    return render_template('clients.html', clients=clients)

@app.route('/clients/new', methods=['GET', 'POST'])
@login_required
def client_new():
    if request.method == 'POST':
        conn = get_db()
        cur = conn.cursor()
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        vals = [first_name, last_name]
        cols = ['first_name', 'last_name']

        for field in ['cedula', 'phone', 'email', 'address', 'router_model', 'router_serial',
                      'router_mac', 'ip_address', 'nap_number', 'potencia']:
            if request.form.get(field):
                vals.append(request.form.get(field))
                cols.append(field)

        if request.form.get('plan_id'):
            vals.append(int(request.form.get('plan_id')))
            cols.append('plan_id')

        vals.append(request.form.get('connection_status', 'active') if current_user.role == 'admin' else 'active')
        cols.append('connection_status')

        ph = get_placeholder()
        placeholders = ','.join([ph] * len(cols))
        sql = f'INSERT INTO clients ({", ".join(cols)}) VALUES ({placeholders})'
        cur.execute(sql, vals)
        conn.commit()
        conn.close()
        flash('Cliente creado exitosamente', 'success')
        return redirect(url_for('clients_list'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM plans ORDER BY price')
    plans = cur.fetchall()
    conn.close()
    return render_template('client_form.html', plans=plans, client=None)

@app.route('/clients/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def client_edit(id):
    conn = get_db()
    if request.method == 'POST':
        cur = conn.cursor()
        updates = []
        values = []
        for field in ['first_name', 'last_name', 'cedula', 'phone', 'email', 'address',
                      'router_model', 'router_serial', 'router_mac', 'ip_address',
                      'nap_number', 'potencia', 'plan_id', 'connection_status']:
            if request.form.get(field):
                updates.append(f'{field}={get_placeholder()}')
                val = request.form.get(field)
                if field == 'plan_id':
                    val = int(val)
                values.append(val)
        if updates:
            values.append(id)
            cur.execute(f'UPDATE clients SET {", ".join(updates)} WHERE id={get_placeholder()}', values)
            conn.commit()
        conn.close()
        flash('Cliente actualizado', 'success')
        return redirect(url_for('clients_list'))

    cur = conn.cursor()
    cur.execute(f'SELECT * FROM clients WHERE id = {get_placeholder()}', (id,))
    client = cur.fetchone()
    cur.execute('SELECT * FROM plans ORDER BY price')
    plans = cur.fetchall()
    conn.close()
    return render_template('client_form.html', plans=plans, client=client)

@app.route('/clients/<int:id>/delete', methods=['POST'])
@login_required
@require_admin
def client_delete(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f'DELETE FROM clients WHERE id = {get_placeholder()}', (id,))
    conn.commit()
    conn.close()
    flash('Cliente eliminado', 'success')
    return redirect(url_for('clients_list'))

@app.route('/plans')
@login_required
@require_admin
def plans_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''SELECT p.*, COUNT(c.id) as client_count
        FROM plans p LEFT JOIN clients c ON p.id = c.plan_id
        GROUP BY p.id ORDER BY p.price''')
    plans = cur.fetchall()
    conn.close()
    return render_template('plans.html', plans=plans)

@app.route('/plans/new', methods=['GET', 'POST'])
@login_required
@require_admin
def plan_new():
    if request.method == 'POST':
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()
        cur.execute(f'INSERT INTO plans (name, speed, price, description) VALUES ({ph}, {ph}, {ph}, {ph})',
                   (request.form['name'], request.form['speed'], float(request.form['price']), request.form.get('description')))
        conn.commit()
        conn.close()
        flash('Plan creado', 'success')
        return redirect(url_for('plans_list'))
    return render_template('plan_form.html', plan=None)

@app.route('/plans/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_admin
def plan_edit(id):
    conn = get_db()
    ph = get_placeholder()
    if request.method == 'POST':
        cur = conn.cursor()
        cur.execute(f'UPDATE plans SET name={ph}, speed={ph}, price={ph}, description={ph} WHERE id={ph}',
                   (request.form['name'], request.form['speed'], float(request.form['price']), request.form.get('description'), id))
        conn.commit()
        conn.close()
        flash('Plan actualizado', 'success')
        return redirect(url_for('plans_list'))
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM plans WHERE id = {ph}', (id,))
    plan = cur.fetchone()
    conn.close()
    return render_template('plan_form.html', plan=plan)

@app.route('/plans/<int:id>/delete', methods=['POST'])
@login_required
@require_admin
def plan_delete(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f'DELETE FROM plans WHERE id = {get_placeholder()}', (id,))
    conn.commit()
    conn.close()
    flash('Plan eliminado', 'success')
    return redirect(url_for('plans_list'))

@app.route('/export/plans')
@login_required
def export_plans():
    from openpyxl import Workbook
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM plans ORDER BY price')
    plans = cur.fetchall()
    conn.close()
    wb = Workbook()
    ws = wb.active
    ws.append(['ID', 'Nombre', 'Velocidad', 'Precio', 'Descripcion'])
    for p in plans:
        ws.append([p['id'], p['name'], p['speed'], p['price'], p['description']])
    from io import BytesIO
    output = BytesIO()
    wb.save(output)
    from flask import make_response
    return make_response(output.getvalue(), {'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Content-Disposition': 'attachment; filename=planes.xlsx'})

@app.route('/finances')
@login_required
@require_admin
def finances():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM monthly_payments WHERE status = 'paid'")
    total_monthly = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM other_incomes")
    total_other_incomes = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses")
    total_expenses = cur.fetchone()[0]
    balance = total_monthly + total_other_incomes - total_expenses

    cur.execute('''SELECT mp.*, c.first_name, c.last_name, p.name as plan_name
        FROM monthly_payments mp JOIN clients c ON mp.client_id = c.id
        LEFT JOIN plans p ON c.plan_id = p.id ORDER BY mp.payment_date DESC''')
    monthly_payments = cur.fetchall()

    cur.execute('SELECT * FROM other_incomes ORDER BY income_date DESC')
    other_incomes = cur.fetchall()
    cur.execute('SELECT * FROM expenses ORDER BY expense_date DESC')
    expenses = cur.fetchall()
    conn.close()
    return render_template('finances.html', total_monthly=total_monthly, total_other_incomes=total_other_incomes,
                         total_expenses=total_expenses, balance=balance, monthly_payments=monthly_payments,
                         other_incomes=other_incomes, expenses=expenses)

@app.route('/finances/payment/new', methods=['GET', 'POST'])
@login_required
@require_admin
def payment_new():
    if request.method == 'POST':
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()
        cur.execute(f'INSERT INTO monthly_payments (client_id, amount, month, payment_date, method, status, notes) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})',
                   (int(request.form['client_id']), float(request.form['amount']), request.form['month'],
                    request.form.get('payment_date', datetime.now().strftime('%Y-%m-%d')),
                    request.form.get('method', 'efectivo'), 'paid', request.form.get('notes')))
        client_id = int(request.form['client_id'])
        cur.execute(f"UPDATE clients SET connection_status = 'active' WHERE id = {ph} AND connection_status = 'cut'", (client_id,))
        conn.commit()
        conn.close()
        flash('Pago registrado', 'success')
        return redirect(url_for('finances'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, first_name, last_name FROM clients ORDER BY first_name, last_name')
    clients = cur.fetchall()
    conn.close()
    return render_template('payment_form.html', clients=clients, current_month=datetime.now().strftime('%Y-%m'), payment=None)

@app.route('/finances/income/new', methods=['GET', 'POST'])
@login_required
@require_admin
def income_new():
    if request.method == 'POST':
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()
        cur.execute(f'INSERT INTO other_incomes (description, amount, category, income_date, notes) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})',
                   (request.form['description'], float(request.form['amount']), request.form.get('category', 'otro'),
                    request.form.get('income_date', datetime.now().strftime('%Y-%m-%d')), request.form.get('notes')))
        conn.commit()
        conn.close()
        flash('Ingreso registrado', 'success')
        return redirect(url_for('finances'))
    return render_template('income_form.html', income=None)

@app.route('/finances/expense/new', methods=['GET', 'POST'])
@login_required
@require_admin
def expense_new():
    if request.method == 'POST':
        conn = get_db()
        cur = conn.cursor()
        ph = get_placeholder()
        cur.execute(f'INSERT INTO expenses (description, amount, category, expense_date, notes) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})',
                   (request.form['description'], float(request.form['amount']), request.form.get('category', 'otro'),
                    request.form.get('expense_date', datetime.now().strftime('%Y-%m-%d')), request.form.get('notes')))
        conn.commit()
        conn.close()
        flash('Gasto registrado', 'success')
        return redirect(url_for('finances'))
    return render_template('expense_form.html', expense=None)

@app.route('/finances/client/<int:id>/payments')
@login_required
@require_admin
def client_payments(id):
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f'SELECT * FROM clients WHERE id = {ph}', (id,))
    client = cur.fetchone()
    cur.execute(f'SELECT * FROM monthly_payments WHERE client_id = {ph} ORDER BY payment_date DESC', (id,))
    payments = cur.fetchall()
    conn.close()
    return render_template('client_payments.html', client=client, payments=payments)

@app.route('/api/clients/search')
@login_required
def api_client_search():
    query = request.args.get('q', '')
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f'SELECT id, first_name, last_name, cedula FROM clients WHERE first_name LIKE {ph} OR last_name LIKE {ph} OR cedula LIKE {ph} LIMIT 10',
               (f'%{query}%', f'%{query}%', f'{query}%'))
    results = cur.fetchall()
    conn.close()
    return jsonify([dict(c) for c in results])

@app.route('/export/clients')
@login_required
def export_clients():
    from openpyxl import Workbook
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''SELECT c.*, p.name as plan_name, p.speed as plan_speed, p.price as plan_price
        FROM clients c LEFT JOIN plans p ON c.plan_id = p.id''')
    clients = cur.fetchall()
    conn.close()
    wb = Workbook()
    ws = wb.active
    ws.append(['ID', 'Nombre', 'Apellido', 'Cedula', 'Telefono', 'Email', 'Direccion', 'Router', 'Serial', 'MAC', 'IP', 'NAP', 'Potencia', 'Plan', 'Velocidad', 'Precio', 'Estado', 'Fecha'])
    for c in clients:
        ws.append([c['id'], c['first_name'], c['last_name'], c['cedula'], c['phone'], c['email'], c['address'], c['router_model'], c['router_serial'], c['router_mac'], c['ip_address'], c['nap_number'], c['potencia'], c['plan_name'], c['plan_speed'], c['plan_price'], c['connection_status'], c['registration_date']])
    from io import BytesIO
    from flask import make_response
    output = BytesIO()
    wb.save(output)
    return make_response(output.getvalue(), {'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Content-Disposition': 'attachment; filename=clientes.xlsx'})

@app.route('/import/clients', methods=['POST'])
@login_required
@require_admin
def import_clients():
    from openpyxl import load_workbook
    if 'file' not in request.files:
        flash('No se selecciono archivo', 'danger')
        return redirect(url_for('clients_list'))
    file = request.files['file']
    wb = load_workbook(file)
    ws = wb.active
    conn = get_db()
    cur = conn.cursor()
    ph = get_placeholder()
    imported = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            try:
                cur.execute(f'''INSERT INTO clients (first_name, last_name, cedula, phone, email, address, plan_id, connection_status)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})''', (row[1], row[2], row[3], row[4], row[5], row[6], None, 'active'))
                imported += 1
            except:
                pass
    conn.commit()
    conn.close()
    flash(f'{imported} clientes importados', 'success')
    return redirect(url_for('clients_list'))

@app.route('/export/finances')
@login_required
@require_admin
def export_finances():
    from openpyxl import Workbook
    conn = get_db()
    cur = conn.cursor()
    wb = Workbook()
    ws = wb.active
    ws.title = "Pagos"
    ws.append(['ID', 'Cliente', 'Monto', 'Mes', 'Fecha', 'Metodo', 'Estado'])
    cur.execute('SELECT mp.*, c.first_name, c.last_name FROM monthly_payments mp JOIN clients c ON mp.client_id = c.id')
    for p in cur.fetchall():
        ws.append([p['id'], f"{p['first_name']} {p['last_name']}", p['amount'], p['month'], p['payment_date'], p['method'], p['status']])
    ws2 = wb.create_sheet("Ingresos")
    ws2.append(['ID', 'Descripcion', 'Monto', 'Categoria', 'Fecha'])
    cur.execute('SELECT * FROM other_incomes')
    for i in cur.fetchall():
        ws2.append([i['id'], i['description'], i['amount'], i['category'], i['income_date']])
    ws3 = wb.create_sheet("Gastos")
    ws3.append(['ID', 'Descripcion', 'Monto', 'Categoria', 'Fecha'])
    cur.execute('SELECT * FROM expenses')
    for e in cur.fetchall():
        ws3.append([e['id'], e['description'], e['amount'], e['category'], e['expense_date']])
    conn.close()
    from io import BytesIO
    output = BytesIO()
    wb.save(output)
    from flask import make_response
    return make_response(output.getvalue(), {'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Content-Disposition': 'attachment; filename=finanzas.xlsx'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=not USE_POSTGRES, host='0.0.0.0', port=port)