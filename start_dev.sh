#!/bin/bash
# ============================================================
# FlexyRide Local Development Startup Script
# 
# Runs Redis & RabbitMQ in Docker, everything else natively.
# Usage: bash start_dev.sh
# ============================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Track background PIDs for cleanup
PIDS=()

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null || true
        fi
    done
    echo -e "${YELLOW}Stopping Docker containers...${NC}"
    sudo docker compose down 2>/dev/null || true
    echo -e "${GREEN}✓ All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}  FlexyRide Local Development Server${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""

# ── 1. Start Docker containers (Redis + RabbitMQ) ──────────
echo -e "${YELLOW}1. Starting Redis & RabbitMQ (Docker)...${NC}"
sudo docker compose up -d
echo -e "${GREEN}   ✓ Redis on localhost:6379${NC}"
echo -e "${GREEN}   ✓ RabbitMQ on localhost:5672 (management: http://localhost:15672)${NC}"
echo -e "${YELLOW}   ⏳ Waiting for RabbitMQ to fully boot...${NC}"
sleep 15
echo ""

# ── 2. Activate virtual environment ────────────────────────
echo -e "${YELLOW}2. Activating Python virtual environment...${NC}"
if [ ! -f "venv/bin/activate" ]; then
    echo -e "${RED}   ✗ venv not found. Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi
source venv/bin/activate
echo -e "${GREEN}   ✓ Using $(python --version) from venv${NC}"
echo ""

# ── 3. Check PostgreSQL is running ─────────────────────────
echo -e "${YELLOW}3. Checking PostgreSQL...${NC}"
if pg_isready -q 2>/dev/null; then
    echo -e "${GREEN}   ✓ PostgreSQL is running${NC}"
else
    echo -e "${RED}   ✗ PostgreSQL is not running. Start it with: sudo systemctl start postgresql${NC}"
    exit 1
fi
echo ""

# ── 4. Run migrations ──────────────────────────────────────
echo -e "${YELLOW}4. Running migrations...${NC}"
python manage.py migrate --noinput
echo -e "${GREEN}   ✓ Migrations complete${NC}"
echo ""

# ── 5. Start Celery Worker (background) ────────────────────
echo -e "${YELLOW}5. Starting Celery Worker...${NC}"
celery -A flexy_backend worker -l info --pool=solo &
PIDS+=($!)
echo -e "${GREEN}   ✓ Celery Worker started (PID: ${PIDS[-1]})${NC}"
echo ""

# ── 6. Start Celery Beat (background) ──────────────────────
echo -e "${YELLOW}6. Starting Celery Beat...${NC}"
celery -A flexy_backend beat -l info &
PIDS+=($!)
echo -e "${GREEN}   ✓ Celery Beat started (PID: ${PIDS[-1]})${NC}"
echo ""

# ── 7. Start Django Dev Server (foreground) ────────────────
echo -e "${YELLOW}7. Starting Django Development Server...${NC}"
echo -e "${GREEN}   → http://localhost:8000${NC}"
echo -e "${GREEN}   → Admin: http://localhost:8000/admin/${NC}"
echo -e "${GREEN}   → API Docs: http://localhost:8000/api/schema/swagger-ui/${NC}"
echo ""
echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}  Press Ctrl+C to stop all services${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""

python manage.py runserver 0.0.0.0:8000
