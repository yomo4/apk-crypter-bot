# APK Crypter Bot

Телеграм бот для шифрования APK файлов.

## Что делает

1. Принимает APK файл
2. Шифрует его через AES-256-GCM
3. Создает stub APK загрузчик
4. Stub расшифровывает и устанавливает оригинальный APK при запуске

## Установка

1. Создай `.env` файл:
```bash
cp .env.example .env
```

2. Добавь токен бота в `.env`:
```
BOT_TOKEN=твой_токен_от_BotFather
```

3. Установи зависимости:
```bash
pip install -r requirements.txt
```

4. Запусти бота:
```bash
python main.py
```

## Деплой на Railway

1. Создай проект на Railway
2. Подключи GitHub репозиторий
3. Добавь переменную `BOT_TOKEN` в настройках
4. Railway автоматически запустит бота

## Структура

- `main.py` - точка входа
- `config.py` - конфигурация
- `handlers/` - обработчики сообщений
- `services/apk_crypter.py` - криптер APK файлов
