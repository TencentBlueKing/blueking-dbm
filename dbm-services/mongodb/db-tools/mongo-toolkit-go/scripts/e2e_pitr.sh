#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SOURCE_HOST="${SOURCE_HOST:-127.0.0.1}"
SOURCE_PORT="${SOURCE_PORT:-27002}"
SOURCE_USER="${SOURCE_USER:-root}"
SOURCE_PASS="${SOURCE_PASS:-root}"
SOURCE_AUTH_DB="${SOURCE_AUTH_DB:-admin}"

TARGET_HOST="${TARGET_HOST:-}"
TARGET_PORT="${TARGET_PORT:-}"
TARGET_USER="${TARGET_USER:-$SOURCE_USER}"
TARGET_PASS="${TARGET_PASS:-$SOURCE_PASS}"
TARGET_AUTH_DB="${TARGET_AUTH_DB:-$SOURCE_AUTH_DB}"

E2E_ARCHIVE="${E2E_ARCHIVE:-1}"
E2E_KEEP_WORKDIR="${E2E_KEEP_WORKDIR:-1}"
E2E_DB="${E2E_DB:-dbm_toolkit_e2e_$(date +%Y%m%d%H%M%S)}"
E2E_COLL="${E2E_COLL:-records}"
E2E_WORKDIR="${E2E_WORKDIR:-$(mktemp -d /tmp/mongo-toolkit-go-pitr-e2e-XXXXXX)}"

BIN="$E2E_WORKDIR/mongo-toolkit-go"
BACKUP_DIR="$E2E_WORKDIR/backups"
LOG_DIR="$E2E_WORKDIR/logs"

usage() {
	cat <<EOF
Usage:
  TARGET_HOST=127.0.0.1 TARGET_PORT=27003 $0

Environment:
  SOURCE_HOST       source MongoDB host, default: 127.0.0.1
  SOURCE_PORT       source MongoDB port, default: 27002
  SOURCE_USER       source MongoDB user, default: root
  SOURCE_PASS       source MongoDB password, default: root
  SOURCE_AUTH_DB    source auth db, default: admin
  TARGET_HOST       target MongoDB host, required
  TARGET_PORT       target MongoDB port, required
  TARGET_USER       target MongoDB user, default: SOURCE_USER
  TARGET_PASS       target MongoDB password, default: SOURCE_PASS
  TARGET_AUTH_DB    target auth db, default: SOURCE_AUTH_DB
  E2E_ARCHIVE       use --archive for full/incr backup, default: 1
  E2E_KEEP_WORKDIR  keep logs/backups after test, default: 1
  E2E_DB            test database name, default: dbm_toolkit_e2e_<timestamp>
  E2E_WORKDIR       work directory, default: /tmp/mongo-toolkit-go-pitr-e2e-XXXXXX

This test writes to SOURCE, restores into TARGET, and drops E2E_DB on both instances.
Use disposable replica-set instances only. Full restore is instance-level and may overwrite
data on TARGET.
EOF
}

log() {
	printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

die() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

need_cmd() {
	command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

mongo_eval() {
	local role="$1"
	local js="$2"
	shift 2

	local host port user pass auth_db
	if [[ "$role" == "source" ]]; then
		host="$SOURCE_HOST"
		port="$SOURCE_PORT"
		user="$SOURCE_USER"
		pass="$SOURCE_PASS"
		auth_db="$SOURCE_AUTH_DB"
	elif [[ "$role" == "target" ]]; then
		host="$TARGET_HOST"
		port="$TARGET_PORT"
		user="$TARGET_USER"
		pass="$TARGET_PASS"
		auth_db="$TARGET_AUTH_DB"
	else
		die "bad mongo_eval role: $role"
	fi

	mongosh \
		--host "$host" \
		--port "$port" \
		--username "$user" \
		--password "$pass" \
		--authenticationDatabase "$auth_db" \
		--quiet \
		--eval "$js" "$@"
}

check_instance() {
	local role="$1"
	mongo_eval "$role" '
const h = db.adminCommand({hello: 1});
if (!h.ok) {
  print("hello failed");
  quit(2);
}
if (!h.setName) {
  print("not a replica set");
  quit(3);
}
if (!h.isWritablePrimary) {
  print("not writable primary");
  quit(4);
}
print(JSON.stringify({setName: h.setName, isWritablePrimary: h.isWritablePrimary, version: db.version()}));
'
}

backup_args_common() {
	local role="$1"
	if [[ "$role" != "source" ]]; then
		die "backup role must be source"
	fi
	printf '%s\n' \
		--host "$SOURCE_HOST" \
		--port "$SOURCE_PORT" \
		--user "$SOURCE_USER" \
		--pass "$SOURCE_PASS" \
		--authdb "$SOURCE_AUTH_DB" \
		--dir "$BACKUP_DIR" \
		--logLevel info
}

run_backup() {
	local backup_type="$1"
	local log_file="$LOG_DIR/backup-${backup_type}.log"
	local args=()
	mapfile -t args < <(backup_args_common source)
	args+=(--type "$backup_type")
	if [[ "$E2E_ARCHIVE" == "1" ]]; then
		args+=(--zip --archive)
	fi

	log "running ${backup_type} backup"
	"$BIN" backup "${args[@]}" >"$log_file" 2>&1
}

run_recover() {
	local recover_time="$1"
	local log_file="$LOG_DIR/recover.log"

	log "running recover to ${TARGET_HOST}:${TARGET_PORT} at ${recover_time}"
	"$BIN" recover \
		--host "$TARGET_HOST" \
		--port "$TARGET_PORT" \
		--user "$TARGET_USER" \
		--pass "$TARGET_PASS" \
		--authdb "$TARGET_AUTH_DB" \
		--dir "$BACKUP_DIR" \
		--src "${SOURCE_HOST}:${SOURCE_PORT}" \
		--recover-time "$recover_time" \
		--logLevel info >"$log_file" 2>&1
}

verify_target() {
	local marker="$1"
	local expected_js="$2"
	mongo_eval target "
const marker = '$marker';
const dbName = '$E2E_DB';
const collName = '$E2E_COLL';
const docs = db.getSiblingDB(dbName).getCollection(collName).find({marker}).sort({step: 1}).toArray();
printjson(docs.map(d => ({step: d.step, marker: d.marker})));
$expected_js
"
}

main() {
	if [[ -z "$TARGET_HOST" || -z "$TARGET_PORT" ]]; then
		usage
		die "TARGET_HOST and TARGET_PORT are required"
	fi
	if [[ "$SOURCE_HOST:$SOURCE_PORT" == "$TARGET_HOST:$TARGET_PORT" && "${E2E_ALLOW_SAME_INSTANCE:-0}" != "1" ]]; then
		die "source and target are the same instance; set E2E_ALLOW_SAME_INSTANCE=1 only for disposable tests"
	fi

	need_cmd go
	need_cmd mongosh

	mkdir -p "$BACKUP_DIR" "$LOG_DIR"
	if [[ "$E2E_KEEP_WORKDIR" != "1" ]]; then
		trap 'rm -rf "$E2E_WORKDIR"' EXIT
	fi

	log "workdir: $E2E_WORKDIR"
	log "checking source ${SOURCE_HOST}:${SOURCE_PORT}"
	check_instance source
	log "checking target ${TARGET_HOST}:${TARGET_PORT}"
	check_instance target

	log "building mongo-toolkit-go"
	(cd "$ROOT_DIR" && go build -o "$BIN" ./cmd/mongo-toolkit-go)

	local marker recover_time
	marker="mongo-toolkit-go-pitr-e2e-$(date +%s)"

	log "resetting test db $E2E_DB on source and target"
	mongo_eval source "db.getSiblingDB('$E2E_DB').dropDatabase();"
	mongo_eval target "db.getSiblingDB('$E2E_DB').dropDatabase();"

	log "inserting full-backup baseline document"
	mongo_eval source "
db.getSiblingDB('$E2E_DB').getCollection('$E2E_COLL').insertOne({
  marker: '$marker',
  step: 'full',
  createdAt: new Date()
});
"

	run_backup FULL

	sleep 2
	log "inserting document that should be restored by incremental replay"
	mongo_eval source "
db.getSiblingDB('$E2E_DB').getCollection('$E2E_COLL').insertOne({
  marker: '$marker',
  step: 'incr-before-recover-time',
  createdAt: new Date()
});
db.getSiblingDB('$E2E_DB').getCollection('$E2E_COLL').updateOne(
  {marker: '$marker', step: 'full'},
  {\$set: {updatedByIncrOplog: true, updatedAt: new Date()}}
);
db.getSiblingDB('$E2E_DB').getCollection('$E2E_COLL').insertOne({
  marker: '$marker',
  step: 'delete-before-recover-time',
  createdAt: new Date()
});
db.getSiblingDB('$E2E_DB').getCollection('$E2E_COLL').deleteOne({
  marker: '$marker',
  step: 'delete-before-recover-time'
});
"
	recover_time="$(date '+%Y-%m-%dT%H:%M:%S')"

	sleep 2
	log "inserting document that should be excluded by recover-time"
	mongo_eval source "
db.getSiblingDB('$E2E_DB').getCollection('$E2E_COLL').insertOne({
  marker: '$marker',
  step: 'incr-after-recover-time',
  createdAt: new Date()
});
"

	run_backup INCR

	log "dropping test db on target before restore"
	mongo_eval target "db.getSiblingDB('$E2E_DB').dropDatabase();"
	run_recover "$recover_time"

	log "verifying restored target data"
	verify_target "$marker" "
const steps = docs.map(d => d.step).sort();
if (steps.length !== 2 ||
    steps[0] !== 'full' ||
    steps[1] !== 'incr-before-recover-time') {
  print('unexpected restored steps: ' + JSON.stringify(steps));
  quit(10);
}
if (db.getSiblingDB(dbName).getCollection(collName).countDocuments({marker, step: 'full', updatedByIncrOplog: true}) !== 1) {
  print('incremental update oplog was not replayed');
  quit(11);
}
if (db.getSiblingDB(dbName).getCollection(collName).countDocuments({marker, step: 'delete-before-recover-time'}) !== 0) {
  print('incremental delete oplog was not replayed');
  quit(12);
}
if (db.getSiblingDB(dbName).getCollection(collName).countDocuments({marker, step: 'incr-after-recover-time'}) !== 0) {
  print('post recover-time document was restored unexpectedly');
  quit(13);
}
"

	log "backup artifacts:"
	compgen -G "$BACKUP_DIR/*" || true
	log "PASS: full backup, incremental backup, and point-in-time recover succeeded"
	log "workdir kept at: $E2E_WORKDIR"
}

main "$@"
