"""
database.py
Database layer for the Budget Tracker (SQLite).
"""

import sqlite3
from typing import List, Tuple, Optional
from datetime import datetime

DB_FILENAME = "budget.db"

def get_connection():
    conn = sqlite3.connect(DB_FILENAME)
    # return rows as tuples by default; we'll map as needed
    return conn

def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income','expense')),
            description TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_transaction(date: str, amount: float, category: str, type_: str, description: Optional[str]):
    """Insert a new transaction. date must be YYYY-MM-DD."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO transactions (date, amount, category, type, description)
        VALUES (?, ?, ?, ?, ?)
    """, (date, amount, category, type_, description))
    conn.commit()
    conn.close()

def delete_transaction(tx_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_all_transactions(order_desc: bool = True) -> List[Tuple]:
    conn = get_connection()
    cur = conn.cursor()
    order = "DESC" if order_desc else "ASC"
    cur.execute(f"SELECT id, date, amount, category, type, description FROM transactions ORDER BY date {order}, id {order}")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_transactions_between(start_date: str, end_date: str) -> List[Tuple]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, amount, category, type, description
        FROM transactions
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC
    """, (start_date, end_date))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_transactions_by_month(year: int, month: int) -> List[Tuple]:
    start = f"{year:04d}-{month:02d}-01"
    # compute end of month (simple approach: next month minus one day)
    if month == 12:
        end = f"{year+1:04d}-01-01"
    else:
        end = f"{year:04d}-{month+1:02d}-01"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, amount, category, type, description
        FROM transactions
        WHERE date >= ? AND date < ?
        ORDER BY date DESC
    """, (start, end))
    rows = cur.fe
