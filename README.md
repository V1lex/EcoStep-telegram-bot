# EcoStep Telegram Bot

EcoStep помогает студентам МАИ формировать экологичные привычки через Telegram. Бот предоставляет список челленджей, собирает отчёты, ведёт рейтинг друзей и даёт администраторам инструменты модерации через mini app на базе FastAPI.

## Возможности
- **Библиотека челленджей** — предустановленные сценарии и кастомные задания из `config/challenges.py` и админ-панели.
- **Отчёты с медиа** — пользователи отправляют фото/видео, бот фиксирует статус в SQLite (`database.py`) и передаёт задания на проверку.
- **Рейтинг друзей** — система дружбы и лидербордов хранится в таблицах `user_friends` и `friend_requests`.
- **Аналитика и напоминания** — отдельные роутеры в `handlers/` отвечают за статистику, уведомления и взаимодействие с пользователем.
- **Админ-инструменты** — FastAPI-приложение в `admin_webapp/backend` позволяет управлять челленджами, рассылками и отчётами.

## Структура репозитория
| Путь | Содержание |
| --- | --- |
| `run.py`, `create_bot.py` | Точка входа бота и инициализация `aiogram` 3.x |
| `handlers/` | Роутеры: приветствие (`start.py`), аналитика (`analytics.py`), работа с друзьями и челленджами |
| `database.py` | Все операции с SQLite, включая регистрацию пользователей, отчёты и логи админов |
| `config/` | Настройки челленджей, администраторов и других констант |
| `keyboards/` | Reply/inline-клавиатуры, включая mini app для админов |
| `admin_webapp/` | FastAPI backend (`backend/`) и статика mini app (`index.html`, `app.js`) |
| `tasks/` | Заготовки фоновых задач и планировщика |
| `tests/` | Pytest-спеки для БД и бизнес-логики |
| `docs/`, `structure_explanation.md`, `roadmap.md` | Дополнительная документация и планы |

## Быстрый старт
### Предварительные требования
- Python 3.11+ (проект разрабатывается на 3.12)
- Установленный `pip`
- Токен Telegram-бота (BotFather)

### Установка
```bash
git clone https://github.com/<your-org>/EcoStep-telegram-bot.git
cd EcoStep-telegram-bot
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Создайте файл `.env` рядом с `run.py` и добавьте значения:
```ini
BOT_TOKEN=123456:ABCDEF
# один из способов указать админов:
ADMIN_IDS=11111111,22222222
ADMIN_PANEL_PASSWORD=supersecret
ADMIN_WEBAPP_URL=https://your-mini-app-host
# или в формате id:пароль
ADMIN_CREDENTIALS=11111111:supersecret,22222222:anotherpass
```

### Запуск бота
```bash
python run.py
```
После запуска бот создаст `ecostep.db`, настройит команды (см. `utils/bot_commands.py`) и начнёт polling. Пользователи регистрируются автоматически при первом сообщении благодаря middleware в `run.py`.

### Запуск админской mini app
Backend использует FastAPI и запускается как фабрика приложения:
```bash
uvicorn admin_webapp.backend.main:get_app --factory --reload --port 8000
```
Статический интерфейс (`admin_webapp/index.html`) можно открыть из любой статики или раздать через тот же сервер, если потребуется.

## Тестирование
В проекте используются pytest-тесты для БД (`tests/test_database.py`) и заготовки под другие сценарии.
```bash
pip install pytest
pytest
```
Тесты автоматически создают отдельную SQLite-базу (`test_ecostep.db`), поэтому рабочие данные не затрагиваются.

## Дополнительные материалы
- `structure_explanation.md` — подробная карта модулей.
- `docs/` — техническая документация и спецификации (например, `docs/api_spec.md`).
- `roadmap.md` — планы и приоритеты команды.

Если вы хотите внести изменения в код, обязательно загляните в `README-CONTRIBUTORS.md` — там описаны гайдлайны для разработчиков.
