# Events Aggregator

Сервис-агрегатор для Events Provider API.

## Требования

- Python 3.9+
- PostgreSQL
- uv (менеджер пакетов)

## Локальный запуск

1. Создайте `.env` на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```
   Укажите `EVENTS_PROVIDER_API_KEY` из профиля LMS.

2. Запустите PostgreSQL (через Docker или локально).

3. Установите зависимости и запустите:
   ```bash
   uv sync
   uv run uvicorn app.main:app --reload
   ```

## Запуск через Docker Compose

```bash
export EVENTS_PROVIDER_API_KEY=your_api_key
docker compose up --build
```

API будет доступен на http://localhost:8000

## API Endpoints

- `GET /api/health` - health check
- `POST /api/sync/trigger` - ручной запуск синхронизации
- `GET /api/events` - список событий (date_from, page, page_size)
- `GET /api/events/{event_id}` - детали события
- `GET /api/events/{event_id}/seats` - свободные места
- `POST /api/tickets` - регистрация на событие
- `DELETE /api/tickets/{ticket_id}` - отмена регистрации
