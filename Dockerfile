FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

RUN useradd --system --no-create-home --shell /usr/sbin/nologin app

COPY --chown=app:app app/ ./app/
COPY --chown=app:app public/ ./public/

USER app

CMD ["python", "-m", "app.main"]
