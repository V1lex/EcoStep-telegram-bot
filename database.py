import sqlite3
from datetime import datetime

DB_NAME = 'ecostep.db'

def init_db():
    """Инициализация базы данных и создание таблицы users"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            registration_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def register_user(user_id: int, username: str, first_name: str):
    """Регистрация нового пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Проверяем, есть ли пользователь
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        conn.close()
        return False  # Уже зарегистрирован
    
    # Добавляем нового пользователя
    cursor.execute(
        "INSERT INTO users (user_id, username, first_name, registration_date) VALUES (?, ?, ?, ?)",
        (user_id, username, first_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()
    return True  # Успешная регистрация

def get_user_info(user_id: int):
    """Получить информацию о пользователе"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user
