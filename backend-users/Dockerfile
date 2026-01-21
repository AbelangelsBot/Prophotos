FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev cron \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . /app

# Rendre le script executable
RUN chmod +x /app/entrypoint.sh

# Creer le fichier de log
RUN touch /var/log/cleanup.log

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

