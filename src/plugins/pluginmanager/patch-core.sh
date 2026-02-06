#!/usr/bin/env bash
set -e

# Default PROJECT_DIR to project root when unset
if [[ -z "${PROJECT_DIR:-}" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

echo "[INFO] Patching core files for plugin blueprint support..."

# Run the Python patch script
python3 -c "
import sys
import os
sys.path.insert(0, '$PLUGIN_DIR')
from patch_core import patch_core_files

success, error = patch_core_files()
if not success:
    print(f'[ERROR] Patch failed: {error}')
    sys.exit(1)
print('[INFO] Core files patched successfully')
"

echo "[INFO] Done"

# Restart service if APPNAME is set
if [[ -n "${APPNAME:-}" ]]; then
    echo "[INFO] Restarting $APPNAME service."
    sudo systemctl restart "$APPNAME.service" 2>&1 || echo "[WARN] Service restart failed"
else
    echo "[INFO] APPNAME not set, skipping service restart (e.g. development mode)"
fi
