#Standard Python Imports
import csv
import io
from datetime import datetime

#Third-Party Imports (Flask & Werkzeug)
from flask import Flask, request, redirect, render_template, session, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash

# Imports
from db import get_conn, init_db

app = Flask(__name__)
app.secret_key = "supersecretkey" 

init_db()

# ---------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------

def get_theme():
    """Gets the user's theme preference from cookies."""
    return request.cookies.get("theme", "light")

def get_dashboard_data(user_id, year, month_num):
    """Fetches all dashboard statistics and transactions for the given period."""
    conn = get_conn()
    
    # 1. Determine Date Filter
    is_all_time = (year == 'all')
    target_date = f"{year}-{month_num}"

    if is_all_time:
        date_filter_sql = ""
        params = (user_id,)
    else:
        date_filter_sql = "AND strftime('%Y-%m', date) = ?"
        params = (user_id, target_date)

    # 2. Fetch Transactions (Table)
    sql_rows = f"SELECT * FROM transactions WHERE user_id=? {date_filter_sql} ORDER BY date DESC"
    rows = conn.execute(sql_rows, params).fetchall()

    # 3. Fetch Income & Expense (Summary)
    sql_income = f"SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='income' AND user_id=? {date_filter_sql}"
    income = conn.execute(sql_income, params).fetchone()[0]

    sql_expense = f"SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense' AND user_id=? {date_filter_sql}"
    expense = conn.execute(sql_expense, params).fetchone()[0]

    # 4. Fetch Chart Data (Expenses by Category)
    sql_chart = f"""
        SELECT category, SUM(amount) as total 
        FROM transactions 
        WHERE user_id=? AND type='expense' {date_filter_sql}
        GROUP BY category
    """
    category_data = conn.execute(sql_chart, params).fetchall()
    
    # 5. Calculate Global Wallet Balance (Always All-Time)
    all_income = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='income' AND user_id=?", (user_id,)).fetchone()[0]
    all_expense = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense' AND user_id=?", (user_id,)).fetchone()[0]
    wallet_balance = all_income - all_expense

    conn.close()
    
    return rows, income, expense, category_data, wallet_balance

# ---------------------------------------------------
# ROUTES
# ---------------------------------------------------

@app.route('/')
def home():
    if not session.get('user_id'):
        return redirect('/login')
    
    today = datetime.today()
    selected_year = request.args.get('year', today.strftime('%Y'))
    selected_month_num = request.args.get('month', today.strftime('%m'))

    rows, income, expense, category_data, wallet_balance = get_dashboard_data(
        session['user_id'], selected_year, selected_month_num
    )

    chart_labels = [row['category'] for row in category_data]
    chart_values = [row['total'] for row in category_data]

    return render_template(
        'home.html',
        rows=rows,
        income=f"{income:.2f}",
        expense=f"{expense:.2f}",
        net=f"{income-expense:.2f}",
        wallet_balance=f"{wallet_balance:.2f}",
        today=today.strftime('%Y-%m-%d'),
        username=session['username'],
        theme=get_theme(),
        chart_labels=chart_labels,
        chart_values=chart_values,
        current_year=selected_year,
        current_month_num=selected_month_num
    )

@app.route('/add', methods=['POST'])
def add():
    if not session.get('user_id'): return redirect('/login')

    conn = get_conn()
    conn.execute(
        "INSERT INTO transactions(user_id, date, amount, category, type, description) VALUES(?,?,?,?,?,?)",
        (session['user_id'], request.form['date'], float(request.form['amount']), 
         request.form['category'], request.form['type'], request.form['description'])
    )
    conn.commit()
    conn.close()
    flash("Transaction added successfully!")
    return redirect('/')

@app.route('/edit/<int:tx_id>', methods=['GET', 'POST'])
def edit(tx_id):
    if not session.get('user_id'): return redirect('/login')

    conn = get_conn()
    
    if request.method == 'POST':
        conn.execute("""
            UPDATE transactions 
            SET date=?, amount=?, category=?, type=?, description=?
            WHERE id=? AND user_id=?
        """, (request.form['date'], float(request.form['amount']), request.form['category'], 
              request.form['type'], request.form['description'], tx_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Transaction updated successfully!")
        return redirect('/')
    
    transaction = conn.execute("SELECT * FROM transactions WHERE id=? AND user_id=?", (tx_id, session['user_id'])).fetchone()
    conn.close()
    
    if not transaction: return "Transaction not found", 404
    return render_template('edit.html', row=transaction, theme=get_theme())

@app.route('/delete/<int:tx_id>', methods=['POST'])
def delete(tx_id):
    if not session.get('user_id'): return redirect('/login')
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (tx_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Transaction deleted.")
    return redirect('/')

@app.route('/export')
def export():
    if not session.get('user_id'): return redirect('/login')
    conn = get_conn()
    rows = conn.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC", (session['user_id'],)).fetchall()
    conn.close()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Type', 'Category', 'Amount', 'Description'])
    for row in rows:
        cw.writerow([row['date'], row['type'], row['category'], row['amount'], row['description']])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=transactions.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        conn = get_conn()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/')
        else:
            msg = 'Incorrect username or password.'
    return render_template('login.html', msg=msg, theme=get_theme())

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        try:
            conn = get_conn()
            conn.execute("INSERT INTO users(username, password) VALUES(?,?)", 
                        (request.form['username'], generate_password_hash(request.form['password'])))
            conn.commit()
            conn.close()
            return redirect('/login')
        except:
            msg = 'Username already taken.'
    return render_template('register.html', msg=msg, theme=get_theme())

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)