import sqlite3
from collections.abc import Sequence
from datetime import datetime

DB_NAME = 'ecostep.db'


def _get_connection() -> sqlite3.Connection:
    """Создать подключение к базе."""
    conn = sqlite3.connect(DB_NAME)
    return conn


def init_db():
    """Инициализировать таблицы и недостающие поля."""
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
            review_status TEXT,
            review_comment TEXT,
            reviewed_at TEXT,
            points_awarded INTEGER,
            PRIMARY KEY (user_id, challenge_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            points INTEGER NOT NULL,
            co2 TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_friends (
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, friend_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (friend_id) REFERENCES users(user_id)
        )
    ''')

    cursor.execute("PRAGMA table_info(user_challenges)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if 'review_status' not in existing_columns:
        cursor.execute("ALTER TABLE user_challenges ADD COLUMN review_status TEXT")
    if 'review_comment' not in existing_columns:
        cursor.execute("ALTER TABLE user_challenges ADD COLUMN review_comment TEXT")
    if 'reviewed_at' not in existing_columns:
        cursor.execute("ALTER TABLE user_challenges ADD COLUMN reviewed_at TEXT")
    if 'attachment_type' not in existing_columns:
        cursor.execute("ALTER TABLE user_challenges ADD COLUMN attachment_type TEXT")
    if 'attachment_name' not in existing_columns:
        cursor.execute("ALTER TABLE user_challenges ADD COLUMN attachment_name TEXT")
    if 'points_awarded' not in existing_columns:
        cursor.execute("ALTER TABLE user_challenges ADD COLUMN points_awarded INTEGER")
    cursor.execute(
        "UPDATE user_challenges SET review_status = COALESCE(review_status, 'pending')"
    )
    cursor.execute(
        "UPDATE user_challenges SET attachment_type = COALESCE(attachment_type, 'photo')"
    )
    conn.commit()
    conn.close()


def register_user(user_id: int, username: str, first_name: str):
    """Зарегистрировать пользователя (если ещё нет)."""
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


def get_all_user_ids() -> list[int]:
    """Вернуть список ID всех пользователей."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids


def find_user_by_username(username: str) -> tuple[int, str | None, str | None] | None:
    """Найти пользователя по username (без учёта регистра)."""
    if not username:
        return None
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT user_id, username, first_name
        FROM users
        WHERE LOWER(username) = LOWER(?)
        LIMIT 1
        """,
        (username,)
    )
    row = cursor.fetchone()
    conn.close()
    return row


def add_friend(user_id: int, friend_id: int) -> bool:
    """Добавить друга (двусторонняя запись)."""
    if user_id == friend_id:
        return False

    conn = _get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        '''
        INSERT OR IGNORE INTO user_friends (user_id, friend_id, created_at)
        VALUES (?, ?, ?)
        ''',
        (user_id, friend_id, timestamp)
    )
    inserted_primary = cursor.rowcount > 0
    cursor.execute(
        '''
        INSERT OR IGNORE INTO user_friends (user_id, friend_id, created_at)
        VALUES (?, ?, ?)
        ''',
        (friend_id, user_id, timestamp)
    )
    conn.commit()
    conn.close()
    return inserted_primary


def remove_friend(user_id: int, friend_id: int) -> bool:
    """Удалить дружбу в обе стороны."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        DELETE FROM user_friends
        WHERE (user_id = ? AND friend_id = ?)
           OR (user_id = ? AND friend_id = ?)
        ''',
        (user_id, friend_id, friend_id, user_id)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_friends(user_id: int) -> list[dict]:
    """Вернуть список друзей пользователя."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT u.user_id, u.username, u.first_name, uf.created_at
        FROM user_friends AS uf
        JOIN users AS u ON u.user_id = uf.friend_id
        WHERE uf.user_id = ?
        ORDER BY u.first_name ASC
        ''',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "user_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "since": row[3],
        }
        for row in rows
    ]


def get_users_by_ids(user_ids: Sequence[int]) -> dict[int, dict[str, str | int | None]]:
    """Вернуть информацию о пользователях по списку ID."""
    unique_ids = list(dict.fromkeys(uid for uid in user_ids if isinstance(uid, int)))
    if not unique_ids:
        return {}
    placeholders = ",".join("?" * len(unique_ids))
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f'''
        SELECT user_id, username, first_name
        FROM users
        WHERE user_id IN ({placeholders})
        ''',
        unique_ids,
    )
    rows = cursor.fetchall()
    conn.close()
    return {
        row[0]: {
            "user_id": row[0],
            "username": row[1],
            "first_name": row[2],
        }
        for row in rows
    }


def get_user_challenge_statuses(user_id: int) -> dict[str, str]:
    """Статусы челленджей пользователя."""
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


def get_user_review_statuses(user_id: int) -> dict[str, str]:
    """Вернуть статусы модерации челленджей пользователя."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT challenge_id, COALESCE(review_status, 'pending')
        FROM user_challenges
        WHERE user_id = ?
        ''',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return {challenge_id: status for challenge_id, status in rows}


def accept_challenge(user_id: int, challenge_id: str) -> bool:
    """Записать факт принятия челленджа пользователем."""
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
    accepted_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if existing:
        if existing[0] == 'submitted':
            conn.close()
            return False
        cursor.execute(
            '''
            UPDATE user_challenges
            SET status = 'accepted',
                accepted_at = ?,
                submitted_at = NULL,
                photo_file_id = NULL,
                caption = NULL,
                review_status = 'pending',
                review_comment = NULL,
                reviewed_at = NULL,
                attachment_type = NULL,
                attachment_name = NULL,
                points_awarded = NULL
            WHERE user_id = ? AND challenge_id = ?
            ''',
            (accepted_at, user_id, challenge_id)
        )
    else:
        cursor.execute(
            '''
            INSERT INTO user_challenges (
                user_id, challenge_id, status, accepted_at, review_status,
                attachment_type, attachment_name, points_awarded
            )
            VALUES (?, ?, 'accepted', ?, 'pending', NULL, NULL, NULL)
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
    file_id: str,
    caption: str | None = None,
    attachment_type: str = 'photo',
    attachment_name: str | None = None
) -> bool:
    """Пометить челлендж как отправленный на проверку."""
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
            caption = ?,
            review_status = 'pending',
            review_comment = NULL,
            reviewed_at = NULL,
            attachment_type = ?,
            attachment_name = ?,
            points_awarded = NULL
        WHERE user_id = ? AND challenge_id = ?
        ''',
        (submitted_at, file_id, caption, attachment_type, attachment_name, user_id, challenge_id)
    )
    conn.commit()
    conn.close()
    return True


def get_user_challenges_by_status(
    user_id: int,
    statuses: Sequence[str]
) -> list[tuple]:
    """Вернуть список челленджей пользователя с указанными статусами."""
    if not statuses:
        return []

    placeholders = ",".join("?" * len(statuses))
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f'''
        SELECT challenge_id, status, submitted_at, photo_file_id, caption,
               review_status, review_comment, reviewed_at,
               attachment_type, attachment_name
        FROM user_challenges
        WHERE user_id = ? AND status IN ({placeholders})
        ORDER BY accepted_at ASC
        ''',
        (user_id, *statuses)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_submitted_challenges(user_id: int, only_pending: bool = True) -> list[tuple]:
    """Вернуть отправленные отчёты пользователя."""
    conn = _get_connection()
    cursor = conn.cursor()
    query = '''
        SELECT challenge_id, status, submitted_at, photo_file_id, caption,
               review_status, review_comment, reviewed_at,
               attachment_type, attachment_name
        FROM user_challenges
        WHERE user_id = ? AND status = 'submitted'
    '''
    params: list = [user_id]
    if only_pending:
        query += " AND (review_status IS NULL OR review_status = 'pending')"
    query += " ORDER BY submitted_at ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_reviewed_challenges(user_id: int) -> list[tuple]:
    """Вернуть отчёты пользователя, где есть решение модератора."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT challenge_id, status, submitted_at, photo_file_id, caption,
               review_status, review_comment, reviewed_at,
               attachment_type, attachment_name
        FROM user_challenges
        WHERE user_id = ?
          AND status = 'submitted'
          AND review_status IN ('approved', 'rejected')
        ORDER BY reviewed_at DESC
        ''',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_accepted_challenges(user_id: int) -> list[str]:
    """Вернуть принятые (но не сданные) челленджи."""
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
    """Сбросить состояние (используется при отклонении)."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        UPDATE user_challenges
        SET status = 'accepted',
            submitted_at = NULL,
            photo_file_id = NULL,
            caption = NULL,
            review_status = 'pending',
            review_comment = NULL,
            reviewed_at = NULL,
            attachment_type = NULL,
            attachment_name = NULL
        WHERE user_id = ? AND challenge_id = ? AND status != 'submitted'
        ''',
        (user_id, challenge_id)
    )
    conn.commit()
    conn.close()


def _decode_custom_id(challenge_id: str) -> int | None:
    if not challenge_id.startswith("custom_"):
        return None
    try:
        return int(challenge_id.split("_", 1)[1])
    except ValueError:
        return None


def fetch_custom_challenges(active_only: bool = True) -> list[dict]:
    """Получить список кастомных челленджей."""
    conn = _get_connection()
    cursor = conn.cursor()
    query = '''
        SELECT id, title, description, points, co2, active
        FROM custom_challenges
    '''
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id ASC"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    result: list[dict] = []
    for row in rows:
        challenge_id = f"custom_{row[0]}"
        result.append(
            {
                "challenge_id": challenge_id,
                "title": row[1],
                "description": row[2],
                "points": row[3],
                "co2": row[4],
                "active": bool(row[5]),
            }
        )
    return result


def get_custom_challenge(challenge_id: str) -> dict | None:
    """Получить информацию о кастомном челлендже."""
    internal_id = _decode_custom_id(challenge_id)
    if internal_id is None:
        return None
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, points, co2, active
        FROM custom_challenges
        WHERE id = ?
        ''',
        (internal_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "challenge_id": f"custom_{row[0]}",
        "title": row[1],
        "description": row[2],
        "points": row[3],
        "co2": row[4],
        "active": bool(row[5]),
    }


def create_custom_challenge(
    title: str,
    description: str,
    points: int,
    co2: str
) -> str:
    """Создать новый кастомный челлендж и вернуть его идентификатор."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO custom_challenges (title, description, points, co2, active)
        VALUES (?, ?, ?, ?, 1)
        ''',
        (title, description, points, co2)
    )
    challenge_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return f"custom_{challenge_id}"


def set_custom_challenge_active(challenge_id: str, active: bool) -> bool:
    """Обновить флаг активности кастомного челленджа."""
    internal_id = _decode_custom_id(challenge_id)
    if internal_id is None:
        return False
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        UPDATE custom_challenges
        SET active = ?
        WHERE id = ?
        ''',
        (1 if active else 0, internal_id)
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_custom_challenge(challenge_id: str) -> bool:
    """Полностью удалить кастомный челлендж."""
    internal_id = _decode_custom_id(challenge_id)
    if internal_id is None:
        return False
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        DELETE FROM custom_challenges
        WHERE id = ?
        ''',
        (internal_id,)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def log_admin_action(admin_id: int, action: str, details: str | None = None):
    """Сохранить действие администратора."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO admin_logs (admin_id, action, details, created_at)
        VALUES (?, ?, ?, ?)
        ''',
        (admin_id, action, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()


def get_admin_logs(limit: int | None = 50) -> list[dict]:
    """Получить последние действия админов."""
    conn = _get_connection()
    cursor = conn.cursor()
    query = '''
        SELECT id, admin_id, action, details, created_at
        FROM admin_logs
        ORDER BY created_at DESC
    '''
    params: tuple = ()
    if limit is not None:
        query += " LIMIT ?"
        params = (limit,)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "admin_id": row[1],
            "action": row[2],
            "details": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]


def get_pending_reports() -> list[dict]:
    """Вернуть отчёты, которые ждут проверки."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT uc.user_id,
               u.username,
               u.first_name,
               uc.challenge_id,
               uc.submitted_at,
               uc.photo_file_id,
               uc.caption,
               uc.attachment_type,
               uc.attachment_name
        FROM user_challenges uc
        LEFT JOIN users u ON u.user_id = uc.user_id
        WHERE uc.status = 'submitted'
          AND (uc.review_status IS NULL OR uc.review_status = 'pending')
        ORDER BY uc.submitted_at ASC
        '''
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "user_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "challenge_id": row[3],
            "submitted_at": row[4],
            "photo_file_id": row[5],
            "caption": row[6],
            "attachment_type": row[7] or 'photo',
            "attachment_name": row[8],
        }
        for row in rows
    ]


def update_report_review(
    user_id: int,
    challenge_id: str,
    review_status: str,
    review_comment: str | None = None,
    awarded_points: int | None = None
) -> bool:
    """Обновить статус проверки отчёта."""
    conn = _get_connection()
    cursor = conn.cursor()
    reviewed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    points_value = awarded_points if review_status == 'approved' else None
    cursor.execute(
        '''
        UPDATE user_challenges
        SET review_status = ?,
            review_comment = ?,
            reviewed_at = ?,
            points_awarded = ?
        WHERE user_id = ? AND challenge_id = ? AND status = 'submitted'
        ''',
        (
            review_status,
            review_comment,
            reviewed_at,
            points_value,
            user_id,
            challenge_id,
        )
    )
    updated = cursor.rowcount > 0
    if updated and review_status == 'rejected':
        cursor.execute(
            '''
            UPDATE user_challenges
            SET status = NULL,
                accepted_at = NULL,
                submitted_at = NULL,
                photo_file_id = NULL,
                caption = NULL,
                attachment_type = NULL,
                attachment_name = NULL,
                points_awarded = NULL
            WHERE user_id = ? AND challenge_id = ?
            ''',
            (user_id, challenge_id)
        )
    conn.commit()
    conn.close()
    return updated


def get_user_review_summary(user_id: int) -> dict[str, int]:
    """Сводка по статусам проверок пользователя."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT status, COALESCE(review_status, 'pending')
        FROM user_challenges
        WHERE user_id = ?
        ''',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    summary: dict[str, int] = {}
    for status, review_status in rows:
        if review_status in (None, 'pending'):
            if status == 'submitted':
                summary['pending'] = summary.get('pending', 0) + 1
        elif review_status in ('approved', 'rejected'):
            summary[review_status] = summary.get(review_status, 0) + 1
    return summary


def get_user_awarded_points(user_id: int) -> list[tuple[str, int | None, str | None]]:
    """Вернуть список одобренных отчётов с начисленными баллами."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT challenge_id, points_awarded, reviewed_at
        FROM user_challenges
        WHERE user_id = ? AND review_status = 'approved'
        ''',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_user_challenge(user_id: int, challenge_id: str) -> tuple | None:
    """Получить запись челленджа конкретного пользователя."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT user_id, challenge_id, status, accepted_at, submitted_at,
               photo_file_id, caption, review_status, review_comment, reviewed_at
        FROM user_challenges
        WHERE user_id = ? AND challenge_id = ?
        ''',
        (user_id, challenge_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row
