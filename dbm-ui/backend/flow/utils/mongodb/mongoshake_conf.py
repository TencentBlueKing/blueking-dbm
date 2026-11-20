# -*- coding: utf-8 -*-
"""MongoShake collector.conf 与启动脚本。mongo-dts.tar.gz 下发到 JobHost 后解包。"""

import os
import re
import shlex
import zlib
from urllib.parse import quote

MONGO_DTS_ROOT = "/data/mongo-dts"
MONGO_DTS_PKG_NAME = "mongo-dts.tar.gz"
MONGOSHAKE_BIN_NAME = "collector.linux"
CONF_VERSION = 14
CATCHUP_LAG_SECONDS = 15
CATCHUP_STABLE_ROUNDS = 3
CATCHUP_POLL_SECONDS = 10

# 源端拉数策略（写入 collector.conf 的 mongo_connect_mode）。
SOURCE_CONNECT_BACKUP = "backup"
SOURCE_CONNECT_SECONDARY_PREFERRED = "secondaryPreferred"
SOURCE_CONNECT_MODES = (SOURCE_CONNECT_BACKUP, SOURCE_CONNECT_SECONDARY_PREFERRED)
MONGO_CONNECT_STANDALONE = "standalone"
MONGO_CONNECT_SECONDARY_PREFERRED = "secondaryPreferred"

# 同步停止方式：追平自动停 / 人工确认后停。
STOP_MODE_AUTO = "auto"
STOP_MODE_MANUAL = "manual"
STOP_MODES = (STOP_MODE_AUTO, STOP_MODE_MANUAL)


def mongo_uri(user: str, password: str, addrs: list) -> str:
    if not addrs:
        raise ValueError("mongo address is empty")
    if "@" in user or "@" in password:
        raise ValueError("MongoShake URL cannot contain @ in user or password")
    return "mongodb://{}:{}@{}".format(quote(user, safe=""), quote(password, safe=""), ",".join(addrs))


def replica_set_connect_uri(addrs: list, set_name: str) -> str:
    """无密码副本集连接串，mongosh 会路由到 primary。账号用 -u/-p 传入。"""
    if not addrs:
        raise ValueError("mongo address is empty")
    name = (set_name or "").strip()
    if not name:
        raise ValueError("replica set name is empty")
    if any(ch in name for ch in " ;?\n\t"):
        raise ValueError("invalid replica set name {}".format(set_name))
    return "mongodb://{}/?replicaSet={}".format(",".join(addrs), name)


def assert_mongoshake_supported_version(version: str) -> None:
    """MongoShake 对 MongoDB 8 无明确支持，major >= 8 直接拒绝。"""
    from backend.flow.utils.mongodb.version_utils import extract_mongodb_version_tuple

    major, _, _ = extract_mongodb_version_tuple(version)
    if major >= 8:
        raise Exception("MongoShake does not support MongoDB {}: major version >= 8".format(version))


def namespace_list(items) -> str:
    """库或库.表，分号分隔。不支持正则。"""
    if not items:
        return ""
    parts = []
    for item in items:
        name = str(item).strip()
        if not name or any(ch in name for ch in " ;*\n\t"):
            raise ValueError("invalid namespace {}".format(item))
        parts.append(name)
    return ";".join(parts)


def collector_http_ports(collector_id: str):
    """同一台 MongoDts 上按任务错开全量/增量监控端口。"""
    slot = zlib.crc32(collector_id.encode()) % 4000
    full_port = 21000 + slot * 2
    return full_port, full_port + 1


def repl_caught_up(repl: dict, lag_seconds: int = CATCHUP_LAG_SECONDS) -> bool:
    """lsn_ack 已经有位点，并且落后 now 不超过 lag_seconds。"""
    ack = int((repl.get("lsn_ack") or {}).get("unix") or 0)
    now = int((repl.get("now") or {}).get("unix") or 0)
    return ack > 0 and now >= ack and now - ack <= lag_seconds


def normalize_source_connect_mode(mode: str = None) -> str:
    """infos.source_connect_mode：backup | secondaryPreferred，默认 secondaryPreferred。"""
    value = (mode or SOURCE_CONNECT_SECONDARY_PREFERRED).strip()
    if value not in SOURCE_CONNECT_MODES:
        raise ValueError("source_connect_mode must be one of {}, got {}".format(SOURCE_CONNECT_MODES, mode))
    return value


def normalize_stop_mode(mode: str = None) -> str:
    """infos.stop_mode：auto（追平自动停，默认）| manual（人工确认后停）。"""
    value = (mode or STOP_MODE_AUTO).strip()
    if value not in STOP_MODES:
        raise ValueError("stop_mode must be one of {}, got {}".format(STOP_MODES, mode))
    return value


def stop_collector_script(work_dir: str, remove_conf: bool = False) -> str:
    """按 collector.pid 停止 MongoShake（先 SIGTERM，再 SIGKILL）。"""
    work = shlex.quote(work_dir)
    lines = [
        "set -euo pipefail",
        "pid_file={work}/collector.pid".format(work=work),
        'if [ -f "$pid_file" ]; then',
        '  pid=$(cat "$pid_file")',
        '  if kill -0 "$pid" 2>/dev/null; then',
        '    kill "$pid" || true',
        "    for i in $(seq 1 30); do",
        '      if ! kill -0 "$pid" 2>/dev/null; then break; fi',
        "      sleep 1",
        "    done",
        '    if kill -0 "$pid" 2>/dev/null; then kill -9 "$pid" || true; fi',
        "  fi",
        "fi",
        'echo "collector stopped"',
    ]
    if remove_conf:
        # Keep logs for triage; only drop plaintext connection strings.
        lines.append("rm -f {work}/collector.conf".format(work=work))
    lines.append("")
    return "\n".join(lines)


def cleanup_dts_work_script(work_dir: str) -> str:
    """失败/手动清理：停 collector 并删除明文 collector.conf（保留日志目录）。"""
    return stop_collector_script(work_dir, remove_conf=True)


def _catchup_watcher_source() -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mongoshake_catchup_watcher.py")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _iter_user_collection_names_js() -> str:
    """Shared JS snippet: iterate real collections (skip views / system.*) under user dbs."""
    # Use double quotes inside so shlex.quote (single-quoted) keeps type:"collection" intact.
    return (
        "var skip={admin:1,config:1,local:1,test:1};"
        "function eachUserColl(fn){"
        "db.adminCommand({listDatabases:1}).databases.forEach(function(d){"
        "if(skip[d.name]){return;}"
        "var dbo=db.getSiblingDB(d.name);"
        'dbo.getCollectionInfos({type:"collection"}).forEach(function(info){'
        "var c=info.name;"
        'if(c.indexOf("system.")===0){return;}'
        "fn(d.name,c,dbo)})})}"
    )


def check_empty_target_script(ip: str, port: int, dba_user: str, dba_password: str, connect_uri: str = "") -> str:
    """目标用户集合必须无文档。允许已做 enableSharding/shardCollection 的空表（RS→分片场景）。"""
    # Prefer findOne / estimatedDocumentCount to avoid full scans on large mistaken targets.
    js = (
        _iter_user_collection_names_js()
        + "var bad=[];"
        + "eachUserColl(function(dbn,c,dbo){"
        + "var coll=dbo.getCollection(c);"
        + "var has=false;"
        + "try{has=coll.estimatedDocumentCount()>0}catch(e){has=!!coll.findOne()}"
        + "if(has){bad.push(dbn+'.'+c)}});"
        + "if(bad.length){throw new Error('target not empty: '+bad.join(','))}"
    )
    return _mongo_shell_eval_script(ip, port, dba_user, dba_password, js, connect_uri=connect_uri)


def assert_target_user_collections_sharded_script(
    ip: str, port: int, dba_user: str, dba_password: str, connect_uri: str = ""
) -> str:
    """
    目标为分片集群时：用户集合必须已在 config.collections 中（允许预建空分片表）。
    若目标上还没有任何用户分片表，直接失败，避免数据落到 primary shard。
    """
    js = (
        _iter_user_collection_names_js()
        + "var cfg=db.getSiblingDB('config').collections;"
        + "var missing=[]; var seen=0;"
        + "eachUserColl(function(dbn,c){"
        + "seen+=1;"
        + "var ns=dbn+'.'+c;"
        + "var ok=cfg.find({_id:ns,dropped:{$ne:true}}).limit(1).hasNext();"
        + "if(!ok){missing.push(ns)}});"
        + "if(seen===0){"
        + "var n=cfg.find({_id:{$not:/^(admin|config|local)\\./},dropped:{$ne:true}}).limit(1).hasNext();"
        + "if(!n){throw new Error('no user sharded collections; run shardCollection on target first')}}"
        + "if(missing.length){throw new Error('collections not sharded: '+missing.join(','))}"
    )
    return _mongo_shell_eval_script(ip, port, dba_user, dba_password, js, connect_uri=connect_uri)


def drop_mongoshake_ckpt_script(
    ip: str,
    port: int,
    dba_user: str,
    dba_password: str,
    collector_id: str,
    connect_uri: str = "",
) -> str:
    """清理目标上 MongoShake checkpoint 集合 mongoshake.ckpt_<collector_id>。"""
    coll = "ckpt_{}".format(collector_id)
    if not re.match(r"^ckpt_[A-Za-z0-9]+$", coll):
        raise ValueError("invalid checkpoint collection name")
    js = "var dbx=db.getSiblingDB('mongoshake');" "try{{dbx.getCollection({coll!r}).drop()}}catch(e){{}}".format(
        coll=coll
    )
    return _mongo_shell_eval_script(ip, port, dba_user, dba_password, js, connect_uri=connect_uri)


def resolve_source_connect(
    source_connect_mode: str,
    user: str,
    password: str,
    *,
    is_sharded: bool,
    member_addrs: list = None,
    backup_addr: str = None,
    mongos_addrs: list = None,
    cluster_name: str = "",
):
    """
    返回 (source_urls, source_mongos_url, mongo_connect_mode)。
    backup：副本集只连 backup，standalone；secondaryPreferred：全成员 / mongos。
    """
    mode = normalize_source_connect_mode(source_connect_mode)
    if is_sharded:
        if mode == SOURCE_CONNECT_BACKUP:
            raise ValueError("source_connect_mode=backup is only supported for replica set source")
        return "", mongo_uri(user, password, mongos_addrs or []), MONGO_CONNECT_SECONDARY_PREFERRED
    if mode == SOURCE_CONNECT_BACKUP:
        if not backup_addr:
            raise ValueError(
                "source_connect_mode=backup but cluster {} has no MONGO_BACKUP member".format(cluster_name or "?")
            )
        return mongo_uri(user, password, [backup_addr]), "", MONGO_CONNECT_STANDALONE
    return mongo_uri(user, password, member_addrs or []), "", MONGO_CONNECT_SECONDARY_PREFERRED


def build_collector_conf(
    collector_id: str,
    log_dir: str,
    source_urls: str,
    source_mongos_url: str,
    target_url: str,
    namespace_white: str = "",
    transform_namespace: str = "",
    full_http_port: int = -1,
    incr_http_port: int = -1,
    mongo_connect_mode: str = MONGO_CONNECT_SECONDARY_PREFERRED,
) -> str:
    """change_stream + 全量增量。checkpoint 写到目标 mongoshake 库，不写源业务库。"""
    if not source_urls and not source_mongos_url:
        raise ValueError("source mongo_urls or mongo_s_url is required")
    connect_mode = (mongo_connect_mode or MONGO_CONNECT_SECONDARY_PREFERRED).strip()
    if connect_mode not in (MONGO_CONNECT_STANDALONE, MONGO_CONNECT_SECONDARY_PREFERRED):
        raise ValueError("mongo_connect_mode must be standalone or secondaryPreferred")
    lines = [
        "conf.version = {}".format(CONF_VERSION),
        "id = {}".format(collector_id),
        "master_quorum = false",
        "full_sync.http_port = {}".format(int(full_http_port)),
        "incr_sync.http_port = {}".format(int(incr_http_port)),
        "prom.http_port = -1",
        "system_profile_port = -1",
        "log.level = info",
        "log.dir = {}".format(log_dir),
        "sync_mode = all",
        "mongo_urls = {}".format(source_urls),
        "mongo_cs_url =",
        "mongo_s_url = {}".format(source_mongos_url),
        "mongo_connect_mode = {}".format(connect_mode),
        "tunnel = direct",
        "tunnel.address = {}".format(target_url),
        "filter.namespace.black =",
        "filter.namespace.white = {}".format(namespace_white),
        "filter.ddl_enable = false",
        "filter.pass.special.db =",
        "transform.namespace = {}".format(transform_namespace or ""),
        "checkpoint.storage.url = {}".format(target_url),
        "checkpoint.storage.db = mongoshake",
        "checkpoint.storage.collection = ckpt_{}".format(collector_id),
        "checkpoint.start_position = 1970-01-01T00:00:00Z",
        "full_sync.collection_exist_drop = false",
        "incr_sync.mongo_fetch_method = change_stream",
        "",
    ]
    return "\n".join(lines)


def dts_host_from_extension(extension) -> dict:
    details = getattr(extension, "details", None) or {}
    ip = details.get("ip")
    if not ip:
        raise Exception("MongoDts machine is not registered: DBExtension MONGODB_DTS details.ip is empty")
    return {"ip": ip}


def mongo_dts_pkg_path(root: str = MONGO_DTS_ROOT) -> str:
    """SendMedia 把 mongo-dts.tar.gz 落到 root/install/。"""
    return "{}/install/{}".format(root.rstrip("/"), MONGO_DTS_PKG_NAME)


def mongo_dts_unpack_dir(root: str = MONGO_DTS_ROOT) -> str:
    return "{}/pkg".format(root.rstrip("/"))


def _mongo_shell_eval_script(
    ip: str, port: int, dba_user: str, dba_password: str, js: str, connect_uri: str = ""
) -> str:
    if connect_uri:
        target = shlex.quote(connect_uri)
    else:
        target = "--host {} --port {}".format(shlex.quote(ip), int(port))
    # 逐个探测可执行文件，避免 ls 多 glob 在 set -euo pipefail 下因某一个不存在而提前退出。
    return "\n".join(
        [
            "set -euo pipefail",
            'MONGO_BIN=""',
            "if command -v mongosh >/dev/null 2>&1; then MONGO_BIN=$(command -v mongosh)",
            "elif command -v mongo >/dev/null 2>&1; then MONGO_BIN=$(command -v mongo)",
            "else",
            "  for d in /usr/local/mongodb*; do",
            '    [ -d "$d/bin" ] || continue',
            '    if [ -x "$d/bin/mongosh" ]; then MONGO_BIN="$d/bin/mongosh"; break; fi',
            '    if [ -x "$d/bin/mongo" ]; then MONGO_BIN="$d/bin/mongo"; break; fi',
            "  done",
            "fi",
            'if [ -z "$MONGO_BIN" ]; then echo "mongo shell not found"; exit 1; fi',
            '"$MONGO_BIN" {target} -u {dba_user} -p {dba_pwd} --authenticationDatabase admin --quiet --eval {js}'.format(
                target=target,
                dba_user=shlex.quote(dba_user),
                dba_pwd=shlex.quote(dba_password),
                js=shlex.quote(js),
            ),
            "",
        ]
    )


def create_user_script(
    ip: str,
    port: int,
    dba_user: str,
    dba_password: str,
    user: str,
    password: str,
    roles_js: str,
    connect_uri: str = "",
) -> str:
    js = (
        "var admin=db.getSiblingDB('admin');"
        "try{{admin.dropUser({user!r})}}catch(e){{}}"
        "admin.createUser({{user:{user!r},pwd:{pwd!r},roles:{roles}}});"
    ).format(user=user, pwd=password, roles=roles_js)
    return _mongo_shell_eval_script(ip, port, dba_user, dba_password, js, connect_uri=connect_uri)


def start_collector_script(work_dir: str, conf_text: str) -> str:
    if "\nCOLLECTOR_CONF_END\n" in "\n" + conf_text:
        raise ValueError("collector conf contains the heredoc terminator")
    pkg = shlex.quote(mongo_dts_pkg_path())
    # Unpack under the task work dir so concurrent DTS jobs on one JobHost do not clash.
    unpack = shlex.quote("{}/pkg".format(work_dir.rstrip("/")))
    work = shlex.quote(work_dir)
    bin_name = shlex.quote(MONGOSHAKE_BIN_NAME)
    return "\n".join(
        [
            "set -euo pipefail",
            "test -f {pkg}".format(pkg=pkg),
            "rm -rf {unpack}".format(unpack=unpack),
            "mkdir -p {unpack} {work}/logs".format(unpack=unpack, work=work),
            "tar -xzf {pkg} -C {unpack}".format(pkg=pkg, unpack=unpack),
            "bin=$(find {unpack} -type f -name {bin_name} | head -1)".format(unpack=unpack, bin_name=bin_name),
            'if [ -z "$bin" ]; then echo "collector.linux not found in mongo-dts.tar.gz"; exit 1; fi',
            'chmod +x "$bin"',
            "cat > {work}/collector.conf << 'COLLECTOR_CONF_END'".format(work=work),
            conf_text.rstrip("\n"),
            "COLLECTOR_CONF_END",
            "chmod 600 {work}/collector.conf".format(work=work),
            "if [ -f {work}/collector.pid ] && kill -0 $(cat {work}/collector.pid) 2>/dev/null; then".format(
                work=work
            ),
            '  echo "collector already running"; exit 1',
            "fi",
            'nohup "$bin" -conf={work}/collector.conf >> {work}/collector.stdout 2>&1 &'.format(work=work),
            "echo $! > {work}/collector.pid".format(work=work),
            "sleep 1",
            "kill -0 $(cat {work}/collector.pid)".format(work=work),
            "",
        ]
    )


def drop_user_script(ip: str, port: int, dba_user: str, dba_password: str, user: str, connect_uri: str = "") -> str:
    js = "var admin=db.getSiblingDB('admin'); try{{admin.dropUser({user!r})}}catch(e){{}}".format(user=user)
    return _mongo_shell_eval_script(ip, port, dba_user, dba_password, js, connect_uri=connect_uri)


def wait_and_stop_script(
    work_dir: str,
    full_port: int,
    incr_port: int,
    lag_seconds: int = CATCHUP_LAG_SECONDS,
    stable_rounds: int = CATCHUP_STABLE_ROUNDS,
    poll_seconds: int = CATCHUP_POLL_SECONDS,
    deadline_seconds: int = 82800,
) -> str:
    """全量到 100% 后，增量延迟连续落在阈值内就停掉 collector。"""
    # Embed mongoshake_catchup_watcher.py (ASCII-only) so JobHost need not have the file.
    return "\n".join(
        [
            "set -euo pipefail",
            "command -v python3 >/dev/null",
            "python3 - {work} {full_port} {incr_port} {lag} {stable} {poll} {deadline} << 'PY'".format(
                work=shlex.quote(work_dir),
                full_port=int(full_port),
                incr_port=int(incr_port),
                lag=int(lag_seconds),
                stable=int(stable_rounds),
                poll=int(poll_seconds),
                deadline=int(deadline_seconds),
            ),
            _catchup_watcher_source().rstrip("\n"),
            "PY",
            "",
        ]
    )
