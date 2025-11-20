# EcoStep Telegram Bot

EcoStep помогает студентам МАИ и молодёжи формировать экологичные привычки через Telegram. Бот предоставляет список челленджей, собирает отчёты, ведёт рейтинг друзей и даёт администраторам инструменты модерации через mini app на базе FastAPI.

## Возможности
- **Библиотека челленджей**: предустановленные сценарии и кастомные задания из `settings/challenges.py` и админ-панели.
- **Отчёты с медиа**: пользователи отправляют фото/видео, бот фиксирует статус в SQLite (`database.py`) и передаёт задания на проверку.
- **Рейтинг друзей**: система друзей и лидербордов хранится в таблицах `user_friends` и `friend_requests`.
- **Аналитика и напоминания**: отдельные роутеры в `bot_routes/` отвечают за статистику, уведомления и взаимодействие с пользователем.
- **Админ-инструменты**: FastAPI-приложение в `admin_panel/backend` позволяет управлять челленджами, рассылками и отчётами.

## Структура репозитория
| Путь | Содержание |
| --- | --- |
| `run.py`, `bot_core.py` | Точка входа бота и инициализация `aiogram` 3.x |
| `bot_routes/` | Роутеры: приветствие (`start.py`), аналитика (`analytics.py`), работа с друзьями и челленджами |
| `database.py` | Все операции с SQLite, включая регистрацию пользователей, отчёты и логи админов |
| `settings/` | Настройки челленджей, администраторов и других констант |
| `bot_keyboards/` | Reply/inline-клавиатуры, включая mini app для админов |
| `admin_panel/` | FastAPI backend (`backend/`) и статика mini app (`index.html`, `app.js`) |
| `assets/` | Баннера и статические изображения для сообщений |
| `support_tools/` | Вспомогательные функции, команды и утилиты |
| `tests/` | Pytest-тесты для БД и бизнес-логики |
| `roadmap.md` | Планы и приоритеты команды |

## Быстрый старт
### Предварительные требования
- Python 3.11+ (проект разрабатывается на 3.12)
- Установленный `pip`
- Токен Telegram-бота (BotFather)

### Установка
```bash
git clone https://github.com/v1lex/EcoStep-telegram-bot.git
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
После запуска бот создаст `ecostep.db`, настройит команды (см. `support_tools/bot_commands.py`) и начнёт polling. Пользователи регистрируются автоматически при первом сообщении благодаря middleware в `run.py`.

### Запуск админской mini app
Backend использует FastAPI и запускается как фабрика приложения:
```bash
uvicorn admin_panel.backend.main:get_app --factory --reload --port 8000
```
Статический интерфейс (`admin_panel/index.html`) можно открыть из любой статики или раздать через тот же сервер, если потребуется.

## Тестирование
В проекте есть pytest-тесты для БД (`tests/test_database.py`). После установки зависимостей запускайте тесты из корня проекта с активированным виртуальным окружением:
```bash
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pytest
```
Тесты автоматически создают отдельную SQLite-базу (`test_ecostep.db`), рабочие данные не трогаются.

## Дополнительные материалы
- `roadmap.md`: планы и приоритеты команды.
