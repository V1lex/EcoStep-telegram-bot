import os

from dotenv import load_dotenv


def _parse_admin_ids(raw: str) -> set[int]:
    """Разобрать список ID админов из строки."""
    admin_ids: set[int] = set()
    for chunk in raw.split(","):
        value = chunk.strip()
        if not value:
            continue
        try:
            admin_ids.add(int(value))
        except ValueError:
            continue
    return admin_ids


def _parse_admin_credentials(raw: str) -> dict[int, str]:
    """Разобрать список вида 'id:password,id:password'."""
    credentials: dict[int, str] = {}
    for chunk in raw.split(","):
        pair = chunk.strip()
        if not pair:
            continue
        if ":" not in pair:
            continue
        admin_id_part, password = pair.split(":", 1)
        admin_id_part = admin_id_part.strip()
        password = password.strip()
        if not admin_id_part or not password:
            continue
        try:
            admin_id = int(admin_id_part)
        except ValueError:
            continue
        credentials[admin_id] = password
    return credentials


load_dotenv()

ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
ADMIN_WEBAPP_URL = os.getenv("ADMIN_WEBAPP_URL", "").strip()
ADMIN_PANEL_PASSWORD = os.getenv("ADMIN_PANEL_PASSWORD", "").strip()
ADMIN_CREDENTIALS = _parse_admin_credentials(os.getenv("ADMIN_CREDENTIALS", ""))

if ADMIN_CREDENTIALS:
    ADMIN_IDS.update(ADMIN_CREDENTIALS.keys())


def is_admin(user_id: int) -> bool:
    """Проверить, относится ли пользователь к списку админов."""
    return user_id in ADMIN_IDS


def has_admin_panel() -> bool:
    """Есть ли ссылка на админскую mini app."""
    return bool(ADMIN_WEBAPP_URL)


def validate_admin_password(admin_id: int, password: str) -> bool:
    """Проверить пароль для конкретного администратора."""
    if ADMIN_CREDENTIALS:
        expected = ADMIN_CREDENTIALS.get(admin_id)
        if expected is None:
            return False
        return password == expected
    if not ADMIN_PANEL_PASSWORD:
        return False
    return password == ADMIN_PANEL_PASSWORD
