# Инструкция для разработчиков EcoStep Bot (локальный запуск)

## 1. Клонируй репозиторий
```
git clone git@github.com:yourname/ecostep-telegram-bot.git
cd ecostep-telegram-bot
```

## 2. Создай виртуальное окружение и активируй его

macOS / Linux:
```
python3.12 -m venv venv
source venv/bin/activate
```

Windows (PowerShell):
```
python3.12 -m venv venv
venv\Scripts\Activate.ps1
```

## 3. Установи зависимости
```
pip install -r requirements.txt
```

Проблема: pydantic-core (зависимость aiogram) еще не поддерживает Python 3.14
Используем: python 3.12
## 4. Создай свой .env

Скопируй шаблон:
```
# Если есть .env.example
cp .env.example .env

# Или создай вручную
echo "BOT_TOKEN=your_bot_token_here" > .env
echo "ADMINS=your_admin_id_here" >> .env
```

Открой файл .env и вставь токен из нашей беседы:
```
BOT_TOKEN=1234567890:AAEexampleToken
ADMINS=123456789
```

## 5. Запусти бота
```
python3 run.py
```

Если всё правильно — бот запустится, и в Telegram можно будет написать /start,
