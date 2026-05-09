from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import psycopg2
import psycopg2.extras
import os
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'isp_manager_secret_key_2024'

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    if 'db' not in g:
        if not DATABASE_URL:
            return None
        url = DATABASE_URL
        if 'sslmode' not in url.lower():
            url += '?sslmode=require' if '?' not in url else '&sslmode=require'
        g.db = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

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
    db = get_db()
    if not db:
        return None
    try:
        cur = db.cursor()
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()
        if user:
            return User(user['id'], user['username'], user['role'])
    except:
        pass
    return None

def require_admin(f):
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acceso solo para administradores', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@app.route('/health')
def health():
    db = get_db()
    if db:
        return "OK", 200
    return "Error", 500

@app.route('/setup')
def setup():
    if not DATABASE_URL:
        return "DATABASE_URL no configurada", 500
    try:
        db = psycopg2.connect(DATABASE_URL + ('?sslmode=require' if '?' not in DATABASE_URL else '&sslmode=require'))
        cur = db.cursor()
        
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
        
        cur.execute('SELECT COUNT(*) FROM users')
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                       ('adminisp', generate_password_hash('adminisp123'), 'admin'))
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                       ('tecnico1', generate_password_hash('tecnico123'), 'technician'))
        
        cur.execute('SELECT COUNT(*) FROM plans')
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO plans (name, speed, price, description) VALUES ('100 Mbps', '100 Mbps', 25.00, 'Plan 100 Mbps')")
            cur.execute("INSERT INTO plans (name, speed, price, description) VALUES ('200 Mbps', '200 Mbps', 30.00, 'Plan 200 Mbps')")
            cur.execute("INSERT INTO plans (name, speed, price, description) VALUES ('300 Mbps', '300 Mbps', 40.00, 'Plan 300 Mbps')")
        
        db.commit()
        cur.close()
        db.close()
        return "Base de datos inicializada correctamente!", 200
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/')
@login_required
def index():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT COUNT(*) FROM clients')
    total_clients = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clients WHERE connection_status = 'active'")
    active_clients = cur.fetchone()[0]
    cur.execute('''SELECT c.*, p.name as plan_name, p.price as plan_price
        FROM clients c LEFT JOIN plans p ON c.plan_id = p.id
        ORDER BY c.registration_date DESC LIMIT 5''')
    recent_clients = cur.fetchall()
    return render_template('index.html', total_clients=total_clients, active_clients=active_clients, recent_clients=recent_clients)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            db = get_db()
            if not db:
                flash('Error de conexión', 'danger')
                return render_template('login.html')
            cur = db.cursor()
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user and check_password_hash(user['password'], password):
                login_user(User(user['id'], user['username'], user['role']))
                return redirect(url_for('index'))
            flash('Usuario o contraseña incorrectos', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/clients')
@login_required
def clients_list():
    db = get_db()
    cur = db.cursor()
    cur.execute('''SELECT c.*, p.name as plan_name, p.speed as plan_speed, p.price as plan_price
        FROM clients c LEFT JOIN plans p ON c.plan_id = p.id
        ORDER BY c.first_name, c.last_name''')
    clients = cur.fetchall()
    return render_template('clients.html', clients=clients)

@app.route('/clients/new', methods=['GET', 'POST'])
@login_required
def client_new():
    db = get_db()
    if request.method == 'POST':
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
        
        sql = 'INSERT INTO clients (' + ', '.join(cols) + ') VALUES (' + ','.join(['%s']*len(cols)) + ')'
        cur = db.cursor()
        cur.execute(sql, vals)
        db.commit()
        flash('Cliente creado exitosamente', 'success')
        return redirect(url_for('clients_list'))
    
    cur = db.cursor()
    cur.execute('SELECT * FROM plans ORDER BY price')
    plans = cur.fetchall()
    return render_template('client_form.html', plans=plans, client=None)

@app.route('/clients/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_admin
def client_edit(id):
    db = get_db()
    if request.method == 'POST':
        updates = []
        values = []
        for field in ['first_name', 'last_name', 'cedula', 'phone', 'email', 'address',
                      'router_model', 'router_serial', 'router_mac', 'ip_address',
                      'nap_number', 'potencia', 'plan_id', 'connection_status']:
            if request.form.get(field):
                updates.append(f'{field}=%s')
                val = request.form.get(field)
                if field == 'plan_id':
                    val = int(val)
                values.append(val)
        if updates:
            values.append(id)
            cur = db.cursor()
            cur.execute('UPDATE clients SET ' + ', '.join(updates) + ' WHERE id=%s', values)
            db.commit()
        flash('Cliente actualizado', 'success')
        return redirect(url_for('clients_list'))
    
    cur = db.cursor()
    cur.execute('SELECT * FROM clients WHERE id = %s', (id,))
    client = cur.fetchone()
    cur.execute('SELECT * FROM plans ORDER BY price')
    plans = cur.fetchall()
    return render_template('client_form.html', plans=plans, client=client)

@app.route('/clients/<int:id>/delete', methods=['POST'])
@login_required
@require_admin
def client_delete(id):
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM clients WHERE id = %s', (id,))
    db.commit()
    flash('Cliente eliminado', 'success')
    return redirect(url_for('clients_list'))

@app.route('/plans')
@login_required
@require_admin
def plans_list():
    db = get_db()
    cur = db.cursor()
    cur.execute('''SELECT p.*, COUNT(c.id) as client_count
        FROM plans p LEFT JOIN clients c ON p.id = c.plan_id
        GROUP BY p.id ORDER BY p.price''')
    plans = cur.fetchall()
    return render_template('plans.html', plans=plans)

@app.route('/plans/new', methods=['GET', 'POST'])
@login_required
@require_admin
def plan_new():
    if request.method == 'POST':
        db = get_db()
        cur = db.cursor()
        cur.execute('INSERT INTO plans (name, speed, price, description) VALUES (%s, %s, %s, %s)',
                   (request.form['name'], request.form['speed'], float(request.form['price']), request.form.get('description')))
        db.commit()
        flash('Plan creado', 'success')
        return redirect(url_for('plans_list'))
    return render_template('plan_form.html', plan=None)

@app.route('/plans/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_admin
def plan_edit(id):
    db = get_db()
    if request.method == 'POST':
        cur = db.cursor()
        cur.execute('UPDATE plans SET name=%s, speed=%s, price=%s, description=%s WHERE id=%s',
                   (request.form['name'], request.form['speed'], float(request.form['price']), request.form.get('description'), id))
        db.commit()
        flash('Plan actualizado', 'success')
        return redirect(url_for('plans_list'))
    cur = db.cursor()
    cur.execute('SELECT * FROM plans WHERE id = %s', (id,))
    return render_template('plan_form.html', plan=cur.fetchone())

@app.route('/plans/<int:id>/delete', methods=['POST'])
@login_required
@require_admin
def plan_delete(id):
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM plans WHERE id = %s', (id,))
    db.commit()
    flash('Plan eliminado', 'success')
    return redirect(url_for('plans_list'))

@app.route('/finances')
@login_required
@require_admin
def finances():
    db = get_db()
    cur = db.cursor()
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
    cur.execute('SELECT category, SUM(amount) FROM other_incomes GROUP BY category')
    income_by_category = cur.fetchall()
    cur.execute('SELECT category, SUM(amount) FROM expenses GROUP BY category')
    expense_by_category = cur.fetchall()
    
    return render_template('finances.html', total_monthly=total_monthly, total_other_incomes=total_other_incomes,
                         total_expenses=total_expenses, balance=balance, monthly_payments=monthly_payments,
                         other_incomes=other_incomes, expenses=expenses, income_by_category=income_by_category,
                         expense_by_category=expense_by_category)

@app.route('/finances/payment/new', methods=['GET', 'POST'])
@login_required
@require_admin
def payment_new():
    db = get_db()
    if request.method == 'POST':
        cur = db.cursor()
        cur.execute('INSERT INTO monthly_payments (client_id, amount, month, payment_date, method, status, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                   (int(request.form['client_id']), float(request.form['amount']), request.form['month'],
                    request.form.get('payment_date', datetime.now().strftime('%Y-%m-%d')),
                    request.form.get('method', 'efectivo'), 'paid', request.form.get('notes')))
        client_id = int(request.form['client_id'])
        cur.execute("UPDATE clients SET connection_status = 'active' WHERE id = %s AND connection_status = 'cut'", (client_id,))
        db.commit()
        flash('Pago registrado', 'success')
        return redirect(url_for('finances'))
    cur = db.cursor()
    cur.execute('SELECT id, first_name, last_name FROM clients ORDER BY first_name, last_name')
    return render_template('payment_form.html', clients=cur.fetchall(), current_month=datetime.now().strftime('%Y-%m'), payment=None)

@app.route('/finances/income/new', methods=['GET', 'POST'])
@login_required
@require_admin
def income_new():
    if request.method == 'POST':
        db = get_db()
        cur = db.cursor()
        cur.execute('INSERT INTO other_incomes (description, amount, category, income_date, notes) VALUES (%s, %s, %s, %s, %s)',
                   (request.form['description'], float(request.form['amount']), request.form.get('category', 'otro'),
                    request.form.get('income_date', datetime.now().strftime('%Y-%m-%d')), request.form.get('notes')))
        db.commit()
        flash('Ingreso registrado', 'success')
        return redirect(url_for('finances'))
    return render_template('income_form.html', income=None)

@app.route('/finances/expense/new', methods=['GET', 'POST'])
@login_required
@require_admin
def expense_new():
    if request.method == 'POST':
        db = get_db()
        cur = db.cursor()
        cur.execute('INSERT INTO expenses (description, amount, category, expense_date, notes) VALUES (%s, %s, %s, %s, %s)',
                   (request.form['description'], float(request.form['amount']), request.form.get('category', 'otro'),
                    request.form.get('expense_date', datetime.now().strftime('%Y-%m-%d')), request.form.get('notes')))
        db.commit()
        flash('Gasto registrado', 'success')
        return redirect(url_for('finances'))
    return render_template('expense_form.html', expense=None)

@app.route('/finances/client/<int:id>/payments')
@login_required
@require_admin
def client_payments(id):
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM clients WHERE id = %s', (id,))
    client = cur.fetchone()
    cur.execute('SELECT * FROM monthly_payments WHERE client_id = %s ORDER BY payment_date DESC', (id,))
    return render_template('client_payments.html', client=client, payments=cur.fetchall())

@app.route('/api/clients/search')
@login_required
def api_client_search():
    query = request.args.get('q', '')
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT id, first_name, last_name, cedula FROM clients WHERE first_name LIKE %s OR last_name LIKE %s OR cedula LIKE %s LIMIT 10',
               (f'%{query}%', f'%{query}%', f'{query}%'))
    return jsonify([dict(c) for c in cur.fetchall()])

@app.route('/export/clients')
@login_required
def export_clients():
    from openpyxl import Workbook
    db = get_db()
    cur = db.cursor()
    cur.execute('''SELECT c.*, p.name as plan_name, p.speed as plan_speed, p.price as plan_price
        FROM clients c LEFT JOIN plans p ON c.plan_id = p.id''')
    clients = cur.fetchall()
    wb = Workbook()
    ws = wb.active
    ws.append(['ID', 'Nombre', 'Apellido', 'Cedula', 'Telefono', 'Email', 'Direccion', 'Router', 'Serial', 'MAC', 'IP', 'NAP', 'Potencia', 'Plan', 'Velocidad', 'Precio', 'Estado', 'Fecha'])
    for c in ws.append([c['id'], c['first_name'], c['last_name'], c['cedula'], c['phone'], c['email'], c['address'], c['router_model'], c['router_serial'], c['router_mac'], c['ip_address'], c['nap_number'], c['potencia'], c['plan_name'], c['plan_speed'], c['plan_price'], c['connection_status'], c['registration_date']])
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
    db = get_db()
    cur = db.cursor()
    imported = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            try:
                cur.execute('''INSERT INTO clients (first_name, last_name, cedula, phone, email, address, plan_id, connection_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''', (row[1], row[2], row[3], row[4], row[5], row[6], None, 'active'))
                imported += 1
            except:
                pass
    db.commit()
    flash(f'{imported} clientes importados', 'success')
    return redirect(url_for('clients_list'))

@app.route('/export/plans')
@login_required
def export_plans():
    from openpyxl import Workbook
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM plans')
    plans = cur.fetchall()
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

@app.route('/export/finances')
@login_required
@require_admin
def export_finances():
    from openpyxl import Workbook
    db = get_db()
    cur = db.cursor()
    wb = Workbook()
    ws = wb.active
    ws.title = "Pagos"
    ws.append(['ID', 'Cliente', 'Monto', 'Mes', 'Fecha', 'Metodo', 'Estado'])
    cur.execute('SELECT mp.*, c.first_name, c.last_name FROM monthly_payments mp JOIN clients c ON mp.client_id = c.id')
    for p in cur.fetchall():
        ws.append([p['id'], f"{p['first_name']} {p['last_name']}", p['amount'], p['month'], p['payment_date'], p['method'], p['status']])
    ws2 = wb.create_sheet("Ingresos")
    ws2.append(['ID', 'Descripcion', 'Monto', 'Categoria', 'Fecha'])
    for i in db.cursor().execute('SELECT * FROM other_incomes').fetchall():
        ws2.append([i['id'], i['description'], i['amount'], i['category'], i['income_date']])
    ws3 = wb.create_sheet("Gastos")
    ws3.append(['ID', 'Descripcion', 'Monto', 'Categoria', 'Fecha'])
    for e in db.cursor().execute('SELECT * FROM expenses').fetchall():
        ws3.append([e['id'], e['description'], e['amount'], e['category'], e['expense_date']])
    from io import BytesIO
    output = BytesIO()
    wb.save(output)
    from flask import make_response
    return make_response(output.getvalue(), {'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Content-Disposition': 'attachment; filename=finanzas.xlsx'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)