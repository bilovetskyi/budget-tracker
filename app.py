from flask import Flask, request, redirect, render_template, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from db import get_conn, init_db

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Initialize the database when the app starts
init_db()

# Helper to get current theme
def get_theme():
    return request.cookies.get("theme", "light")

@app.route('/')
def home():
    if not session.get('user_id'):
        return redirect('/login')
    
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC", 
        (session['user_id'],)
    ).fetchall()

    income = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='income' AND user_id=?",
        (session['user_id'],)
    ).fetchone()[0]

    expense = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense' AND user_id=?",
        (session['user_id'],)
    ).fetchone()[0]
    conn.close()

    return render_template(
        'home.html',
        rows=rows,
        income=f"{income:.2f}",
        expense=f"{expense:.2f}",
        net=f"{income-expense:.2f}",
        today=datetime.today().strftime('%Y-%m-%d'),
        username=session['username'],
        theme=get_theme()
    )

@app.route('/add', methods=['POST'])
def add():
    if not session.get('user_id'):
        return redirect('/login')

    date = request.form['date']
    amount = float(request.form['amount'])
    category = request.form['category']
    type_ = request.form['type']
    desc = request.form['description']

    conn = get_conn()
    conn.execute(
        "INSERT INTO transactions(user_id, date, amount, category, type, description) VALUES(?,?,?,?,?,?)",
        (session['user_id'], date, amount, category, type_, desc)
    )
    conn.commit()
    conn.close()

    # --- THIS IS THE NEW LINE ---
    flash("Transaction added successfully!")
    # ----------------------------

    return redirect('/')
    return redirect('/')

@app.route('/delete/<int:tx_id>', methods=['POST'])
def delete(tx_id):
    if not session.get('user_id'):
        return redirect('/login')

    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (tx_id, session['user_id']))
    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_conn()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
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
        username = request.form['username']
        password_hash = generate_password_hash(request.form['password'])

        conn = get_conn()
        try:
            conn.execute("INSERT INTO users(username, password) VALUES(?,?)", (username, password_hash))
            conn.commit()
            conn.close()
            return redirect('/login')
        except sqlite3.IntegrityError:
            msg = 'Username already taken.'

    return render_template('register.html', msg=msg, theme=get_theme())

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)