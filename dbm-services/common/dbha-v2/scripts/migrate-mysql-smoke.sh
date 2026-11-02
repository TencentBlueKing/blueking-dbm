#!/usr/bin/env bash
#
# MIT License
#
# Copyright (c) 2023 腾讯蓝鲸
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# CLI smoke test of `admin migrate` against two loopback MySQL servers.
# The CLI always migrates the production database name, so the script refuses to run when
# that database already exists and only drops what it created itself.
#
# Environment:
#   DBHA_TEST_MYSQL_PASSWORD  required
#   DBHA_TEST_MYSQL_USER      default root
#   DBHA_TEST_MYSQL_PORT      default 13306
#   DBHA_TEST_MYSQL_PORT_B    default 13307
set -uo pipefail

DBHA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST=127.0.0.1
DB=dbha_data
USER_NAME="${DBHA_TEST_MYSQL_USER:-root}"
PORT_A="${DBHA_TEST_MYSQL_PORT:-13306}"
PORT_B="${DBHA_TEST_MYSQL_PORT_B:-13307}"
MYSQL_BIN="${MYSQL_BIN:-mysql}"

if [[ -z "${DBHA_TEST_MYSQL_PASSWORD:-}" ]]; then
  echo "DBHA_TEST_MYSQL_PASSWORD is not set" >&2
  exit 2
fi
export MYSQL_PWD="$DBHA_TEST_MYSQL_PASSWORD"

TMP="$(mktemp -d)"
chmod 700 "$TMP"
BIN="$TMP/admin"
CFG="$TMP/admin.yaml"
CREATED_DB=0
PASSED=0
FAILED=0
SUMMARY=()

cleanup() {
  if [[ "$CREATED_DB" == 1 ]]; then
    for port in "$PORT_A" "$PORT_B"; do
      sql "$port" "DROP DATABASE IF EXISTS \`$DB\`" >/dev/null 2>&1 || true
    done
  fi
  rm -rf "$TMP"
}
trap cleanup EXIT

sql() {
  local port="$1" query="$2"
  "$MYSQL_BIN" -h "$HOST" -P "$port" -u "$USER_NAME" -N -B -e "$query"
}

record() {
  local result="$1" name="$2"
  SUMMARY+=("$result  $name")
  if [[ "$result" == PASS ]]; then
    PASSED=$((PASSED + 1))
  else
    FAILED=$((FAILED + 1))
  fi
}

# migrate runs the CLI from the temp dir so it can never pick up ./etc/admin.yaml of the repo.
migrate() {
  (cd "$TMP" && "$BIN" migrate -c "$CFG" "$@") >"$TMP/last.out" 2>&1
}

expect_ok() {
  local name="$1"
  shift
  if migrate "$@"; then
    record PASS "$name"
  else
    record FAIL "$name"
    tail -n 20 "$TMP/last.out" >&2
  fi
}

expect_fail() {
  local name="$1"
  shift
  if migrate "$@"; then
    record FAIL "$name"
    tail -n 20 "$TMP/last.out" >&2
  else
    record PASS "$name"
  fi
}

check() {
  local name="$1" want="$2" got="$3"
  if [[ "$got" == "$want" ]]; then
    record PASS "$name"
  else
    record FAIL "$name (want: $want, got: $got)"
  fi
}

column_count() {
  sql "$1" "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = '$DB' \
AND TABLE_NAME = 't_dbha_status' AND COLUMN_NAME = 'probe'"
}

strategy_count() {
  sql "$1" "SELECT COUNT(*) FROM \`$DB\`.\`t_db_switching_strategy\`"
}

# Preconditions: reachable, writable, and no pre-existing production database.
for port in "$PORT_A" "$PORT_B"; do
  if ! flags="$(sql "$port" "SELECT @@read_only + @@super_read_only")"; then
    echo "mysql is unreachable, endpoint: $HOST:$port" >&2
    exit 2
  fi
  if [[ "$flags" != 0 ]]; then
    echo "mysql is read only, endpoint: $HOST:$port" >&2
    exit 2
  fi
  exists="$(sql "$port" "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = '$DB'")"
  if [[ "$exists" != 0 ]]; then
    echo "database already exists, refusing to touch it, endpoint: $HOST:$port, database: $DB" >&2
    exit 2
  fi
done

echo "build admin"
if ! (cd "$DBHA_ROOT" && CGO_ENABLED=0 go build -o "$BIN" ./cmd/admin); then
  echo "build admin failed" >&2
  exit 2
fi

quoted_password="${DBHA_TEST_MYSQL_PASSWORD//\'/\'\'}"
umask 077
cat >"$CFG" <<EOF
storage:
  endpoint: "$HOST:$PORT_A;$HOST:$PORT_B"
  user: "$USER_NAME"
  password: '$quoted_password'
EOF

CREATED_DB=1

echo "run migrate smoke, endpoints: $HOST:$PORT_A, $HOST:$PORT_B"
expect_ok "type schema" -t schema
check "schema mode wrote no strategy" 0 "$(strategy_count "$PORT_A")"
expect_ok "type data" -t data
expect_ok "type all is idempotent" -t all
defaults="$(strategy_count "$PORT_A")"
check "both servers hold the same strategies" "$defaults" "$(strategy_count "$PORT_B")"

expect_ok "inventory" --inventory
for port in "$PORT_A" "$PORT_B"; do
  check "inventory lists $HOST:$port" 1 "$(grep -c "^endpoint  $HOST:$port\$" "$TMP/last.out")"
done
expect_ok "inventory-full" --inventory-full
check "inventory-full prints column blocks per endpoint" 2 "$(grep -c '^table: t_dbha_status$' "$TMP/last.out")"

sql "$PORT_A" "ALTER TABLE \`$DB\`.\`t_dbha_status\` DROP COLUMN \`probe\`"
expect_fail "recorded column loss is drift" -t all
check "drift kept the column missing" 0 "$(column_count "$PORT_A")"
expect_ok "repair-missing" -t all --repair-missing
check "repair-missing restored the column" 1 "$(column_count "$PORT_A")"

sql "$PORT_A" "DELETE FROM \`$DB\`.\`t_db_switching_strategy\` ORDER BY id LIMIT 1"
expect_ok "data without repair" -t data
check "data without repair skipped the missing strategy" "$((defaults - 1))" "$(strategy_count "$PORT_A")"
expect_ok "repair-missing-data" -t data --repair-missing-data
check "repair-missing-data restored the strategy" "$defaults" "$(strategy_count "$PORT_A")"

expect_fail "unknown type is rejected" -t foo
expect_fail "inventory with repair is rejected" --inventory --repair-missing

echo
printf '%s\n' "${SUMMARY[@]}"
echo "passed: $PASSED, failed: $FAILED"
[[ "$FAILED" == 0 ]]
