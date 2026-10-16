#!/bin/bash
# ============================================================
# FlexyRide Local Development Startup Script (100% On-Machine)
# 
# Runs Redis, PostgreSQL, flexy-engine, and Django natively.
# Zero Docker dependency.
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
    echo -e "${GREEN}✓ All local background services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}  FlexyRide On-Machine Development Server${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""

# ── 1. Start Native Redis (On-Machine) ─────────────────────
echo -e "${YELLOW}1. Checking native on-machine Redis (port 6379)...${NC}"
if ! redis-cli -p 6379 ping 2>/dev/null | grep -q "PONG"; then
    echo -e "${YELLOW}   Starting native redis-server on port 6379...${NC}"
    redis-server --port 6379 --daemonize yes
    sleep 0.5
fi
echo -e "${GREEN}   ✓ Native Redis is running on localhost:6379${NC}"
echo ""

# ── 2. Check PostgreSQL (On-Machine) ───────────────────────
echo -e "${YELLOW}2. Checking native PostgreSQL...${NC}"
if pg_isready -q 2>/dev/null || pg_isready -h localhost -p 5432 -q 2>/dev/null; then
    echo -e "${GREEN}   ✓ PostgreSQL is running on port 5432${NC}"
else
    echo -e "${RED}   ✗ PostgreSQL is not running. Please check postgres service.${NC}"
    exit 1
fi
echo ""

# ── 3. Start flexy-engine (Go On-Machine Daemon) ───────────
echo -e "${YELLOW}3. Starting flexy-engine (Go native engine)...${NC}"
ENGINE_BIN="$SCRIPT_DIR/engine/bin/flexy-engine"
if [ ! -f "$ENGINE_BIN" ]; then
    echo -e "${YELLOW}   Compiling flexy-engine...${NC}"
    (cd engine && go build -o bin/flexy-engine ./cmd/flexy-engine)
fi
SOCKET_PATH="/tmp/flexy_engine.sock"
rm -f "$SOCKET_PATH"
"$ENGINE_BIN" -socket "$SOCKET_PATH" -port 8091 -redis "redis://localhost:6379/0" &
PIDS+=($!)
sleep 0.8
echo -e "${GREEN}   ✓ flexy-engine started on $SOCKET_PATH and :8091 (PID: ${PIDS[-1]})${NC}"
echo ""

# ── 4. Python Environment ──────────────────────────────────
echo -e "${YELLOW}4. Selecting Python environment...${NC}"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    PYTHON_CMD="python"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi
echo -e "${GREEN}   ✓ Using $($PYTHON_CMD --version)${NC}"
echo ""

# ── 5. Run migrations & sync config ────────────────────────
echo -e "${YELLOW}5. Running migrations & syncing engine config...${NC}"
$PYTHON_CMD manage.py migrate --noinput
$PYTHON_CMD manage.py engine_sync_config
echo -e "${GREEN}   ✓ Database & engine config in sync${NC}"
echo ""

# ── 6. Start Celery Worker (background) ────────────────────
echo -e "${YELLOW}6. Starting Celery Worker (native Redis broker)...${NC}"
$PYTHON_CMD -m celery -A flexy_backend worker -l info --pool=solo &
PIDS+=($!)
echo -e "${GREEN}   ✓ Celery Worker started (PID: ${PIDS[-1]})${NC}"
echo ""

# ── 7. Start Celery Beat (background) ──────────────────────
echo -e "${YELLOW}7. Starting Celery Beat...${NC}"
$PYTHON_CMD -m celery -A flexy_backend beat -l info &
PIDS+=($!)
echo -e "${GREEN}   ✓ Celery Beat started (PID: ${PIDS[-1]})${NC}"
echo ""

# ── 8. Start Django Dev Server (foreground) ────────────────
echo -e "${YELLOW}8. Starting Django Development Server...${NC}"
echo -e "${GREEN}   → http://localhost:8000${NC}"
echo -e "${GREEN}   → Admin: http://localhost:8000/admin/${NC}"
echo -e "${GREEN}   → Engine API: http://localhost:8091/healthz${NC}"
echo -e "${GREEN}   → API Docs: http://localhost:8000/api/schema/swagger-ui/${NC}"
echo ""
echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}  Press Ctrl+C to stop all services${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""

$PYTHON_CMD manage.py runserver 0.0.0.0:8000
