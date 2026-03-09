#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/sql"
ENV_FILE="${SCRIPT_DIR}/.env"

# --- Load configuration ---
# Priority: environment variables > .env file
# In deployment, DBS_MYSQL_* env vars are already set by the runtime.
# For local development, you can create a .env file:
#   cp .env.sample .env && vim .env

if [ -z "${DBS_MYSQL_HOST:-}" ] && [ -f "$ENV_FILE" ]; then
    echo "Loading config from ${ENV_FILE}"
    source "$ENV_FILE"
fi

# Validate required variables
for var in DBS_MYSQL_HOST DBS_MYSQL_PORT DBS_MYSQL_USER DBS_MYSQL_PASSWORD; do
    if [ -z "${!var:-}" ]; then
        echo "Error: ${var} is not set."
        echo ""
        echo "Either set it as an environment variable, or create a .env file:"
        echo "  cp ${SCRIPT_DIR}/.env.sample ${ENV_FILE}"
        exit 1
    fi
done

# --- Build mysql command ---
# Use a temporary defaults file to pass password securely (avoids ps aux exposure
# and the deprecated MYSQL_PWD env var which may not work on MySQL 8.0+)
MYSQL_DEFAULTS_FILE=$(mktemp)
trap 'rm -f "${MYSQL_DEFAULTS_FILE}"' EXIT
chmod 600 "${MYSQL_DEFAULTS_FILE}"
cat > "${MYSQL_DEFAULTS_FILE}" <<EOF
[client]
host=${DBS_MYSQL_HOST}
port=${DBS_MYSQL_PORT}
user=${DBS_MYSQL_USER}
password=${DBS_MYSQL_PASSWORD}
EOF
MYSQL_CMD="mysql --defaults-extra-file=${MYSQL_DEFAULTS_FILE}"

# --- Test connection ---
echo "Testing MySQL connection to ${DBS_MYSQL_HOST}:${DBS_MYSQL_PORT}..."
if ! ${MYSQL_CMD} -e "SELECT 1" > /dev/null 2>&1; then
    echo "Error: Cannot connect to MySQL at ${DBS_MYSQL_HOST}:${DBS_MYSQL_PORT}"
    exit 1
fi
echo "Connection OK."
echo ""

# --- Execute SQL files in order ---
TOTAL=0
SUCCESS=0
FAILED=0

for sql_file in "${SQL_DIR}"/*.sql; do
    [ -f "$sql_file" ] || continue
    filename=$(basename "$sql_file")
    TOTAL=$((TOTAL + 1))
    echo -n "Executing: ${filename} ... "

    if output=$(${MYSQL_CMD} < "$sql_file" 2>&1); then
        echo "OK"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "FAILED"
        echo "  Error: ${output}"
        FAILED=$((FAILED + 1))
    fi
done

# --- Summary ---
echo ""
echo "========================================="
echo "Total: ${TOTAL}  Success: ${SUCCESS}  Failed: ${FAILED}"
echo "========================================="

if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
