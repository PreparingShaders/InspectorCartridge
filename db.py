# db.py
import sqlite3
from datetime import datetime

DB_NAME = "inventory.db"

# --- Инициализация базы данных и таблиц ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Таблица складов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        # Таблица типов картриджей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cartridge_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL UNIQUE
            )
        ''')

        # Таблица операций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                barcode TEXT,
                warehouse_id INTEGER,
                cartridge_type_id INTEGER,
                quantity INTEGER NOT NULL,
                operation_type TEXT CHECK(operation_type IN ('приход', 'расход')),
                user TEXT,
                comment TEXT,
                FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
                FOREIGN KEY (cartridge_type_id) REFERENCES cartridge_types(id)
            )
        ''')

        conn.commit()

# --- Добавление склада ---
def add_warehouse(name: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO warehouses (name) VALUES (?)', (name,))
        conn.commit()

# --- Добавление типа картриджа ---
def add_cartridge_type(model: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO cartridge_types (model) VALUES (?)', (model,))
        conn.commit()

# --- Получение ID склада по имени ---
def get_warehouse_id(name: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM warehouses WHERE name = ?', (name,))
        result = cursor.fetchone()
        return result[0] if result else None

# --- Получение ID картриджа по модели ---
def get_cartridge_type_id(model: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM cartridge_types WHERE model = ?', (model,))
        result = cursor.fetchone()
        return result[0] if result else None

# --- Добавление операции (приход/расход) ---
def add_transaction(barcode: str, warehouse_name: str, model: str, quantity: int, operation_type: str, user: str, comment: str):
    warehouse_id = get_warehouse_id(warehouse_name)
    cartridge_type_id = get_cartridge_type_id(model)

    if warehouse_id is None:
        raise ValueError(f"Склад '{warehouse_name}' не найден в базе данных.")
    if cartridge_type_id is None:
        raise ValueError(f"Картридж '{model}' не найден в базе данных.")

    date = datetime.now().strftime("%d.%m.%Y")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (
                date, barcode, warehouse_id, cartridge_type_id,
                quantity, operation_type, user, comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, barcode, warehouse_id, cartridge_type_id, quantity, operation_type, user, comment))
        conn.commit()

def seed_data():
    """Наполняет базу начальными складами и картриджами"""
    warehouses = ["Невская", "Новороссийская"]
    cartridges = [
        "CE255X", "CF259X", "CE278A", "CE390X", "CE410A",
        "CE411A", "CE412A", "CE413A", "CF226X", "CF230X",
        "CF232X", "CF237A", "CF280X", "CF281X", "CF283X",
        "CF287A", "CF410X", "CF411X", "CF412X", "CF413X"
    ]

    for wh in warehouses:
        add_warehouse(wh)

    for cart in cartridges:
        add_cartridge_type(cart)

    print("База успешно инициализирована начальными данными.")


def get_all_cartridge_models():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT model FROM cartridge_types ORDER BY model")
        return [row[0] for row in cursor.fetchall()]


