.PHONY: run dev lint

run:
	PYTHONPATH=src uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	PYTHONPATH=src uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

lint:
	uv run ruff check src
	uv run ruff format --check src

fix:
	uv run ruff check src --fix
	uv run ruff format src

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-logs:
	docker compose logs -f app
