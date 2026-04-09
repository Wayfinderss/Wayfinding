FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends osmium-tool curl \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --no-cache-dir uv \
    && uv sync --frozen

ENV PYTHONPATH=/app

EXPOSE 8000

COPY scripts/bootstrap_tiles.sh /bootstrap_tiles.sh

RUN chmod +x /bootstrap_tiles.sh

CMD ["/bootstrap_tiles.sh"]