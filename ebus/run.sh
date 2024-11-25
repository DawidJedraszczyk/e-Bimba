#!/bin/sh

echo "Waiting for postgres"

until pg_isready -h postgres -p 5432; do
  sleep 1
done

echo "Starting"

python manage.py migrate
exec python manage.py runserver 0.0.0.0:8000
