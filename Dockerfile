FROM python:3.11-slim

# Install system dependencies (GDAL and PostGIS client tools)
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure migrations and runserver
CMD python manage.py migrate && python manage.py runserver 0.0.0.0:8000
