#!/usr/bin/env bash
# Render build script — runs on every deploy
set -e  # exit immediately if any command fails

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Running database migrations..."
python manage.py migrate

echo "==> Build complete!"
