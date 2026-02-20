FROM python:3.12-slim as base

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv
RUN uv lock
RUN uv sync --no-dev

COPY src/ ./src/
COPY run.sh ./
RUN chmod +x run.sh

ENV PYTHONPATH=/app/src
ENV PORT=8000

EXPOSE 8000

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

CMD ["bash", "./run.sh"]
