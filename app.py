from flask import Flask, request, redirect, render_template_string, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change in production

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
# Templates
# --------------------

login_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <style>
        body { font-family: Arial; background:#f4f4f4; padding:20px; }
        form { background:white; padding:15px; border-radius:8px; margin:50px auto; width:300px; }
        input { padding:8px; margin:5px 0; width:95%; }
        .btn { background:#4CAF50; color:white; padding:10px; border:none; cursor:pointer; width:100%; }
        .msg { text-align:center; color:red; }
        a { display:block; text-align:center; margin-top:10px; }
    </style>
</head>
<body>

<h2 style="text-align:center;">Login</h2>
{% if msg %}<p class="msg">{{msg}}</p>{% endif %}
<form method="POST">
    <input type="text" name="username" placeholder="Username" required>
    <input type="password" name="password" placeholder="Password" required>
    <button class="btn">Login</button>
</form>
<a href="/register">Register</a>

</body>
</html>
"""

register_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Register</title>
    <style>
        body { font-family: Arial; background:#f4f4f4; padding:20px; }
        form { background:white; padding:15px; border-radius:8px; margin:50px auto; width:300px; }
        input { padding:8px; margin:5px 0; width:95%; }
        .btn { background:#4CAF50; color:white; padding:10px; border:none; cursor:pointer; width:100%; }
        .msg { text-align:center; color:red; }
        a { display:block; text-align:center; margin-top:10px; }
    </style>
</head>
<body>

<h2 style="text-align:center;">Register</h2>
{% if msg %}<p class="msg">{{msg}}</p>{% endif %}
<form method="POST">
    <input type="text" name="username" placeholder="Username" required>
    <input type="password" name="password" placeholder="Password" required>
    <button class="btn">Register</button>
</form>
<a href="/login">Login</a>

</body>
</html>
"""

home_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Budget Tracker</title>
    <style>
        body { font-family: Arial; background:#f2f2f2; padding:20px; }
        h1 { text-align:center; }
        form, table { background:white; padding:15px; border-radius:8px; margin:20px auto; width:80%; }
        table { border-collapse: collapse; }
        th, td { border-bottom: 1px solid #ddd; padding: 8px; text-align:center; }
        th { background:#eee; }
        input, select { padding:8px; margin:5px; width:95%; }
        .btn { background:#4CAF50; color:white; border:none; padding:10px 20px; cursor:pointer; }
        .delete { background:red; color:white; border:none; padding:5px 10px; cursor:pointer; }
        .summary-box { text-align:center; margin:20px; font-size:1.2em; }
        .logout { text-align:center; margin:10px; }
        .logout a { text-decoration:none; color:red; font-weight:bold; }
    </style>
</head>
<body>

<h1>Budget Tracker</h1>
<div class="logout">
    Logged in as <b>{{username}}</b> | <a href="/logout">Logout</a>
</div>

<!-- Add Transaction Form -->
<form method="POST" action="/add">
    <h3>Add Transaction</h3>
    <input type="date" name="date" value="{{today}}" required>
    <input type="number" name="amount" step="0.01" placeholder="Amount" required>
    <input type="text" name="category" placeholder="Category" required>

    <select name="type">
        <option value="income">Income</option>
        <option value="expense">Expense</option>
    </select>

    <input type="text" name="description" placeholder="Description (optional)">
    <button class="btn">Add Transaction</button>
</form>

<!-- Summary -->
<div class="summary-box">
    <strong>Total Income:</strong> ${{income}} &nbsp;&nbsp;
    <strong>Total Expense:</strong> ${{expense}} &nbsp;&nbsp;
    <strong>Net Balance:</strong> ${{net}}
</div>

<!-- Transaction Table -->
<table>
<tr>
    <th>ID</th><th>Date</th><th>Amount</th><th>Type</th><th>Category</th><th>Description</th><th>Delete</th>
</tr>
{% for row in rows %}
<tr>
    <td>{{row.id}}</td>
    <td>{{row.date}}</td>
    <td>${{row.amount}}</td>
    <td>{{row.type}}</td>
    <td>{{row.category}}</td>
    <td>{{row.description}}</td>
    <td>
        <form method="POST" action="/delete/{{row.id}}">
            <button class="delete">&times;</button>
        </form>
    </td>
</tr>
{% endfor %}
</table>

</body>
</html>
"""

# --------------------
# Routes
# --------------------

# Home page
@app.route("/")
def home():
    if not session.get("user_id"):
        return redirect("/login")

    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC, id DESC",
        (session["user_id"],)
    ).fetchall()
    income = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='income' AND user_id=?",
        (session["user_id"],)
    ).fetchone()[0]
    expense = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense' AND user_id=?",
        (session["user_id"],)
    ).fetchone()[0]
    conn.close()

    return render_template_string(
        home_template,
        rows=rows,
        income=f"{income:.2f}",
        expense=f"{expense:.2f}",
        net=f"{income-expense:.2f}",
        today=datetime.today().strftime("%Y-%m-%d"),
        username=session["username"]
    )

# Add transaction
@app.route("/add", methods=["POST"])
def add():
    if not session.get("user_id"):
        return redirect("/login")

    date = request.form["date"]
    amount = float(request.form["amount"])
    category = request.form["category"]
    type_ = request.form["type"]
    description = request.form["description"]

    conn = get_conn()
    conn.execute(
        "INSERT INTO transactions(user_id, date, amount, category, type, description) VALUES(?,?,?,?,?,?)",
        (session["user_id"], date, amount, category, type_, description)
    )
    conn.commit()
    conn.close()
    return redirect("/")

# Delete transaction
@app.route("/delete/<int:tx_id>", methods=["POST"])
def delete(tx_id):
    if not session.get("user_id"):
        return redirect("/login")
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (tx_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect("/")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    msg = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_conn()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")
        else:
            msg = "Incorrect username or password."
    return render_template_string(login_template, msg=msg)

# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""
    if request.method == "POST":
        username = request.form["username"]
        password_hash = generate_password_hash(request.form["password"])
        conn = get_conn()
        try:
            conn.execute("INSERT INTO users(username, password) VALUES(?,?)", (username, password_hash))
            conn.commit()
            conn.close()
            return redirect("/login")
        except sqlite3.IntegrityError:
            msg = "Username already taken."
    return render_template_string(register_template, msg=msg)

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# --------------------
# Run app
# --------------------
if __name__ == "__main__":
    app.run(debug=True)
