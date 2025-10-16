import sqlite3
from datetime import datetime

DB_FILE = "cartridges.db"

# --------- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cartridges (
            name TEXT PRIMARY KEY,
            qty INTEGER NOT NULL DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            user TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS barcodes (
            barcode TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            UNIQUE(barcode)
        )
    """)
    conn.commit()
    conn.close()


# --------- ОПЕРАЦИИ С КАРТРИДЖАМИ ---------
def add_cartridge(name, qty, user):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cartridges(name, qty)
        VALUES(?, ?)
        ON CONFLICT(name) DO UPDATE SET qty = qty + ?
    """, (name, qty, qty))
    cur.execute("""
        INSERT INTO history(action, name, qty, user, timestamp)
        VALUES(?, ?, ?, ?, ?)
    """, ("add", name, qty, user, datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def use_cartridge(name, qty, user):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT qty FROM cartridges WHERE name=?", (name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return "❌ Картридж не найден."
    if row[0] < qty:
        conn.close()
        return f"⚠️ Недостаточно на складе. Остаток: {row[0]}"
    cur.execute("UPDATE cartridges SET qty = qty - ? WHERE name=?", (qty, name))
    cur.execute("""
        INSERT INTO history(action, name, qty, user, timestamp)
        VALUES(?, ?, ?, ?, ?)
    """, ("use", name, qty, user, datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()
    return f"📤 Списано {qty} шт. *{name}*."


def get_status():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT name, qty FROM cartridges ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "📭 Склад пуст."
    return "\n".join(f"• {name}: {qty}" for name, qty in rows)


def get_history(limit=10):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT action, name, qty, user, timestamp
        FROM history ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "🕓 История пуста."
    lines = []
    for action, name, qty, user, timestamp in rows:
        icon = "➕" if action == "add" else "➖"
        who = f" ({user})" if user else ""
        lines.append(f"{icon} {timestamp}: {name} — {qty} шт{who}")
    return "\n".join(lines)


def find_name_by_barcode(barcode):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT name FROM barcodes WHERE barcode = ?", (barcode,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def add_barcode_mapping(barcode, name):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO barcodes(barcode, name) VALUES(?, ?)", (barcode, name))
    conn.commit()
    conn.close()
