import sqlite3
from datetime import datetime, timedelta
import re

DB_NAME = "inventory.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Включаем поддержку внешних ключей
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Таблица складов
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS warehouses
                       (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE
                       )
                       ''')

        # Таблица типов картриджей
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS cartridge_types
                       (
                           id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           model TEXT NOT NULL UNIQUE
                       )
                       ''')

        # Таблица операций
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS transactions
                       (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           date TEXT NOT NULL,
                           barcode TEXT, warehouse_id INTEGER,
                           cartridge_type_id INTEGER,
                           quantity INTEGER NOT NULL,
                           operation_type TEXT CHECK ( operation_type IN ( 'приход', 'расход')),
                           user TEXT, comment TEXT, FOREIGN KEY(warehouse_id) REFERENCES warehouses(id),
                           FOREIGN KEY(cartridge_type_id) REFERENCES cartridge_types(id)
                           )
                       ''')

        # Начальное заполнение складов и картриджей
        warehouses = ["Невская", "Новороссийская"]
        cartridges = [
            "CE255X", "CF259X", "CE278A", "CE390X", "CE410A",
            "CE411A", "CE412A", "CE413A", "CF226X", "CF230X",
            "CF232X", "CF237A", "CF280X", "CF281X", "CF283X",
            "CF287A", "CF410X", "CF411X", "CF412X", "CF413X"
        ]

        for wh in warehouses:
            cursor.execute('INSERT OR IGNORE INTO warehouses (name) VALUES (?)', (wh,))

        for cart in cartridges:
            cursor.execute('INSERT OR IGNORE INTO cartridge_types (model) VALUES (?)', (cart,))

        conn.commit()
        print("База инициализирована и заполнена начальными данными.")


def get_all_cartridge_types():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT model FROM cartridge_types")
        results = [row[0] for row in cursor.fetchall()]

    # Функция для извлечения числа из модели
    def extract_number(model):
        match = re.search(r'\d+', model)
        return int(match.group()) if match else float('inf')

    # Сортируем по числу и по названию модели
    results.sort(key=lambda x: (extract_number(x), x))

    # Ищем индекс CF226X, чтобы поставить его в начало (если нужно)
    if "CF226X" in results:
        idx = results.index("CF226X")
        results = results[idx:] + results[:idx]

    # Делим на левый и правый столбцы
    mid = (len(results) + 1) // 2
    left_col = results[:mid]
    right_col = results[mid:]

    # Склеиваем сначала левый столбец, потом правый
    final_results = left_col + right_col

    return final_results

def get_stock_grouped_by_warehouse():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                w.name AS warehouse,
                ct.model AS model,
                SUM(t.quantity) AS stock
            FROM transactions t
            JOIN warehouses w ON t.warehouse_id = w.id
            JOIN cartridge_types ct ON t.cartridge_type_id = ct.id
            GROUP BY w.name, ct.model
            ORDER BY w.name, ct.model;
        """)
        return cursor.fetchall()

def can_spend_cartridge(warehouse_id, cartridge_type_id, barcode=None):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        query = """
            SELECT SUM(quantity)
            FROM transactions
            WHERE warehouse_id=? AND cartridge_type_id=?
        """
        params = [warehouse_id, cartridge_type_id]

        if barcode and barcode != "отсутствует":
            query += " AND barcode=?"
            params.append(barcode)
        else:
            query += " AND (barcode IS NULL OR barcode='отсутствует')"

        cursor.execute(query, params)
        stock = cursor.fetchone()[0] or 0
        return stock > 0

def save_transaction(user_state: dict, username: str):
    warehouse_name = user_state.get("warehouse")
    model_name = user_state.get("model")
    barcode = user_state.get("barcode")
    operation = user_state.get("operation")
    comment = user_state.get("comment")
    quantity = 1 if operation == "приход" else -1

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Получаем ID склада и модели
        cursor.execute("SELECT id FROM warehouses WHERE name=?", (warehouse_name,))
        warehouse_id = cursor.fetchone()[0]

        cursor.execute("SELECT id FROM cartridge_types WHERE model=?", (model_name,))
        cartridge_type_id = cursor.fetchone()[0]

        # Проверка перед списанием
        if operation == "расход" and not can_spend_cartridge(warehouse_id, cartridge_type_id, barcode):
            raise ValueError(f"Невозможно списать картридж {model_name} с barcode {barcode}. Нет доступного экземпляра.")

        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Добавляем транзакцию
        cursor.execute("""
            INSERT INTO transactions 
                (date, barcode, warehouse_id, cartridge_type_id, quantity, operation_type, user, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date_now, barcode, warehouse_id, cartridge_type_id, quantity, operation, username, comment))

        conn.commit()


def get_transactions_by_period(date_from: datetime, date_to: datetime):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                t.date,
                w.name AS warehouse,
                ct.model AS cartridge,
                t.barcode,
                t.operation_type,
                t.user,
                t.comment
            FROM transactions t
            JOIN warehouses w ON t.warehouse_id = w.id
            JOIN cartridge_types ct ON t.cartridge_type_id = ct.id
            WHERE date(t.date) BETWEEN date(?) AND date(?)
            ORDER BY datetime(t.date) DESC
            LIMIT 50
        """, (
            date_from.strftime("%Y-%m-%d"),
            date_to.strftime("%Y-%m-%d")
        ))
        return cursor.fetchall()
