# Events Aggregator

Сервис-агрегатор для Events Provider API с поддержкой Transactional Outbox, интеграцией с Capashino и идемпотентностью.

## Требования

- Python 3.9+
- PostgreSQL
- uv (менеджер пакетов)

## Локальный запуск

1. Создайте `.env` на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```
   Укажите `EVENTS_PROVIDER_API_KEY` и `CAPASHINO_API_KEY` из профиля LMS.

2. Запустите PostgreSQL (через Docker или локально).

3. Установите зависимости и запустите:
   ```bash
   uv sync
   uv run uvicorn app.main:app --reload
   ```

## Запуск через Docker Compose

```bash
export EVENTS_PROVIDER_API_KEY=your_api_key
export CAPASHINO_API_KEY=your_api_key
docker compose up --build
```

API будет доступен на http://localhost:8000

## API Endpoints

- `GET /api/health` - health check
- `POST /api/testing/clear-db` - очистка всех данных БД (только при `ENABLE_TEST_API=true`)
- `POST /api/sync/trigger` - ручной запуск синхронизации
- `GET /api/events` - список событий (date_from, page, page_size)
- `GET /api/events/{event_id}` - детали события
- `GET /api/events/{event_id}/seats` - свободные места
- `POST /api/tickets` - регистрация на событие (поддержка идемпотентности)
- `DELETE /api/tickets/{ticket_id}` - отмена регистрации

## Часть 2: Новая функциональность

### Transactional Outbox

При покупке билета запись о событии «ticket_purchased» сохраняется в таблицу `outbox` в той же транзакции, что и билет. Фоновый воркер (корутина в lifespan FastAPI) периодически читает неотправленные записи и отправляет уведомления в Capashino. При ошибке запись остаётся в статусе «ожидает отправки» и обрабатывается на следующих итерациях (до `OUTBOX_MAX_ATTEMPTS` попыток).

### Интеграция с Capashino

Воркер outbox при обработке записи вызывает `POST /api/notifications` Capashino с:
- `message` — текст о регистрации
- `reference_id` — ticket_id
- `idempotency_key` — для защиты от дубликатов при повторной обработке

### Идемпотентность POST /api/tickets

Клиент может передать `idempotency_key` в теле запроса:

```json
{
  "event_id": "...",
  "first_name": "...",
  "last_name": "...",
  "email": "...",
  "seat": "...",
  "idempotency_key": "optional-unique-key"
}
```

**Поведение:**
- **С ключом, первый раз:** обычная регистрация, ответ 201 с `ticket_id`. Результат сохраняется.
- **С тем же ключом и данными:** возвращает 201 с тем же `ticket_id`, повторная регистрация не происходит.
- **С тем же ключом, но другими данными:** возвращает 409 Conflict.
- **Без ключа:** каждый запрос обрабатывается как новый (поведение части 1).

## Конфигурация

| Переменная | Описание | По умолчанию |
|---|---|---|
| `POSTGRES_CONNECTION_STRING` | Строка подключения к PostgreSQL | `postgresql://...localhost` |
| `EVENTS_PROVIDER_URL` | URL Events Provider API | `http://events-provider.dev-1.python-labs.ru` |
| `EVENTS_PROVIDER_API_KEY` | API-ключ Events Provider | — |
| `CAPASHINO_URL` | URL Capashino Notification Service | `https://capashino.dev-1.python-labs.ru` |
| `CAPASHINO_API_KEY` | API-ключ Capashino | — |
| `OUTBOX_POLL_INTERVAL` | Интервал опроса outbox (сек) | `5` |
| `OUTBOX_MAX_ATTEMPTS` | Максимум попыток отправки | `10` |
| `ENABLE_TEST_API` | Разрешить тестовые endpoint'ы | `false` |
| `HOST` | Хост сервера | `0.0.0.0` |
| `PORT` | Порт сервера | `8000` |
