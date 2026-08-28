# AdvokatBot

Телеграм-бот для адвоката: клиент оставляет обращение (имя, телефон, суть), бот публикует его в канал
и позволяет админам ответить клиенту прямо из бота.

Стек: aiogram 3, PostgreSQL (SQLAlchemy + Alembic), Redis (FSM), pydantic-settings, Docker.

## Возможности

**Клиент**
- Выбор языка при первом `/start`: русский / узбекский (меняется кнопкой «🌐 Язык»).
- Анкета: Ф.И.О. → телефон (кнопкой «Отправить номер» или вручную) → описание ситуации.
- Обращение уходит в канал в едином формате, клиент получает номер обращения.
- «📂 Мои обращения» — статус и ответ адвоката.
- `/cancel` — отмена анкеты.

**Админка (в боте, `/admin` или кнопка в меню)**
- 📥 Новые обращения / 📋 Все обращения — карточка с контактами и текстом, кнопка «✉️ Ответить».
  Ответ приходит клиенту в бот на его языке, обращение помечается как отвеченное.
- 👥 Пользователи — список с языком и правами.
- 🛡 Админы (только суперадмин) — назначить админа по Telegram ID или @username, снять права.

Суперадмин задаётся в `.env` (`APP_CONFIG__BOT__SUPERADMIN_ID`), остальные админы хранятся в БД.
Интерфейс админки — на русском.

## Запуск

1. Зависимости:
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```

2. Конфиг — скопировать `.env-template` в `.env` и заполнить:
   ```
   APP_CONFIG__BOT__TOKEN=            # токен от @BotFather
   APP_CONFIG__BOT__CHANNEL_ID=       # ID канала, например -1001234567890
   APP_CONFIG__BOT__SUPERADMIN_ID=    # ваш Telegram ID (@userinfobot)
   ```
   Бота нужно добавить в канал администратором с правом публикации.

3. Postgres и Redis:
   ```bash
   docker compose --profile prod up -d pg redis
   ```

4. Миграции и запуск:
   ```bash
   .venv/bin/alembic upgrade head
   .venv/bin/python main.py
   ```

Всё в докере (бот + БД + Redis): `docker compose --profile prod up -d`.

## Разработка

```bash
.venv/bin/ruff check . && .venv/bin/ruff format .
.venv/bin/mypy .
docker compose --profile test up -d && .venv/bin/pytest
```

## Структура

```
main.py                 точка входа, роутеры и middleware
src/config.py           настройки из .env
src/handlers/user.py    язык, меню, анкета, «мои обращения»
src/handlers/admin.py   админ-панель
src/keyboards.py        клавиатуры
src/states.py           FSM-состояния
src/filters.py          IsAdmin
src/core/models/        UserOrm, RequestOrm
src/repository/         доступ к БД
texts/ru.json, uz.json  все тексты клиентской части
migrations/             Alembic
```

Тексты клиента правятся только в `texts/*.json` — код трогать не нужно.
