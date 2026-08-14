#!/bin/bash
set -e

APP_DIR="/opt/flexyride_backend"
VENV_DIR="$APP_DIR/venv"
APP_NAME="flexyride_backend"

echo "========================================="
echo "Starting CI/CD Production Deployment"
echo "========================================="

cd $APP_DIR

echo "Pulling latest code..."
git fetch origin
git reset --hard origin/main
git pull origin main

echo "Activating virtual environment..."
source $VENV_DIR/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Restarting services..."
supervisorctl restart ${APP_NAME}_replicas:*
supervisorctl restart ${APP_NAME}_celery_high
supervisorctl restart ${APP_NAME}_celery_default
supervisorctl restart ${APP_NAME}_celery_beat

echo "========================================="
echo "✓ Production deployment completed successfully!"
echo "========================================="
