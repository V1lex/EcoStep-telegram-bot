import sqlite3

conn = sqlite3.connect('ecostep.db')
cursor = conn.cursor()

# Показать всех пользователей
cursor.execute("SELECT * FROM users")
users = cursor.fetchall()

print("Пользователи в базе данных:")
for user in users:
    print(f"ID: {user[0]}, Username: {user[1]}, Имя: {user[2]}, Дата регистрации: {user[3]}")

conn.close()
