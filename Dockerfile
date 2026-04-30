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

# Use Daphne as the production ASGI server
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "flexy_backend.asgi:application"]
