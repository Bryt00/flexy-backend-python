#!/bin/bash
# FlexyRide Service Restart Script
# Centralized script to restart all application components, including multiples Redis instances.
# Usage: sudo bash restart_services.sh

set -e

# Configuration
APP_NAME="flexyride_backend"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "Restarting FlexyRide Services"
echo "========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo -e "${YELLOW}0. Ensuring Nginx WebSocket Support...${NC}"
CONF="/etc/nginx/sites-available/flexyride_backend"

if [ -f "$CONF" ]; then
    if ! grep -q "location /v1/" "$CONF"; then
        echo "   Applying WebSocket upgrade patch to $CONF..."
        python3 - <<'PYTHON'
import re, sys
conf_path = "/etc/nginx/sites-available/flexyride_backend"
with open(conf_path, "r") as f:
    content = f.read()

v1_block = """
    # Versioned API routes (mobile app traffic + websockets)
    location /v1/ {
        proxy_pass http://flexyride_backend_cluster;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        client_max_body_size 200M;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_redirect off;
    }
"""
if "location /callbacks/" in content:
    content = content.replace("    location /callbacks/", v1_block + "    location /callbacks/", 1)
else:
    content = content.replace(
        "    # Redirect everything else on the API subdomain to the main site\n    location / {",
        v1_block + "    # Redirect non-API paths on the API subdomain to the main site\n    location / {",
        1
    )
with open(conf_path, "w") as f:
    f.write(content)
PYTHON
        echo "   Patch applied. Nginx will be reloaded later."
    else
        echo "   ✓ Nginx already configured for /v1/"
    fi
fi

echo -e "${YELLOW}0.1 Updating Static Assets...${NC}"

# Collect static files (UI changes)
if [ -f "manage.py" ]; then
    echo "   Collecting static files..."
    # Attempt to find venv
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    python manage.py collectstatic --noinput
else
    echo "   Warning: manage.py not found, skipping static collection"
fi
echo -e "${GREEN}✓ Code and UI assets updated${NC}"

echo -e "${YELLOW}1. Restarting Redis Instances...${NC}"
# Primary Redis
systemctl restart redis-server || echo "Primary Redis not found"

# Secondary Redis Instances (redis2, redis3, etc.)
for service in $(systemctl list-units --type=service --state=active | grep -oE "redis[0-9]+" | sort -u); do
    echo "   Restarting ${service}..."
    systemctl restart ${service}
done
echo -e "${GREEN}✓ Redis services restarted${NC}"

echo -e "${YELLOW}2. Restarting RabbitMQ Broker...${NC}"
systemctl restart rabbitmq-server || echo "RabbitMQ not found"
echo -e "${GREEN}✓ RabbitMQ restarted${NC}"

echo -e "${YELLOW}3. Restarting Application Replicas (Supervisor)...${NC}"
supervisorctl restart ${APP_NAME}_replicas:*
echo -e "${GREEN}✓ Application replicas restarted${NC}"

echo -e "${YELLOW}3. Restarting Celery Services...${NC}"
supervisorctl restart ${APP_NAME}_celery
supervisorctl restart ${APP_NAME}_celery_beat
echo -e "${GREEN}✓ Celery services restarted${NC}"

echo -e "${YELLOW}4. Restarting Nginx...${NC}"
systemctl restart nginx
echo -e "${GREEN}✓ Nginx restarted${NC}"

echo ""
echo "========================================="
echo -e "${GREEN}🎉 All services restarted successfully!${NC}"
echo "========================================="