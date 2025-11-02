import sqlite3
from datetime import datetime
from collections.abc import Sequence

DB_NAME = 'ecostep.db'


def _get_connection() -> sqlite3.Connection:
    """Получить подключение к базе данных."""
    return sqlite3.connect(DB_NAME)


def init_db():
    """Инициализация базы данных и создание таблиц."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            registration_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_challenges (
            user_id INTEGER,
            challenge_id TEXT,
            status TEXT CHECK(status IN ('accepted', 'submitted')),
            accepted_at TEXT,
            submitted_at TEXT,
            photo_file_id TEXT,
            caption TEXT,
            PRIMARY KEY (user_id, challenge_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    conn.commit()
    conn.close()


def register_user(user_id: int, username: str, first_name: str):
    """Регистрация нового пользователя."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        conn.close()
        return False

    cursor.execute(
        '''
        INSERT INTO users (user_id, username, first_name, registration_date)
        VALUES (?, ?, ?, ?)
        ''',
        (user_id, username, first_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()
    return True


def get_user_info(user_id: int) -> tuple | None:
    """Получить информацию о пользователе."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_challenge_statuses(user_id: int) -> dict[str, str]:
    """Вернуть словарь с текущими статусами челленджей пользователя."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT challenge_id, status
        FROM user_challenges
        WHERE user_id = ?
        ''',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return {challenge_id: status for challenge_id, status in rows}


def accept_challenge(user_id: int, challenge_id: str) -> bool:
    """Отметить челлендж как принятый пользователем."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT status
        FROM user_challenges
        WHERE user_id = ? AND challenge_id = ?
        ''',
        (user_id, challenge_id)
    )
    existing = cursor.fetchone()
    if existing and existing[0] == 'submitted':
        conn.close()
        return False

    accepted_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if existing:
        cursor.execute(
            '''
            UPDATE user_challenges
            SET status = 'accepted',
                accepted_at = ?,
                submitted_at = NULL,
                photo_file_id = NULL,
                caption = NULL
            WHERE user_id = ? AND challenge_id = ?
            ''',
            (accepted_at, user_id, challenge_id)
        )
    else:
        cursor.execute(
            '''
            INSERT INTO user_challenges (
                user_id, challenge_id, status, accepted_at
            )
            VALUES (?, ?, 'accepted', ?)
            ''',
            (user_id, challenge_id, accepted_at)
        )
    conn.commit()
    conn.close()
    return True


def decline_challenge(user_id: int, challenge_id: str) -> bool:
    """Удалить принятый челлендж, если пользователь отказался."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        DELETE FROM user_challenges
        WHERE user_id = ? AND challenge_id = ? AND status = 'accepted'
        ''',
        (user_id, challenge_id)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def mark_challenge_submitted(
    user_id: int,
    challenge_id: str,
    photo_file_id: str,
    caption: str | None = None
) -> bool:
    """Обновить статус челленджа как отправленного на проверку."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT status
        FROM user_challenges
        WHERE user_id = ? AND challenge_id = ?
        ''',
        (user_id, challenge_id)
    )
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return False

    submitted_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        '''
        UPDATE user_challenges
        SET status = 'submitted',
            submitted_at = ?,
            photo_file_id = ?,
            caption = ?
        WHERE user_id = ? AND challenge_id = ?
        ''',
        (submitted_at, photo_file_id, caption, user_id, challenge_id)
    )
    conn.commit()
    conn.close()
    return True


def get_user_challenges_by_status(
    user_id: int,
    statuses: Sequence[str]
) -> list[tuple[str, str, str | None, str | None, str | None]]:
    """Получить список челленджей пользователя для указанных статусов."""
    if not statuses:
        return []

    placeholders = ",".join("?" * len(statuses))
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f'''
        SELECT challenge_id, status, submitted_at, photo_file_id, caption
        FROM user_challenges
        WHERE user_id = ? AND status IN ({placeholders})
        ORDER BY accepted_at ASC
        ''',
        (user_id, *statuses)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_submitted_challenges(user_id: int) -> list[tuple[str, str, str, str, str]]:
    """Получить отправленные на проверку челленджи пользователя."""
    return get_user_challenges_by_status(user_id, ('submitted',))


def get_accepted_challenges(user_id: int) -> list[str]:
    """Получить принятые, но не отправленные челленджи."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT challenge_id
        FROM user_challenges
        WHERE user_id = ? AND status = 'accepted'
        ORDER BY accepted_at ASC
        ''',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [challenge_id for (challenge_id,) in rows]


def clear_challenge_state(user_id: int, challenge_id: str):
    """Сбросить временное состояние принятых челленджей (для служебных целей)."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        UPDATE user_challenges
        SET status = 'accepted',
            submitted_at = NULL,
            photo_file_id = NULL,
            caption = NULL
        WHERE user_id = ? AND challenge_id = ? AND status != 'submitted'
        ''',
        (user_id, challenge_id)
    )
    conn.commit()
    conn.close()
