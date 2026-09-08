FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /projet
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
RUN useradd --create-home atelier && mkdir /donnees && chown atelier:atelier /donnees
USER atelier
EXPOSE 8000
CMD [".venv/bin/uvicorn", "application.principal:app", "--host", "0.0.0.0", "--port", "8000"]
