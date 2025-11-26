"""
main.py
Command-line interface for the Budget Tracker.
"""

from datetime import datetime
import database
import sys

PAGE_SIZE = 10

def clear_screen():
    # small cross-platform hint (not required)
    print("\n" * 2)

def prompt_date(prompt_text="Date (YYYY-MM-DD) [default: today]: "):
    while True:
        s = input(prompt_text).strip()
        if s == "":
            return datetime.today().strftime("%Y-%m-%d")
        if database.validate_date_str(s):
            return s
        print("Invalid date format. Please use YYYY-MM-DD.")

def prompt_amount():
    while True:
        s = input("Amount (positive number): ").strip()
        try:
            a = float(s)
            if a <= 0:
                print("Amount must be positive.")
                continue
            return a
        except ValueError:
            print("Enter a numeric value (e.g. 12.50).")

def prompt_type():
    while True:
        s = input("Type (income/expense): ").strip().lower()
        if s in ("income", "expense"):
            return s
        print("Type must be 'income' or 'expense'.")

def add_transaction_ui():
    print("\n--- Add Transaction ---")
    date = prompt_date()
    amount = prompt_amount()
    category = input("Category (e.g. Food, Salary, Rent): ").strip() or "Uncategorized"
    type_ = prompt_type()
    description = input("Description (optional): ").strip() or None

    # For expenses, we store positive numbers and track type separately.
    database.add_transaction(date, amount, category, type_, description)
    print("Transaction added successfully.")

def print_rows(rows, page: int = 0):
    if not rows:
        print("No transactions found.")
        return
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    subset = rows[start:end]
    print(f"\n--- Transactions (showing {start+1}-{min(end, len(rows))} of {len(rows)}) ---")
    print(f"{'ID':>3}  {'Date':10}  {'Amount':10}  {'Type':7}  {'Category':15}  Description")
    print("-"*80)
    for r in subset:
        _id, date, amount, category, type_, desc = r
        amt_str = f"{amount:,.2f}"
        print(f"{_id:>3}  {date:10}  {amt_str:10}  {type_:7}  {category:15.15}  {desc or ''}")
    print("-"*80)

def view_transactions_ui():
    rows = database.get_all_transactions(order_desc=True)
    if not rows:
        print("No transactions to show.")
        return
    page = 0
    while True:
        print_rows(rows, page)
        cmd = input("Commands: [n]ext page, [p]rev page, [d]elete <id>, [b]ack: ").strip().lower()
        if cmd == "n":
            if (page+1)*PAGE_SIZE >= len(rows):
                print("No more pages.")
            else:
                page += 1
        elif cmd == "p":
            if page == 0:
                print("Already at first page.")
            else:
                page -= 1
        elif cmd.startswith("d"):
            parts = cmd.split()
            if len(parts) == 2 and parts[1].isdigit():
                tx_id = int(parts[1])
                ok = database.delete_transaction(tx_id)
                if ok:
                    print(f"Transaction {tx_id} deleted.")
                    rows = database.get_all_transactions(order_desc=True)
                    if page*PAGE_SIZE >= len(rows) and page > 0:
                        page -= 1
                else:
                    print("No transaction with that id.")
            else:
                print("To delete: d <id>  (example: d 5)")
        elif cmd == "b":
            break
        else:
            print("Unknown command.")

def summary_ui():
    print("\n--- Summary ---")
    income, expense = database.get_summary()
    net = income - expense
    print(f"Total income : {income:,.2f}")
    print(f"Total expense: {expense:,.2f}")
    print(f"Net balance  : {net:,.2f}")
    print("\nYou can also view a monthly breakdown.")
    while True:
        s = input("Show month summary? Enter YYYY-MM or press Enter to go back: ").strip()
        if s == "":
            break
        try:
            dt = datetime.strptime(s, "%Y-%m")
            month_rows = database.get_transactions_by_month(dt.year, dt.month)
            inc = sum(r[2] for r in month_rows if r[4] == "income")
            exp = sum(r[2] for r in month_rows if r[4] == "expense")
            print(f"\nSummary for {s}: income={inc:,.2f}, expense={exp:,.2f}, net={(inc-exp):,.2f}")
            print_rows(month_rows, 0)
        except ValueError:
            print("Invalid month format. Use YYYY-MM (example: 2025-11).")

def export_ui():
    print("\n--- Export Transactions to CSV ---")
    fn = input("Filename (default: export.csv): ").strip() or "export.csv"
    rows = database.get_all_transactions(order_desc=False)
    database.export_transactions_to_csv(fn, rows)
    print(f"Exported {len(rows)} rows to {fn}.")

def filter_ui():
    print("\n--- Filter Transactions ---")
    print("1) Date range")
    print("2) Month")
    print("3) Category")
    print("4) Back")
    choice = input("Choose: ").strip()
    if choice == "1":
        start = input("Start date (YYYY-MM-DD): ").strip()
        end = input("End date (YYYY-MM-DD): ").strip()
        if not (database.validate_date_str(start) and database.validate_date_str(end)):
            print("Invalid date(s). Returning.")
            return
        rows = database.get_transactions_between(start, end)
        print_rows(rows)
    elif choice == "2":
        s = input("Enter month (YYYY-MM): ").strip()
        try:
            dt = datetime.strptime(s, "%Y-%m")
            rows = database.get_transactions_by_month(dt.year, dt.month)
            print_rows(rows)
        except ValueError:
            print("Invalid format.")
    elif choice == "3":
        cat = input("Category (exact match): ").strip()
        if not cat:
            print("Empty category.")
            return
        # simple filter in Python
        rows = [r for r in database.get_all_transactions() if r[3].lower() == cat.lower()]
        print_rows(rows)
    else:
        return

def seed_demo_data():
    """Optionally insert some demo data for quick testing."""
    demo = [
        ("2025-11-01", 2500.00, "Salary", "income", "November salary"),
        ("2025-11-06", 45.60, "Groceries", "expense", "Weekly shop"),
        ("2025-11-07", 12.50, "Transport", "expense", "Bus pass top-up"),
        ("2025-11-09", 120.00, "Utilities", "expense", "Electricity bill"),
        ("2025-11-15", 100.00, "Freelance", "income", "Side gig"),
    ]
    for row in demo:
        database.add_transaction(*row)
    print("Demo data seeded.")

def main_menu():
    database.create_table()
    print("Welcome to the Personal Budget Tracker!")
    while True:
        print("\n--- Main Menu ---")
        print("1) Add transaction")
        print("2) View transactions")
        print("3) Summary")
        print("4) Filter transactions")
        print("5) Export to CSV")
        print("6) Seed demo data (for testing)")
        print("7) Exit")
        choice = input("Select an option: ").strip()
        if choice == "1":
            add_transaction_ui()
        elif choice == "2":
            view_transactions_ui()
        elif choice == "3":
            summary_ui()
        elif choice == "4":
            filter_ui()
        elif choice == "5":
            export_ui()
        elif choice == "6":
            seed_demo_data()
        elif choice == "7":
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid option. Try again.")

if __name__ == "__main__":
    main_menu()
