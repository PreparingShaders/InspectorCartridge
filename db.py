import sqlite3
from datetime import datetime

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
        cursor.execute("SELECT model FROM cartridge_types ORDER BY model")
        results = cursor.fetchall()
        return [row[0] for row in results]

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


def save_transaction(user_state: dict, username: str):
    """Добавляет операцию (приход или расход) в базу данных."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Извлекаем значения из состояния
        warehouse_name = user_state.get("warehouse")
        model_name = user_state.get("model")
        barcode = user_state.get("barcode")
        operation = user_state.get("operation")
        comment = user_state.get("comment")
        quantity = -1 if operation == "расход" else 1  # приход = +1, расход = -1

        # Находим warehouse_id
        cursor.execute("SELECT id FROM warehouses WHERE name = ?", (warehouse_name,))
        warehouse_row = cursor.fetchone()
        if not warehouse_row:
            raise ValueError(f"Склад '{warehouse_name}' не найден.")
        warehouse_id = warehouse_row[0]

        # Находим cartridge_type_id
        cursor.execute("SELECT id FROM cartridge_types WHERE model = ?", (model_name,))
        cartridge_row = cursor.fetchone()
        if not cartridge_row:
            raise ValueError(f"Модель картриджа '{model_name}' не найдена.")
        cartridge_type_id = cartridge_row[0]

        # Формируем дату
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Добавляем запись
        cursor.execute(
            """
            INSERT INTO transactions (
                date, barcode, warehouse_id, cartridge_type_id, quantity, 
                operation_type, user, comment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_now,
                barcode,
                warehouse_id,
                cartridge_type_id,
                quantity,
                operation,
                username,
                comment,
            ),
        )

        conn.commit()
        print(f"✅ {operation.title()} картриджа {model_name} успешно записан в базу.")