from flask import Flask, request, redirect, render_template_string, session, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --------------------
# Database Setup
# --------------------
def get_conn():
    conn = sqlite3.connect("budget.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --------------------
# Theme Logic
# --------------------
def get_theme():
    return request.cookies.get("theme", "light")

# --------------------
# Templates (Apple Minimalistic)
# --------------------
base_style = """
<style>
:root {
    --bg-light: #f5f5f7;
    --card-light: #ffffff;
    --text-light: #000000;
    --border-light: #e0e0e0;

    --bg-dark: #1c1c1e;
    --card-dark: #2c2c2e;
    --text-dark: #f5f5f7;
    --border-dark: #3a3a3c;
}

body[data-theme='light'] {
    --bg: var(--bg-light);
    --card: var(--card-light);
    --text: var(--text-light);
    --border: var(--border-light);
}

body[data-theme='dark'] {
    --bg: var(--bg-dark);
    --card: var(--card-dark);
    --text: var(--text-dark);
    --border: var(--border-dark);
}

body {
    margin:0;
    padding:20px;
    background: var(--bg);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
    color: var(--text);
    transition: background .3s, color .3s;
}

.card {
    background: var(--card);
    border:1px solid var(--border);
    padding:20px;
    max-width:650px;
    margin:20px auto;
    border-radius:20px;
    box-shadow:0 8px 20px rgba(0,0,0,0.05);
    transition: background .3s, border .3s;
}

input, select {
    width:100%;
    padding:12px;
    margin:8px 0;
    border-radius:12px;
    border:1px solid var(--border);
    background:var(--card);
    color:var(--text);
}

.btn {
    width:100%;
    padding:12px;
    background:#0071e3;
    border:none;
    border-radius:12px;
    color:white;
    cursor:pointer;
    font-size:1rem;
}

.table-container {
    overflow-x:auto;
}

table {
    width:100%;
    border-collapse:collapse;
}

td, th {
    padding:12px;
    border-bottom:1px solid var(--border);
}

.delete-btn {
    background:#ff3b30;
    color:white;
    padding:6px 12px;
    border:none;
    border-radius:10px;
    cursor:pointer;
}

.theme-toggle {
    text-align:center;
    margin:10px;
}
</style>
<script>
function switchTheme() {
    const current = document.body.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.cookie = `theme=${next}; path=/;`;
    location.reload();
}
</script>
"""

# Login Template
login_template = base_style + """
<body data-theme='{{theme}}'>
<h2 style='text-align:center;'>Login</h2>
<div class='card'>
    {% if msg %}<p style='color:red; text-align:center;'>{{msg}}</p>{% endif %}
    <form method='POST'>
        <input name='username' placeholder='Username' required>
        <input type='password' name='password' placeholder='Password' required>
        <button class='btn'>Login</button>
    </form>
    <p style='text-align:center;'><a href='/register'>Register</a></p>
</div>
</body>
"""

# Register Template
register_template = base_style + """
<body data-theme='{{theme}}'>
<h2 style='text-align:center;'>Register</h2>
<div class='card'>
    {% if msg %}<p style='color:red; text-align:center;'>{{msg}}</p>{% endif %}
    <form method='POST'>
        <input name='username' placeholder='Username' required>
        <input type='password' name='password' placeholder='Password' required>
        <button class='btn'>Register</button>
    </form>
    <p style='text-align:center;'><a href='/login'>Login</a></p>
</div>
</body>
"""

# Home Template
home_template = base_style + """
<body data-theme='{{theme}}'>
<h1 style='text-align:center;'>Budget Tracker</h1>
<div class='theme-toggle'>
    <button onclick='switchTheme()' class='btn'>Toggle Theme</button>
</div>
<p style='text-align:center;'>Logged in as <b>{{username}}</b> | <a href='/logout'>Logout</a></p>

<div class='card'>
<h3>Add Transaction</h3>
<form method='POST' action='/add'>
    <input type='date' name='date' value='{{today}}' required>
    <input type='number' name='amount' step='0.01' placeholder='Amount' required>
    <input name='category' placeholder='Category' required>
    <select name='type'>
        <option value='income'>Income</option>
        <option value='expense'>Expense</option>
    </select>
    <input name='description' placeholder='Description (optional)'>
    <button class='btn'>Add</button>
</form>
</div>

<div class='card'>
<h3>Summary</h3>
<p><b>Total Income:</b> ${{income}}</p>
<p><b>Total Expense:</b> ${{expense}}</p>
<p><b>Net Balance:</b> ${{net}}</p>
</div>

<div class='card table-container'>
<h3>Transactions</h3>
<table>
<tr>
    <th>Date</th><th>Amount</th><th>Type</th><th>Category</th><th>Description</th><th></th>
</tr>
{% for row in rows %}
<tr>
    <td>{{row.date}}</td>
    <td>${{row.amount}}</td>
    <td>{{row.type}}</td>
    <td>{{row.category}}</td>
    <td>{{row.description}}</td>
    <td>
        <form method='POST' action='/delete/{{row.id}}'>
            <button class='delete-btn'>&times;</button>
        </form>
    </td>
</tr>
{% endfor %}
</table>
</div>
</body>
"""

# --------------------
# Routes
# --------------------
@app.route('/')
def home():
    if not session.get('user_id'):
        return redirect('/login')
    theme = get_theme()
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

    return render_template_string(
        home_template,
        rows=rows,
        income=f"{income:.2f}",
        expense=f"{expense:.2f}",
        net=f"{income-expense:.2f}",
        today=datetime.today().strftime('%Y-%m-%d'),
        username=session['username'],
        theme=theme
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

    return redirect('/')

@app.route('/delete/<int:tx_id>', methods=['POST'])
def delete(tx_id):
    if not session.get('user_id'):
        return redirect('/login')

    conn = get_conn()
    conn.execute(
        "DELETE FROM transactions WHERE id=? AND user_id=?",
        (tx_id, session['user_id'])
    )
    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    theme = get_theme()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_conn()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/')
        else:
            msg = 'Incorrect username or password.'

    return render_template_string(login_template, msg=msg, theme=theme)

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    theme = get_theme()

    if request.method == 'POST':
        username = request.form['username']
        password_hash = generate_password_hash(request.form['password'])

        conn = get_conn()
        try:
            conn.execute(
                "INSERT INTO users(username, password) VALUES(?,?)",
                (username, password_hash)
            )
            conn.commit()
            conn.close()
            return redirect('/login')
        except sqlite3.IntegrityError:
            msg = 'Username already taken.'

    return render_template_string(register_template, msg=msg, theme=theme)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
