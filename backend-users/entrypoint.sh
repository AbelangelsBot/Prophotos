#!/bin/bash
set -e

echo "Running migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Setup cron job for cleanup (every 6 hours)
echo "Setting up cleanup cron job..."
echo "0 */6 * * * cd /app && python manage.py cleanup_unverified_users --cleanup-attempts >> /var/log/cleanup.log 2>&1" | crontab -

# Start cron daemon in background
cron

echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8000
