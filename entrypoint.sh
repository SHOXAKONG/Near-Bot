#!/bin/bash
set -e

echo "🔃 Waiting for PostgreSQL to be available..."
python << END
import time
import socket

s = socket.socket()
while True:
    try:
        s.connect(("db", 5432))
        s.close()
        break
    except socket.error:
        print("⏳ PostgreSQL is unavailable - sleeping")
        time.sleep(2)
END

echo "Running Migrations"
python manage.py migrate

echo "Checking for superuser..."
python manage.py shell <<EOF
from decouple import config
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

User = get_user_model()

email = config('DJANGO_SUPERUSER_EMAIL', default='admin@info.com')

try:
    password = config('DJANGO_SUPERUSER_PASSWORD')
except ImproperlyConfigured:
    password = None

if not User.objects.filter(username=username).exists():
    if not password:
        print("DJANGO_SUPERUSER_PASSWORD not found in environment or .env file. Cannot create superuser.")
        exit(1)

    print(f"Creating superuser for username '{username}'")
    User.objects.create_superuser(username=username, password=password)
    print("Superuser created successfully.")
else:
    print(f"Superuser with email '{username}' already exists. Skipping.")
EOF

echo "Collecting static files"
python manage.py collectstatic --noinput

echo "Start Gunicorn"
exec gunicorn src.core.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 3
