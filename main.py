import csv
import hashlib
import json
import os
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, filedialog

APP_NAME = "Amit Tex Business Manager"
DB_FILE = "amit_tex.db"

FEATURES = [
    "stock",
    "billing",
    "challan",
    "admin_panel",
    "data_share",
]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class Database:
    def __init__(self, db_file: str = DB_FILE):
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self.setup()

    def setup(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'sub_admin', 'temp')),
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                feature TEXT NOT NULL,
                allowed INTEGER NOT NULL DEFAULT 1,
                UNIQUE(user_id, feature),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT UNIQUE NOT NULL,
                cloth_name TEXT NOT NULL,
                variety TEXT,
                color TEXT,
                unit TEXT DEFAULT 'meter',
                quantity REAL NOT NULL,
                cost_price REAL NOT NULL,
                sell_price REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                customer_phone TEXT,
                subtotal REAL NOT NULL,
                gst_pct REAL NOT NULL,
                total REAL NOT NULL,
                created_at TEXT NOT NULL,
                created_by INTEGER,
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                stock_id INTEGER NOT NULL,
                qty REAL NOT NULL,
                price REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id),
                FOREIGN KEY(stock_id) REFERENCES stock_items(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS challans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challan_no TEXT UNIQUE NOT NULL,
                party_name TEXT NOT NULL,
                vehicle_no TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                created_by INTEGER,
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
            """
        )
        self.conn.commit()

        # Seed default admin
        cur.execute("SELECT id FROM users WHERE username='admin'")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users(username,password_hash,role,active) VALUES(?,?,?,1)",
                ("admin", hash_password("admin123"), "admin"),
            )
            admin_id = cur.lastrowid
            for feature in FEATURES:
                cur.execute(
                    "INSERT OR IGNORE INTO permissions(user_id,feature,allowed) VALUES(?,?,1)",
                    (admin_id, feature),
                )
            self.conn.commit()

    def login(self, username: str, password: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=? AND active=1",
            (username, hash_password(password)),
        )
        return cur.fetchone()

    def get_permissions(self, user_id: int):
        cur = self.conn.cursor()
        cur.execute("SELECT feature, allowed FROM permissions WHERE user_id=?", (user_id,))
        rows = cur.fetchall()
        if not rows:
            # Default role-level behavior for new users
            return {f: 1 for f in FEATURES}
        return {r["feature"]: r["allowed"] for r in rows}


class LoginWindow:
    def __init__(self, root, db: Database):
        self.root = root
        self.db = db
        self.user = None
        self.root.title(f"{APP_NAME} - Login")
        self.root.geometry("430x330")
        self.root.resizable(False, False)

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        logo = tk.Canvas(frame, width=360, height=80, bg="#1f3a93", highlightthickness=0)
        logo.create_text(180, 24, text="AMIT TEX", fill="white", font=("Segoe UI", 22, "bold"))
        logo.create_text(
            180,
            54,
            text="Textile Business Management | Surat, Gujarat",
            fill="#dfe6ff",
            font=("Segoe UI", 10),
        )
        logo.grid(row=0, column=0, columnspan=2, pady=(0, 16))

        ttk.Label(frame, text="Username").grid(row=1, column=0, sticky="w", pady=6)
        self.user_entry = ttk.Entry(frame, width=28)
        self.user_entry.grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(frame, text="Password").grid(row=2, column=0, sticky="w", pady=6)
        self.pass_entry = ttk.Entry(frame, show="*", width=28)
        self.pass_entry.grid(row=2, column=1, sticky="ew", pady=6)

        ttk.Button(frame, text="Login", command=self.try_login).grid(
            row=3, column=0, columnspan=2, pady=16
        )
        ttk.Label(
            frame,
            text="Default admin login: admin / admin123",
            foreground="#3b3b3b",
        ).grid(row=4, column=0, columnspan=2)

    def try_login(self):
        user = self.db.login(self.user_entry.get().strip(), self.pass_entry.get().strip())
        if not user:
            messagebox.showerror("Login failed", "Invalid credentials or inactive account.")
            return
        self.user = user
        self.root.destroy()


class App:
    def __init__(self, user, db: Database):
        self.user = user
        self.db = db
        self.permissions = db.get_permissions(user["id"])

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1080x700")

        header = ttk.Frame(self.root, padding=8)
        header.pack(fill="x")
        ttk.Label(
            header,
            text=f"AMIT TEX | Logged in as: {self.user['username']} ({self.user['role']})",
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.stock_tree = None
        self.users_tree = None
        self.invoice_items = []

        if self.permissions.get("stock", 0):
            self.build_stock_tab()
        if self.permissions.get("billing", 0):
            self.build_billing_tab()
        if self.permissions.get("challan", 0):
            self.build_challan_tab()
        if self.permissions.get("data_share", 0):
            self.build_share_tab()
        if self.user["role"] == "admin" and self.permissions.get("admin_panel", 0):
            self.build_admin_tab()

    # ---------------- Stock ----------------
    def build_stock_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Stock")

        form = ttk.Frame(tab)
        form.pack(fill="x", pady=4)

        labels = ["SKU", "Cloth Name", "Variety", "Color", "Qty", "Cost", "Sell"]
        self.stock_entries = {}
        for i, lbl in enumerate(labels):
            ttk.Label(form, text=lbl).grid(row=0, column=i, padx=3, sticky="w")
            e = ttk.Entry(form, width=12)
            e.grid(row=1, column=i, padx=3)
            self.stock_entries[lbl.lower().replace(" ", "_")] = e

        ttk.Button(form, text="Add/Update", command=self.add_stock).grid(row=1, column=len(labels), padx=8)

        self.stock_tree = ttk.Treeview(
            tab,
            columns=("sku", "cloth", "variety", "color", "qty", "sell"),
            show="headings",
            height=18,
        )
        for c in ("sku", "cloth", "variety", "color", "qty", "sell"):
            self.stock_tree.heading(c, text=c.upper())
            self.stock_tree.column(c, width=130)
        self.stock_tree.pack(fill="both", expand=True, pady=8)
        self.refresh_stock_tree()

    def add_stock(self):
        e = self.stock_entries
        sku = e["sku"].get().strip()
        if not sku:
            messagebox.showerror("Error", "SKU is required")
            return

        data = (
            sku,
            e["cloth_name"].get().strip(),
            e["variety"].get().strip(),
            e["color"].get().strip(),
            float(e["qty"].get() or 0),
            float(e["cost"].get() or 0),
            float(e["sell"].get() or 0),
            datetime.utcnow().isoformat(),
        )

        cur = self.db.conn.cursor()
        cur.execute("SELECT id FROM stock_items WHERE sku=?", (sku,))
        exists = cur.fetchone()
        if exists:
            cur.execute(
                """
                UPDATE stock_items
                SET cloth_name=?, variety=?, color=?, quantity=?, cost_price=?, sell_price=?, updated_at=?
                WHERE sku=?
                """,
                (data[1], data[2], data[3], data[4], data[5], data[6], data[7], sku),
            )
        else:
            cur.execute(
                """
                INSERT INTO stock_items(sku, cloth_name, variety, color, quantity, cost_price, sell_price, updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                data,
            )
        self.db.conn.commit()
        self.refresh_stock_tree()

    def refresh_stock_tree(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM stock_items ORDER BY id DESC")
        rows = cur.fetchall()
        if self.stock_tree is not None:
            for i in self.stock_tree.get_children():
                self.stock_tree.delete(i)
            for r in rows:
                self.stock_tree.insert(
                    "", "end", values=(r["sku"], r["cloth_name"], r["variety"], r["color"], r["quantity"], r["sell_price"])
                )
        if hasattr(self, "stock_pick"):
            self.stock_pick["values"] = [f"{r['id']} | {r['sku']} | {r['cloth_name']}" for r in rows]

    # ---------------- Billing ----------------
    def build_billing_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Billing")

        top = ttk.Frame(tab)
        top.pack(fill="x")
        ttk.Label(top, text="Customer Name").grid(row=0, column=0, sticky="w")
        self.customer_name = ttk.Entry(top, width=24)
        self.customer_name.grid(row=0, column=1, padx=5)

        ttk.Label(top, text="Phone").grid(row=0, column=2, sticky="w")
        self.customer_phone = ttk.Entry(top, width=16)
        self.customer_phone.grid(row=0, column=3, padx=5)

        ttk.Label(top, text="GST %").grid(row=0, column=4, sticky="w")
        self.gst_entry = ttk.Entry(top, width=8)
        self.gst_entry.insert(0, "5")
        self.gst_entry.grid(row=0, column=5, padx=5)

        item = ttk.Frame(tab)
        item.pack(fill="x", pady=8)
        self.stock_pick = ttk.Combobox(item, width=45)
        self.stock_pick.grid(row=0, column=0, padx=5)
        self.bill_qty = ttk.Entry(item, width=10)
        self.bill_qty.grid(row=0, column=1, padx=5)
        self.bill_qty.insert(0, "1")
        ttk.Button(item, text="Add Item", command=self.add_bill_item).grid(row=0, column=2, padx=6)

        self.bill_tree = ttk.Treeview(
            tab, columns=("stock_id", "name", "qty", "price", "total"), show="headings", height=12
        )
        for c in ("stock_id", "name", "qty", "price", "total"):
            self.bill_tree.heading(c, text=c.upper())
            self.bill_tree.column(c, width=140)
        self.bill_tree.pack(fill="both", expand=True)

        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Generate Invoice", command=self.generate_invoice).pack(side="left")
        self.bill_summary = ttk.Label(actions, text="Subtotal: 0.00 | Total: 0.00")
        self.bill_summary.pack(side="left", padx=20)

        self.refresh_stock_tree()

    def add_bill_item(self):
        pick = self.stock_pick.get().strip()
        if not pick:
            return
        stock_id = int(pick.split("|")[0].strip())
        qty = float(self.bill_qty.get() or 0)
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM stock_items WHERE id=?", (stock_id,))
        stock = cur.fetchone()
        if not stock:
            return
        if qty <= 0 or qty > stock["quantity"]:
            messagebox.showerror("Invalid qty", "Qty must be > 0 and <= available stock")
            return
        line_total = qty * stock["sell_price"]
        self.invoice_items.append({"stock": stock, "qty": qty, "line": line_total})
        self.bill_tree.insert(
            "", "end", values=(stock["id"], stock["cloth_name"], qty, stock["sell_price"], round(line_total, 2))
        )
        subtotal = sum(x["line"] for x in self.invoice_items)
        gst = float(self.gst_entry.get() or 0)
        total = subtotal + subtotal * gst / 100
        self.bill_summary.config(text=f"Subtotal: {subtotal:.2f} | Total: {total:.2f}")

    def generate_invoice(self):
        if not self.invoice_items:
            messagebox.showerror("Error", "No items in invoice")
            return
        customer = self.customer_name.get().strip() or "Walk-in"
        phone = self.customer_phone.get().strip()
        gst = float(self.gst_entry.get() or 0)
        subtotal = sum(x["line"] for x in self.invoice_items)
        total = subtotal + subtotal * gst / 100
        invoice_no = f"INV-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        cur = self.db.conn.cursor()
        cur.execute(
            """
            INSERT INTO invoices(invoice_no, customer_name, customer_phone, subtotal, gst_pct, total, created_at, created_by)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (invoice_no, customer, phone, subtotal, gst, total, datetime.utcnow().isoformat(), self.user["id"]),
        )
        invoice_id = cur.lastrowid
        for item in self.invoice_items:
            cur.execute(
                "INSERT INTO invoice_items(invoice_id, stock_id, qty, price, line_total) VALUES(?,?,?,?,?)",
                (invoice_id, item["stock"]["id"], item["qty"], item["stock"]["sell_price"], item["line"]),
            )
            cur.execute(
                "UPDATE stock_items SET quantity = quantity - ?, updated_at=? WHERE id=?",
                (item["qty"], datetime.utcnow().isoformat(), item["stock"]["id"]),
            )
        self.db.conn.commit()
        messagebox.showinfo("Invoice Created", f"Invoice {invoice_no} generated successfully.")
        self.invoice_items.clear()
        for i in self.bill_tree.get_children():
            self.bill_tree.delete(i)
        self.bill_summary.config(text="Subtotal: 0.00 | Total: 0.00")
        self.refresh_stock_tree()

    # ---------------- Challan ----------------
    def build_challan_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Challan")

        form = ttk.Frame(tab)
        form.pack(fill="x")
        self.challan_no = ttk.Entry(form, width=20)
        self.party_name = ttk.Entry(form, width=24)
        self.vehicle_no = ttk.Entry(form, width=14)
        self.challan_notes = ttk.Entry(form, width=40)

        for idx, (lbl, widget) in enumerate(
            [
                ("Challan No", self.challan_no),
                ("Party", self.party_name),
                ("Vehicle", self.vehicle_no),
                ("Notes", self.challan_notes),
            ]
        ):
            ttk.Label(form, text=lbl).grid(row=0, column=idx, sticky="w", padx=3)
            widget.grid(row=1, column=idx, padx=3)

        ttk.Button(form, text="Save Challan", command=self.save_challan).grid(row=1, column=4, padx=8)

        self.challan_tree = ttk.Treeview(tab, columns=("no", "party", "vehicle", "created"), show="headings")
        for c in ("no", "party", "vehicle", "created"):
            self.challan_tree.heading(c, text=c.upper())
            self.challan_tree.column(c, width=200)
        self.challan_tree.pack(fill="both", expand=True, pady=8)
        self.refresh_challan()

    def save_challan(self):
        challan_no = self.challan_no.get().strip()
        if not challan_no:
            messagebox.showerror("Error", "Challan no is required")
            return
        cur = self.db.conn.cursor()
        cur.execute(
            """
            INSERT INTO challans(challan_no, party_name, vehicle_no, notes, created_at, created_by)
            VALUES(?,?,?,?,?,?)
            """,
            (
                challan_no,
                self.party_name.get().strip(),
                self.vehicle_no.get().strip(),
                self.challan_notes.get().strip(),
                datetime.utcnow().isoformat(),
                self.user["id"],
            ),
        )
        self.db.conn.commit()
        self.refresh_challan()

    def refresh_challan(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT challan_no, party_name, vehicle_no, created_at FROM challans ORDER BY id DESC")
        rows = cur.fetchall()
        if hasattr(self, "challan_tree"):
            for i in self.challan_tree.get_children():
                self.challan_tree.delete(i)
            for r in rows:
                self.challan_tree.insert("", "end", values=(r["challan_no"], r["party_name"], r["vehicle_no"], r["created_at"][:19]))

    # ---------------- Share / Export ----------------
    def build_share_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Data Share")

        ttk.Label(tab, text="Export/Import business data to share with other branches/users.").pack(anchor="w")
        actions = ttk.Frame(tab)
        actions.pack(anchor="w", pady=8)
        ttk.Button(actions, text="Export JSON", command=self.export_json).pack(side="left", padx=4)
        ttk.Button(actions, text="Import JSON", command=self.import_json).pack(side="left", padx=4)

    def export_json(self):
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not file:
            return
        cur = self.db.conn.cursor()
        payload = {}
        for table in ["stock_items", "invoices", "invoice_items", "challans", "users", "permissions"]:
            cur.execute(f"SELECT * FROM {table}")
            payload[table] = [dict(r) for r in cur.fetchall()]
        with open(file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        messagebox.showinfo("Export done", f"Data exported to {file}")

    def import_json(self):
        file = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not file:
            return
        with open(file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        cur = self.db.conn.cursor()
        for table in ["stock_items", "invoices", "invoice_items", "challans", "users", "permissions"]:
            if table not in payload:
                continue
            cols_cur = cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cols_cur.fetchall()]
            ph = ",".join(["?"] * len(cols))
            col_names = ",".join(cols)
            for row in payload[table]:
                values = [row.get(c) for c in cols]
                cur.execute(f"INSERT OR REPLACE INTO {table}({col_names}) VALUES({ph})", values)
        self.db.conn.commit()
        messagebox.showinfo("Import done", f"Imported data from {os.path.basename(file)}")
        self.refresh_stock_tree()
        self.refresh_challan()

    # ---------------- Admin ----------------
    def build_admin_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Admin Panel")

        user_form = ttk.LabelFrame(tab, text="Create / Manage User", padding=8)
        user_form.pack(fill="x")

        self.new_user = ttk.Entry(user_form, width=18)
        self.new_pass = ttk.Entry(user_form, width=16)
        self.new_role = ttk.Combobox(user_form, values=["sub_admin", "temp"], width=12)
        self.new_role.set("temp")
        self.new_active = tk.IntVar(value=1)

        ttk.Label(user_form, text="Username").grid(row=0, column=0, padx=4)
        self.new_user.grid(row=0, column=1, padx=4)
        ttk.Label(user_form, text="Password").grid(row=0, column=2, padx=4)
        self.new_pass.grid(row=0, column=3, padx=4)
        ttk.Label(user_form, text="Role").grid(row=0, column=4, padx=4)
        self.new_role.grid(row=0, column=5, padx=4)
        ttk.Checkbutton(user_form, text="Active", variable=self.new_active).grid(row=0, column=6, padx=4)
        ttk.Button(user_form, text="Save User", command=self.save_user).grid(row=0, column=7, padx=6)

        perms = ttk.LabelFrame(tab, text="Feature Access", padding=8)
        perms.pack(fill="x", pady=8)

        self.users_tree = ttk.Treeview(perms, columns=("id", "username", "role", "active"), show="headings", height=7)
        for c in ("id", "username", "role", "active"):
            self.users_tree.heading(c, text=c.upper())
            self.users_tree.column(c, width=120)
        self.users_tree.grid(row=0, column=0, rowspan=8, padx=6)

        self.feature_vars = {}
        for i, feature in enumerate(FEATURES):
            var = tk.IntVar(value=1)
            self.feature_vars[feature] = var
            ttk.Checkbutton(perms, text=feature, variable=var).grid(row=i, column=1, sticky="w")

        ttk.Button(perms, text="Load selected user", command=self.load_selected_permissions).grid(row=6, column=1, pady=4)
        ttk.Button(perms, text="Apply permissions", command=self.apply_permissions).grid(row=7, column=1, pady=4)

        self.refresh_users()

    def refresh_users(self):
        cur = self.db.conn.cursor()
        cur.execute("SELECT id, username, role, active FROM users ORDER BY id")
        rows = cur.fetchall()
        for i in self.users_tree.get_children():
            self.users_tree.delete(i)
        for r in rows:
            self.users_tree.insert("", "end", values=(r["id"], r["username"], r["role"], r["active"]))

    def save_user(self):
        username = self.new_user.get().strip()
        password = self.new_pass.get().strip()
        role = self.new_role.get().strip()
        if not username or not password or role not in ("sub_admin", "temp"):
            messagebox.showerror("Invalid", "Enter username, password and valid role")
            return
        cur = self.db.conn.cursor()
        cur.execute(
            "INSERT INTO users(username, password_hash, role, active) VALUES(?,?,?,?)",
            (username, hash_password(password), role, self.new_active.get()),
        )
        user_id = cur.lastrowid
        default_allowed = 1 if role == "sub_admin" else 0
        for f in FEATURES:
            cur.execute(
                "INSERT OR IGNORE INTO permissions(user_id, feature, allowed) VALUES(?,?,?)",
                (user_id, f, default_allowed),
            )
        self.db.conn.commit()
        self.refresh_users()

    def load_selected_permissions(self):
        selected = self.users_tree.selection()
        if not selected:
            return
        values = self.users_tree.item(selected[0], "values")
        user_id = int(values[0])
        perms = self.db.get_permissions(user_id)
        for f in FEATURES:
            self.feature_vars[f].set(int(perms.get(f, 0)))

    def apply_permissions(self):
        selected = self.users_tree.selection()
        if not selected:
            return
        values = self.users_tree.item(selected[0], "values")
        user_id = int(values[0])
        cur = self.db.conn.cursor()
        for f, var in self.feature_vars.items():
            cur.execute(
                "INSERT OR REPLACE INTO permissions(user_id, feature, allowed) VALUES(?,?,?)",
                (user_id, f, int(var.get())),
            )
        self.db.conn.commit()
        messagebox.showinfo("Saved", "Permissions updated")

    def run(self):
        self.root.mainloop()


def main():
    db = Database()
    login_root = tk.Tk()
    login = LoginWindow(login_root, db)
    login_root.mainloop()
    if login.user:
        app = App(login.user, db)
        app.run()


if __name__ == "__main__":
    main()
