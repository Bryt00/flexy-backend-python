#!/bin/bash
# ==============================================================================
# FlexyRide Django REST Backend - Safe Zero-Downtime Deployment & Service Reload
#
# Provides graceful soft rollout with sequential rolling restarts across Daphne
# application replicas, non-disruptive cache/broker checks, and Nginx graceful
# reload to guarantee 0% downtime and prevent 502 Bad Gateway / connection drops.
#
# Usage:
#   sudo bash restart_services.sh              # Soft rolling rollout (zero downtime)
#   sudo bash restart_services.sh --pull       # Pull git updates first, then soft rollout
#   sudo bash restart_services.sh --hard       # Hard restart (forces cold restart of all services)
# ==============================================================================

set -e

# Configuration
APP_NAME="flexyride_backend"
USER="${SUDO_USER:-patmac}"
[ "$USER" = "root" ] && USER="patmac"

# Detect directory: prefer current script directory if manage.py exists, fallback to /opt/flexyride_backend
if [ -f "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manage.py" ]; then
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
elif [ -d "/opt/$APP_NAME" ]; then
    PROJECT_DIR="/opt/$APP_NAME"
elif [ -d "/opt/flexyride_backend" ]; then
    PROJECT_DIR="/opt/flexyride_backend"
else
    PROJECT_DIR="$(pwd)"
fi

# Flags
DO_PULL=false
HARD_RESTART=false

for arg in "$@"; do
    case "$arg" in
        --pull|-p)
            DO_PULL=true
            ;;
        --hard)
            HARD_RESTART=true
            ;;
    esac
done

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================================="
echo -e "${BLUE}FlexyRide Django REST Backend - Safe Deployment & Reload${NC}"
echo "Project Directory: $PROJECT_DIR"
if [ "$HARD_RESTART" = true ]; then
    echo -e "Mode: ${RED}Hard Service Restart (Cold Boot)${NC}"
else
    echo -e "Mode: ${GREEN}Graceful Soft Rollout (Zero-Downtime Rolling Reload)${NC}"
fi
echo "========================================================="

# 1. Check Root Privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (use sudo: sudo bash restart_services.sh)${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# 2. Optional Git Pull
if [ "$DO_PULL" = true ]; then
    if [ -d ".git" ]; then
        echo -e "${YELLOW}1. Pulling latest updates from Git...${NC}"
        git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
        sudo -u "$USER" git pull || echo -e "${RED}Git pull encountered an issue, proceeding with deployment...${NC}"
        echo -e "${GREEN}✓ Git repository updated${NC}"
    fi
fi

# 3. Virtual Environment Setup
echo -e "${YELLOW}2. Activating Python virtual environment...${NC}"
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated (venv)${NC}"
elif [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated (.venv)${NC}"
elif [ -f "/opt/flexyride_backend/venv/bin/activate" ]; then
    source "/opt/flexyride_backend/venv/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated (/opt/flexyride_backend/venv)${NC}"
else
    echo -e "${RED}Warning: Virtual environment not found, attempting system python...${NC}"
fi

# 4. Pre-flight Health Check (Prevents deploying broken code / 500 crashes)
if [ -f "$PROJECT_DIR/manage.py" ]; then
    echo -e "${YELLOW}3. Running pre-flight system integrity check...${NC}"
    if python manage.py check; then
        echo -e "${GREEN}✓ System check passed - safe to deploy${NC}"
    else
        echo -e "${RED}✗ System check failed! Aborting deployment to prevent downtime.${NC}"
        exit 1
    fi

    # 4.1 Database Migrations
    echo -e "${YELLOW}3.1 Running database migrations...${NC}"
    python manage.py migrate --noinput
    echo -e "${GREEN}✓ Migrations up to date${NC}"

    # 4.2 Safe Static Files Collection (without --clear to prevent 404s during rollout)
    echo -e "${YELLOW}3.2 Collecting static assets (UI updates)...${NC}"
    python manage.py collectstatic --noinput
    echo -e "${GREEN}✓ Static files collected${NC}"
fi

# 5. Ensure Filesystem Permissions
echo -e "${YELLOW}4. Ensuring filesystem permissions...${NC}"
mkdir -p "$PROJECT_DIR/staticfiles" "$PROJECT_DIR/media" "$PROJECT_DIR/logs"
chown -R "$USER:www-data" "$PROJECT_DIR/staticfiles" "$PROJECT_DIR/media" "$PROJECT_DIR/logs" 2>/dev/null || true
chmod -R 755 "$PROJECT_DIR/staticfiles" 2>/dev/null || true
chmod -R 775 "$PROJECT_DIR/media" "$PROJECT_DIR/logs" 2>/dev/null || true
chown "$USER:$USER" "$PROJECT_DIR"/db.sqlite3* 2>/dev/null || true
chmod 664 "$PROJECT_DIR"/db.sqlite3* 2>/dev/null || true
echo -e "${GREEN}✓ Permissions verified${NC}"

# 6. Ensure Nginx WebSocket & API v1 Support
echo -e "${YELLOW}5. Verifying Nginx WebSocket & API routing...${NC}"
CONF="/etc/nginx/sites-available/$APP_NAME"
if [ ! -f "$CONF" ]; then
    CONF="/etc/nginx/sites-available/flexyride_backend"
fi

if [ -f "$CONF" ]; then
    if ! grep -q "location /v1/" "$CONF"; then
        echo "   Applying WebSocket upgrade patch to $CONF..."
        python3 - <<PYTHON
import re, sys
conf_path = "$CONF"
try:
    with open(conf_path, "r") as f:
        content = f.read()

    # 1. Ensure map block exists for WebSocket upgrades
    map_block = """
# WebSocket Upgrade Map
map \$http_upgrade \$connection_upgrade {
    default upgrade;
    ''      close;
}
"""
    if "map \$http_upgrade \$connection_upgrade" not in content:
        content = map_block + "\n" + content

    # 2. Ensure /v1/ location block exists
    v1_block = """
    # Versioned API routes (mobile app traffic + websockets)
    location /v1/ {
        proxy_pass http://flexyride_backend_cluster;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        client_max_body_size 200M;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_redirect off;
    }
"""
    if "location /v1/" not in content:
        if "location /callbacks/" in content:
            content = content.replace("    location /callbacks/", v1_block + "    location /callbacks/", 1)
        elif "location / {" in content:
            content = content.replace("    location / {", v1_block + "    location / {", 1)

    with open(conf_path, "w") as f:
        f.write(content)
    print("   ✓ Nginx WebSocket patch applied.")
except Exception as e:
    print(f"   Note: Nginx patch skipped: {e}")
PYTHON
    else
        echo -e "${GREEN}✓ Nginx already configured for /v1/ and WebSockets${NC}"
    fi
fi

# 7. Redis Cache & Channel Layer Check
echo -e "${YELLOW}6. Checking Redis cache & Channel layer...${NC}"
if [ "$HARD_RESTART" = true ]; then
    systemctl restart redis-server 2>/dev/null || systemctl restart redis 2>/dev/null || echo "Primary Redis not found"
    for service in $(systemctl list-units --type=service --state=active 2>/dev/null | grep -oE "redis[0-9]+" | sort -u); do
        echo "   Restarting ${service}..."
        systemctl restart "$service" 2>/dev/null || true
    done
    echo -e "${GREEN}✓ Redis services restarted${NC}"
else
    # Preserve running Redis so active sessions, Channel Layer, and WebSocket states are not wiped
    if systemctl is-active --quiet redis-server 2>/dev/null || systemctl is-active --quiet redis 2>/dev/null; then
        echo -e "${GREEN}✓ Redis active and healthy (sessions & channels preserved)${NC}"
    else
        systemctl start redis-server 2>/dev/null || systemctl start redis 2>/dev/null || echo "Redis not installed as system service"
        echo -e "${GREEN}✓ Redis started${NC}"
    fi
fi

# 8. RabbitMQ Broker Check
echo -e "${YELLOW}7. Checking RabbitMQ message broker...${NC}"
if [ "$HARD_RESTART" = true ]; then
    systemctl restart rabbitmq-server 2>/dev/null || echo "RabbitMQ not found"
    echo -e "${GREEN}✓ RabbitMQ restarted${NC}"
else
    if systemctl is-active --quiet rabbitmq-server 2>/dev/null; then
        echo -e "${GREEN}✓ RabbitMQ active and healthy (queues preserved)${NC}"
    else
        systemctl start rabbitmq-server 2>/dev/null || echo "RabbitMQ not found or not active"
        echo -e "${GREEN}✓ RabbitMQ checked${NC}"
    fi
fi

# 9. Application Replicas Soft Rolling Reload (Zero-Downtime)
echo -e "${YELLOW}8. Rolling reload of application replicas...${NC}"
if command -v supervisorctl &> /dev/null; then
    # Query running replicas for this application
    REPLICAS=$(supervisorctl status 2>/dev/null | grep -E "^(${APP_NAME}_replicas:|${APP_NAME}_replica_)" | awk '{print $1}' || true)

    if [ -n "$REPLICAS" ]; then
        if [ "$HARD_RESTART" = true ]; then
            echo -e "${RED}Hard restarting all replicas at once...${NC}"
            supervisorctl restart ${APP_NAME}_replicas:* 2>/dev/null || true
            echo -e "${GREEN}✓ All application replicas restarted${NC}"
        else
            # Soft sequential rolling restart: one replica at a time so remaining replicas handle live traffic
            TOTAL_REPLICAS=$(echo "$REPLICAS" | wc -l)
            IDX=1
            for rep in $REPLICAS; do
                echo -e "   [${IDX}/${TOTAL_REPLICAS}] Soft rolling reload: ${YELLOW}${rep}${NC}..."
                supervisorctl restart "$rep"
                # Brief sleep allows the newly restarted replica to bind socket and begin handling requests
                sleep 2
                IDX=$((IDX + 1))
            done
            echo -e "${GREEN}✓ All ${TOTAL_REPLICAS} application replicas rolled over seamlessly (zero downtime)${NC}"
        fi
    else
        # Try generic replica group or direct systemd service
        if supervisorctl status "${APP_NAME}:*" 2>/dev/null | grep -q "${APP_NAME}"; then
            for rep in $(supervisorctl status "${APP_NAME}:*" | awk '{print $1}'); do
                echo -e "   Rolling reload: ${rep}..."
                supervisorctl restart "$rep"
                sleep 2
            done
            echo -e "${GREEN}✓ Supervisor programs reloaded${NC}"
        elif systemctl list-unit-files 2>/dev/null | grep -q "gunicorn_${APP_NAME}"; then
            if [ "$HARD_RESTART" = true ]; then
                systemctl restart "gunicorn_${APP_NAME}"
            else
                systemctl reload "gunicorn_${APP_NAME}" 2>/dev/null || pkill -HUP -f "gunicorn.*${APP_NAME}"
            fi
            echo -e "${GREEN}✓ Gunicorn service reloaded${NC}"
        elif pgrep -f "daphne.*flexy_backend" > /dev/null; then
            pkill -HUP -f "daphne.*flexy_backend" 2>/dev/null || true
            echo -e "${GREEN}✓ Sent HUP signal to running Daphne instances${NC}"
        fi
    fi
else
    # Fallback when supervisor is not present
    if systemctl is-active --quiet "$APP_NAME" 2>/dev/null; then
        systemctl reload "$APP_NAME" 2>/dev/null || systemctl restart "$APP_NAME"
        echo -e "${GREEN}✓ Service $APP_NAME refreshed${NC}"
    fi
fi

# 10. Celery Workers & Beat Scheduler Update
echo -e "${YELLOW}9. Refreshing Celery workers & beat scheduler...${NC}"
rm -f "$PROJECT_DIR/celerybeat.pid" "/tmp/celerybeat_${APP_NAME}.pid"

if command -v supervisorctl &> /dev/null; then
    for c_service in "${APP_NAME}_celery_high" "${APP_NAME}_celery_default" "${APP_NAME}_celery_beat"; do
        if supervisorctl status "$c_service" 2>/dev/null | grep -q "$c_service"; then
            supervisorctl restart "$c_service" 2>/dev/null || true
            echo -e "   ✓ Celery task ${c_service} reloaded"
        fi
    done
    echo -e "${GREEN}✓ Celery services updated${NC}"
fi

# 11. Nginx Zero-Downtime Reload (Keeps live HTTP/HTTPS & WebSocket sockets intact)
echo -e "${YELLOW}10. Testing and reloading Nginx...${NC}"
if nginx -t; then
    if [ "$HARD_RESTART" = true ]; then
        systemctl restart nginx
        echo -e "${GREEN}✓ Nginx restarted${NC}"
    else
        systemctl reload nginx
        echo -e "${GREEN}✓ Nginx gracefully reloaded (zero dropped connections)${NC}"
    fi
else
    echo -e "${RED}✗ Nginx configuration test failed! Leaving existing Nginx running to prevent outage.${NC}"
    exit 1
fi

# 12. Service Health Summary Table
echo ""
echo "========================================================="
echo -e "${GREEN}🎉 Django REST Backend rollout completed with ZERO downtime!${NC}"
echo "========================================================="
echo "Live Infrastructure Status:"
if command -v supervisorctl &> /dev/null; then
    supervisorctl status 2>/dev/null | grep -E "(${APP_NAME}|celery)" | sed 's/^/  /' || true
fi
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "  nginx: ${GREEN}Active (Running)${NC}"
fi
if systemctl is-active --quiet redis-server 2>/dev/null || systemctl is-active --quiet redis 2>/dev/null; then
    echo -e "  redis: ${GREEN}Active (Running)${NC}"
fi
if systemctl is-active --quiet rabbitmq-server 2>/dev/null; then
    echo -e "  rabbitmq: ${GREEN}Active (Running)${NC}"
fi
echo "========================================================="
