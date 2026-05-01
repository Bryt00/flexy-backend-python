#!/bin/bash
# Quick-patch: Add missing /v1/ proxy location to api.flexyridegh.com nginx config
# Run on the server: sudo bash patch_nginx.sh

set -e

CONF="/etc/nginx/sites-available/flexyride_backend"
BACKUP="${CONF}.bak.$(date +%Y%m%d%H%M%S)"

echo "Backing up current config to $BACKUP"
cp "$CONF" "$BACKUP"

# Check if /v1/ location already exists
if grep -q "location /v1/" "$CONF"; then
    echo "✓ /v1/ location already exists in nginx config. Nothing to do."
    exit 0
fi

# Insert the /v1/ location block BEFORE "location /callbacks/" in the api.flexyridegh.com server block.
# We use a Python-based sed equivalent for reliability on multi-line inserts.
python3 - <<'PYTHON'
import re, sys

with open("/etc/nginx/sites-available/flexyride_backend", "r") as f:
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
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
        proxy_redirect off;
    }

"""

# Insert before the first occurrence of "location /callbacks/"
if "location /callbacks/" in content:
    content = content.replace("    location /callbacks/", v1_block + "    location /callbacks/", 1)
    with open("/etc/nginx/sites-available/flexyride_backend", "w") as f:
        f.write(content)
    print("✓ /v1/ location block inserted successfully.")
else:
    # Fallback: insert before the catch-all "location /" redirect to main site
    content = content.replace(
        "    # Redirect everything else on the API subdomain to the main site\n    location / {",
        v1_block + "    # Redirect non-API paths on the API subdomain to the main site\n    location / {",
        1
    )
    with open("/etc/nginx/sites-available/flexyride_backend", "w") as f:
        f.write(content)
    print("✓ /v1/ location block inserted (fallback method).")
PYTHON

echo ""
echo "Testing nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✓ Config valid. Reloading nginx..."
    systemctl reload nginx
    echo ""
    echo "✅ Done! /v1/ API routes on api.flexyridegh.com now proxy correctly."
    echo "   Test: curl -X POST https://api.flexyridegh.com/v1/auth/register/"
else
    echo "✗ Config invalid! Restoring backup..."
    cp "$BACKUP" "$CONF"
    systemctl reload nginx
    echo "Backup restored. Fix the config manually."
    exit 1
fi
