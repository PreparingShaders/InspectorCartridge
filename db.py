import sqlite3

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
