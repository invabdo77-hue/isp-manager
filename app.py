from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database import get_db, init_db, check_and_cut_clients, create_default_users
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import calendar

app = Flask(__name__)
app.secret_key = 'isp_manager_secret_key_2024'

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
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    db.close()
    if user:
        return User(user['id'], user['username'], user['role'])
    return None

def require_admin(f):
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Acceso solo para administradores', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
@login_required
def index():
    db = get_db()
    total_clients = db.execute('SELECT COUNT(*) as count FROM clients').fetchone()['count']
    active_clients = db.execute("SELECT COUNT(*) as count FROM clients WHERE connection_status = 'active'").fetchone()['count']
    
    recent_clients = db.execute('''
        SELECT c.*, p.name as plan_name, p.price as plan_price
        FROM clients c LEFT JOIN plans p ON c.plan_id = p.id
        ORDER BY c.registration_date DESC LIMIT 5
    ''').fetchall()
    
    db.close()
    return render_template('index.html', 
                         total_clients=total_clients,
                         active_clients=active_clients,
                         recent_clients=recent_clients)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username'], user['role']))
            return redirect(url_for('index'))
        flash('Usuario o contraseña incorrectos', 'danger')
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
    clients = db.execute('''
        SELECT c.*, p.name as plan_name, p.speed as plan_speed, p.price as plan_price
        FROM clients c LEFT JOIN plans p ON c.plan_id = p.id
        ORDER BY c.first_name || ' ' || c.last_name
    ''').fetchall()
    db.close()
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
        
        if request.form.get('cedula'):
            vals.append(request.form.get('cedula'))
            cols.append('cedula')
        if request.form.get('phone'):
            vals.append(request.form.get('phone'))
            cols.append('phone')
        if request.form.get('email'):
            vals.append(request.form.get('email'))
            cols.append('email')
        if request.form.get('address'):
            vals.append(request.form.get('address'))
            cols.append('address')
        if request.form.get('router_model'):
            vals.append(request.form.get('router_model'))
            cols.append('router_model')
        if request.form.get('router_serial'):
            vals.append(request.form.get('router_serial'))
            cols.append('router_serial')
        if request.form.get('router_mac'):
            vals.append(request.form.get('router_mac'))
            cols.append('router_mac')
        if request.form.get('ip_address'):
            vals.append(request.form.get('ip_address'))
            cols.append('ip_address')
        if request.form.get('nap_number'):
            vals.append(request.form.get('nap_number'))
            cols.append('nap_number')
        if request.form.get('potencia'):
            vals.append(request.form.get('potencia'))
            cols.append('potencia')
        if request.form.get('plan_id'):
            vals.append(int(request.form.get('plan_id')))
            cols.append('plan_id')
        
        if current_user.role == 'admin':
            if request.form.get('connection_status'):
                vals.append(request.form.get('connection_status'))
                cols.append('connection_status')
        else:
            vals.append('active')
            cols.append('connection_status')
        
        sql = 'INSERT INTO clients (' + ', '.join(cols) + ') VALUES (' + ','.join(['?']*len(cols)) + ')'
        
        db.execute(sql, vals)
        db.commit()
        flash('Cliente creado exitosamente', 'success')
        if current_user.role == 'technician':
            return redirect(url_for('clients_list'))
        return redirect(url_for('clients_list'))
    
    plans = db.execute('SELECT * FROM plans ORDER BY price').fetchall()
    db.close()
    return render_template('client_form.html', plans=plans, client=None)

@app.route('/clients/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_admin
def client_edit(id):
    db = get_db()
    if request.method == 'POST':
        updates = []
        values = []
        
        if request.form.get('first_name'):
            updates.append('first_name=?')
            values.append(request.form.get('first_name'))
        if request.form.get('last_name'):
            updates.append('last_name=?')
            values.append(request.form.get('last_name'))
        if request.form.get('cedula'):
            updates.append('cedula=?')
            values.append(request.form.get('cedula'))
        if request.form.get('phone'):
            updates.append('phone=?')
            values.append(request.form.get('phone'))
        if request.form.get('email'):
            updates.append('email=?')
            values.append(request.form.get('email'))
        if request.form.get('address'):
            updates.append('address=?')
            values.append(request.form.get('address'))
        if request.form.get('router_model'):
            updates.append('router_model=?')
            values.append(request.form.get('router_model'))
        if request.form.get('router_serial'):
            updates.append('router_serial=?')
            values.append(request.form.get('router_serial'))
        if request.form.get('router_mac'):
            updates.append('router_mac=?')
            values.append(request.form.get('router_mac'))
        if request.form.get('ip_address'):
            updates.append('ip_address=?')
            values.append(request.form.get('ip_address'))
        if request.form.get('nap_number'):
            updates.append('nap_number=?')
            values.append(request.form.get('nap_number'))
        if request.form.get('potencia'):
            updates.append('potencia=?')
            values.append(request.form.get('potencia'))
        if request.form.get('plan_id'):
            updates.append('plan_id=?')
            values.append(int(request.form.get('plan_id')))
        if request.form.get('connection_status'):
            updates.append('connection_status=?')
            values.append(request.form.get('connection_status'))
        
        values.append(id)
        sql = 'UPDATE clients SET ' + ', '.join(updates) + ' WHERE id=?'
        
        db.execute(sql, values)
        db.commit()
        flash('Cliente actualizado', 'success')
        return redirect(url_for('clients_list'))
    
    client = db.execute('SELECT * FROM clients WHERE id = ?', (id,)).fetchone()
    plans = db.execute('SELECT * FROM plans ORDER BY price').fetchall()
    db.close()
    return render_template('client_form.html', plans=plans, client=client)

@app.route('/clients/<int:id>/delete', methods=['POST'])
@login_required
@require_admin
def client_delete(id):
    db = get_db()
    db.execute('DELETE FROM clients WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Cliente eliminado', 'success')
    return redirect(url_for('clients_list'))

@app.route('/plans')
@login_required
@require_admin
def plans_list():
    db = get_db()
    plans = db.execute('''
        SELECT p.*, COUNT(c.id) as client_count
        FROM plans p LEFT JOIN clients c ON p.id = c.plan_id
        GROUP BY p.id
        ORDER BY p.price
    ''').fetchall()
    db.close()
    return render_template('plans.html', plans=plans)

@app.route('/plans/new', methods=['GET', 'POST'])
@login_required
@require_admin
def plan_new():
    if request.method == 'POST':
        db = get_db()
        db.execute('''
            INSERT INTO plans (name, speed, price, description)
            VALUES (?, ?, ?, ?)
        ''', (
            request.form['name'],
            request.form['speed'],
            float(request.form['price']),
            request.form.get('description')
        ))
        db.commit()
        db.close()
        flash('Plan creado exitosamente', 'success')
        return redirect(url_for('plans_list'))
    return render_template('plan_form.html', plan=None)

@app.route('/plans/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_admin
def plan_edit(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('''
            UPDATE plans SET name=?, speed=?, price=?, description=?
            WHERE id=?
        ''', (
            request.form['name'],
            request.form['speed'],
            float(request.form['price']),
            request.form.get('description'),
            id
        ))
        db.commit()
        db.close()
        flash('Plan actualizado', 'success')
        return redirect(url_for('plans_list'))
    
    plan = db.execute('SELECT * FROM plans WHERE id = ?', (id,)).fetchone()
    db.close()
    return render_template('plan_form.html', plan=plan)

@app.route('/plans/<int:id>/delete', methods=['POST'])
@login_required
@require_admin
def plan_delete(id):
    db = get_db()
    db.execute('DELETE FROM plans WHERE id = ?', (id,))
    db.commit()
    db.close()
    flash('Plan eliminado', 'success')
    return redirect(url_for('plans_list'))

@app.route('/finances')
@login_required
@require_admin
def finances():
    db = get_db()
    
    total_monthly = db.execute("SELECT COALESCE(SUM(amount), 0) as total FROM monthly_payments WHERE status = 'paid'").fetchone()['total']
    total_other_incomes = db.execute("SELECT COALESCE(SUM(amount), 0) as total FROM other_incomes").fetchone()['total']
    total_expenses = db.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses").fetchone()['total']
    balance = total_monthly + total_other_incomes - total_expenses
    
    monthly_payments = db.execute('''
        SELECT mp.*, c.first_name, c.last_name, p.name as plan_name
        FROM monthly_payments mp
        JOIN clients c ON mp.client_id = c.id
        LEFT JOIN plans p ON c.plan_id = p.id
        ORDER BY mp.payment_date DESC
    ''').fetchall()
    
    other_incomes = db.execute('''
        SELECT * FROM other_incomes ORDER BY income_date DESC
    ''').fetchall()
    
    expenses = db.execute('''
        SELECT * FROM expenses ORDER BY expense_date DESC
    ''').fetchall()
    
    income_by_category = db.execute('''
        SELECT category, SUM(amount) as total FROM other_incomes GROUP BY category
    ''').fetchall()
    
    expense_by_category = db.execute('''
        SELECT category, SUM(amount) as total FROM expenses GROUP BY category
    ''').fetchall()
    
    db.close()
    
    return render_template('finances.html',
                         total_monthly=total_monthly,
                         total_other_incomes=total_other_incomes,
                         total_expenses=total_expenses,
                         balance=balance,
                         monthly_payments=monthly_payments,
                         other_incomes=other_incomes,
                         expenses=expenses,
                         income_by_category=income_by_category,
                         expense_by_category=expense_by_category)

@app.route('/finances/payment/new', methods=['GET', 'POST'])
@login_required
@require_admin
def payment_new():
    db = get_db()
    if request.method == 'POST':
        client_id = int(request.form['client_id'])
        month = request.form['month']
        amount = float(request.form['amount'])
        method = request.form.get('method', 'efectivo')
        
        db.execute('''
            INSERT INTO monthly_payments (client_id, amount, month, payment_date, method, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            client_id,
            amount,
            month,
            request.form.get('payment_date', datetime.now().strftime('%Y-%m-%d')),
            method,
            'paid',
            request.form.get('notes')
        ))
        
        client = db.execute('SELECT connection_status FROM clients WHERE id = ?', (client_id,)).fetchone()
        if client and client['connection_status'] == 'cut':
            db.execute("UPDATE clients SET connection_status = 'active' WHERE id = ?", (client_id,))
        
        db.commit()
        flash('Pago registrado', 'success')
        return redirect(url_for('finances'))
    
    clients = db.execute('SELECT id, first_name, last_name FROM clients ORDER BY first_name, last_name').fetchall()
    current_month = datetime.now().strftime('%Y-%m')
    db.close()
    return render_template('payment_form.html', clients=clients, current_month=current_month, payment=None)

@app.route('/finances/income/new', methods=['GET', 'POST'])
@login_required
@require_admin
def income_new():
    db = get_db()
    if request.method == 'POST':
        db.execute('''
            INSERT INTO other_incomes (description, amount, category, income_date, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            request.form['description'],
            float(request.form['amount']),
            request.form.get('category', 'otro'),
            request.form.get('income_date', datetime.now().strftime('%Y-%m-%d')),
            request.form.get('notes')
        ))
        db.commit()
        flash('Ingreso registrado', 'success')
        return redirect(url_for('finances'))
    return render_template('income_form.html', income=None)

@app.route('/finances/expense/new', methods=['GET', 'POST'])
@login_required
@require_admin
def expense_new():
    db = get_db()
    if request.method == 'POST':
        db.execute('''
            INSERT INTO expenses (description, amount, category, expense_date, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            request.form['description'],
            float(request.form['amount']),
            request.form.get('category', 'otro'),
            request.form.get('expense_date', datetime.now().strftime('%Y-%m-%d')),
            request.form.get('notes')
        ))
        db.commit()
        flash('Gasto registrado', 'success')
        return redirect(url_for('finances'))
    return render_template('expense_form.html', expense=None)

@app.route('/finances/client/<int:id>/payments')
@login_required
@require_admin
def client_payments(id):
    db = get_db()
    client = db.execute('SELECT * FROM clients WHERE id = ?', (id,)).fetchone()
    payments = db.execute('''
        SELECT * FROM monthly_payments
        WHERE client_id = ?
        ORDER BY payment_date DESC
    ''', (id,)).fetchall()
    db.close()
    return render_template('client_payments.html', client=client, payments=payments)

@app.route('/api/clients/search')
@login_required
def api_client_search():
    db = get_db()
    query = request.args.get('q', '')
    clients = db.execute('''
        SELECT id, first_name, last_name, cedula FROM clients
        WHERE first_name LIKE ? OR last_name LIKE ? OR cedula LIKE ?
        ORDER BY first_name, last_name LIMIT 10
    ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    db.close()
    return jsonify([dict(c) for c in clients])

@app.route('/export/clients')
@login_required
def export_clients():
    from openpyxl import Workbook
    db = get_db()
    clients = db.execute('''
        SELECT c.*, p.name as plan_name, p.speed as plan_speed, p.price as plan_price
        FROM clients c LEFT JOIN plans p ON c.plan_id = p.id
    ''').fetchall()
    db.close()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes"
    headers = ['ID', 'Nombre', 'Apellido', 'Cédula', 'Teléfono', 'Email', 'Dirección', 
               'Modelo Router', 'Serial Router', 'MAC', 'IP', 'NAP', 'Potencia', 
               'Plan', 'Velocidad', 'Precio Plan', 'Estado', 'Fecha Registro']
    ws.append(headers)
    
    for c in clients:
        ws.append([c['id'], c['first_name'], c['last_name'], c['cedula'], c['phone'],
                   c['email'], c['address'], c['router_model'], c['router_serial'],
                   c['router_mac'], c['ip_address'], c['nap_number'], c['potencia'],
                   c['plan_name'], c['plan_speed'], c['plan_price'], c['connection_status'],
                   c['registration_date']])
    
    from io import BytesIO
    from flask import make_response
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=clientes.xlsx'
    return response

@app.route('/import/clients', methods=['POST'])
@login_required
@require_admin
def import_clients():
    from openpyxl import load_workbook
    if 'file' not in request.files:
        flash('No se seleccionó archivo', 'danger')
        return redirect(url_for('clients_list'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó archivo', 'danger')
        return redirect(url_for('clients_list'))
    
    wb = load_workbook(file)
    ws = wb.active
    
    db = get_db()
    imported = 0
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        try:
            db.execute('''
                INSERT INTO clients (first_name, last_name, cedula, phone, email, address,
                    router_model, router_serial, router_mac, ip_address, nap_number, potencia,
                    plan_id, connection_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8],
                  row[9], row[10], row[11], row[12], None, row[15] or 'active'))
            imported += 1
        except:
            pass
    
    db.commit()
    db.close()
    flash(f'{imported} clientes importados', 'success')
    return redirect(url_for('clients_list'))

@app.route('/export/plans')
@login_required
def export_plans():
    from openpyxl import Workbook
    db = get_db()
    plans = db.execute('SELECT * FROM plans').fetchall()
    db.close()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Planes"
    ws.append(['ID', 'Nombre', 'Velocidad', 'Precio', 'Descripción'])
    
    for p in plans:
        ws.append([p['id'], p['name'], p['speed'], p['price'], p['description']])
    
    from flask import make_response
    from io import BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=planes.xlsx'
    return response

@app.route('/import/plans', methods=['POST'])
@login_required
@require_admin
def import_plans():
    from openpyxl import load_workbook
    if 'file' not in request.files:
        flash('No se seleccionó archivo', 'danger')
        return redirect(url_for('plans_list'))
    
    file = request.files['file']
    wb = load_workbook(file)
    ws = wb.active
    
    db = get_db()
    imported = 0
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        try:
            db.execute('''
                INSERT INTO plans (name, speed, price, description)
                VALUES (?, ?, ?, ?)
            ''', (row[1], row[2], float(row[3]) if row[3] else 0, row[4]))
            imported += 1
        except:
            pass
    
    db.commit()
    db.close()
    flash(f'{imported} planes importados', 'success')
    return redirect(url_for('plans_list'))

@app.route('/export/finances')
@login_required
@require_admin
def export_finances():
    from openpyxl import Workbook
    db = get_db()
    
    wb = Workbook()
    
    ws = wb.active
    ws.title = "Pagos Mensuales"
    ws.append(['ID', 'Cliente', 'Monto', 'Mes', 'Fecha Pago', 'Método', 'Estado'])
    payments = db.execute('''
        SELECT mp.*, c.first_name, c.last_name
        FROM monthly_payments mp JOIN clients c ON mp.client_id = c.id
    ''').fetchall()
    for p in payments:
        ws.append([p['id'], f"{p['first_name']} {p['last_name']}", p['amount'],
                   p['month'], p['payment_date'], p['method'], p['status']])
    
    ws2 = wb.create_sheet("Otros Ingresos")
    ws2.append(['ID', 'Descripción', 'Monto', 'Categoría', 'Fecha'])
    incomes = db.execute('SELECT * FROM other_incomes').fetchall()
    for i in incomes:
        ws2.append([i['id'], i['description'], i['amount'], i['category'], i['income_date']])
    
    ws3 = wb.create_sheet("Gastos")
    ws3.append(['ID', 'Descripción', 'Monto', 'Categoría', 'Fecha'])
    expenses = db.execute('SELECT * FROM expenses').fetchall()
    for e in expenses:
        ws3.append([e['id'], e['description'], e['amount'], e['category'], e['expense_date']])
    
    db.close()
    
    from io import BytesIO
    from flask import make_response
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=finanzas.xlsx'
    return response

if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        print(f"Error initializing DB: {e}")
    try:
        create_default_users()
    except Exception as e:
        print(f"Error creating users: {e}")
    try:
        check_and_cut_clients()
    except Exception as e:
        print(f"Error checking clients: {e}")
    app.run(debug=True, host='0.0.0.0', port=5000)
