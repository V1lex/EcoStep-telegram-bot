# EcoStep Telegram Bot

EcoStep — Telegram‑бот для экопривычек: пользователи берут челленджи, отправляют отчёты, видят прогресс и лидерборды; администраторы управляют заданиями и модерируют отчёты через веб‑интерфейс (мини‑приложение) на FastAPI.

## Основные возможности
- Челленджи: список, принятие, отправка отчётов (фото/текст), баллы и CO₂.
- Соц. функции: друзья, уведомления, лидерборд по друзьям.
- Админка: логин, CRUD челленджей (включая кастомные), модерация отчётов, рассылки, логи.
- Хранение: SQLite (по умолчанию файл `ecostep.db`, путь настраивается).

## Структура
| Часть | Описание |
| --- | --- |
| `run.py`, `bot_core.py` | Точка входа бота (Aiogram 3) |
| `bot_routes/` | Маршруты бота: старт, аналитика/челленджи, друзья, отчёты |
| `bot_keyboards/` | Reply/inline‑клавиатуры, ссылки на WebApp |
| `database.py` | Работа с SQLite, миграции и CRUD |
| `settings/` | Админы, челленджи (конфиг/кэш) |
| `admin_panel/backend/` | FastAPI backend админки (`main.py`, схемы) |
| `admin_panel/` | Фронт мини‑приложения (HTML/JS/CSS) |
| `assets/` | Баннеры и медиа |
| `support_tools/` | Команды бота, подсказки, утилиты |
| `tests/` | Pytest для базы |
| `roadmap.md` | План развития |

## Требования
- Python 3.11+ (работает и на 3.12)
- pip
- Токен Telegram‑бота (BotFather)

## Установка (локально или на чистом сервере)
```bash
git clone https://github.com/V1lex/EcoStep-telegram-bot.git
cd EcoStep-telegram-bot

python -m venv .venv
source .venv/bin/activate       # Windows: .\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Создай `.env` (можно скопировать из примера, если появится):
```env
BOT_TOKEN=123456:ABCDEF                  # токен бота
ADMIN_IDS=11111111,22222222             # список админов (ID)
# либо/и ADMIN_CREDENTIALS=id:password,id:password
ADMIN_PANEL_PASSWORD=supersecret        # общий пароль (если не используешь пары id:pass)
ADMIN_WEBAPP_URL=https://your-mini-app  # URL мини‑приложения
# опционально путь к БД:
ECOSTEP_DB_PATH=/var/lib/ecostep/ecostep.db
```

## Быстрый запуск для проверки
Открой два терминала (оба в корне проекта, с активным venv):
- Бот: `python run.py`
- Админка: `uvicorn admin_panel.backend.main:get_app --factory --host 127.0.0.1 --port 8001`

Админ‑панель будет доступна на `http://127.0.0.1:8001` (WebApp можно открыть прямо в браузере для проверки).

## Деплой (пример: /opt/ecostep + systemd)
```bash
ssh ubuntu@your_server_ip
sudo mkdir -p /opt/ecostep && sudo chown ubuntu:ubuntu /opt/ecostep
cd /opt/ecostep
git clone https://github.com/V1lex/EcoStep-telegram-bot.git .

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env  # если файла нет — создай .env по шаблону выше
nano .env             # заполни реальные BOT_TOKEN, ADMIN_IDS/ADMIN_CREDENTIALS, ADMIN_PANEL_PASSWORD, ADMIN_WEBAPP_URL, ECOSTEP_DB_PATH
```

### systemd unit‑файлы
`/etc/systemd/system/ecostep-bot.service`
```ini
[Unit]
Description=EcoStep Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/ecostep
EnvironmentFile=/opt/ecostep/.env
ExecStart=/opt/ecostep/venv/bin/python run.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/admin-webapp.service`
```ini
[Unit]
Description=EcoStep Admin WebApp (FastAPI)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/ecostep/admin_panel/backend
EnvironmentFile=/opt/ecostep/.env
ExecStart=/opt/ecostep/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск и автозапуск:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ecostep-bot admin-webapp
sudo systemctl start ecostep-bot admin-webapp
sudo systemctl status ecostep-bot admin-webapp
```

Логи:
```bash
journalctl -u ecostep-bot -n 50 --no-pager
journalctl -u admin-webapp -n 50 --no-pager
journalctl -u ecostep-bot -u admin-webapp -f   # realtime
```

## Nginx (по желанию, чтобы отдать админку по домену)
```nginx
server {
    listen 80;
    server_name ecostepadmin.ru;
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Активировать: `sudo ln -s /etc/nginx/sites-available/ecostep-admin /etc/nginx/sites-enabled/` → `sudo nginx -t` → `sudo systemctl restart nginx`. Для HTTPS добавь certbot.

## Тесты
```bash
source .venv/bin/activate
pytest
```

## Обновление версии
```bash
ssh ubuntu@your_server_ip
cd /opt/ecostep
git pull
source venv/bin/activate
pip install -r requirements.txt  # если менялся requirements.txt
sudo systemctl restart ecostep-bot admin-webapp
```
