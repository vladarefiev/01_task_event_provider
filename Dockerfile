FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY run.sh ./
RUN chmod +x run.sh
RUN uv sync --no-dev

ENV PYTHONPATH=/app/src
ENV PORT=8000

EXPOSE 8000

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

CMD ["./run.sh"]
