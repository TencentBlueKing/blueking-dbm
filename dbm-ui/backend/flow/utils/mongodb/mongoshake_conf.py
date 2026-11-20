# -*- coding: utf-8 -*-
"""MongoShake collector.conf 与目标/源端账号脚本。collector 的启停由 mongo-dbactuator mongoshake_collector 执行。"""

import re
import shlex
import zlib
from urllib.parse import quote

MONGO_DTS_ROOT = "/data/mongo-dts"
MONGO_DTS_PKG_NAME = "mongo-dts.tar.gz"
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


def mongo_uri(user: str, password: str, addrs: list, direct_connection: bool = False) -> str:
    if not addrs:
        raise ValueError("mongo address is empty")
    if "@" in user or "@" in password:
        raise ValueError("MongoShake URL cannot contain @ in user or password")
    uri = "mongodb://{}:{}@{}".format(quote(user, safe=""), quote(password, safe=""), ",".join(addrs))
    if direct_connection:
        uri += "/?directConnection=true"
    return uri


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


def normalize_source_connect_mode(mode: str = None) -> str:
    """infos.source_connect_mode：backup（URI 直连）| secondaryPreferred，默认 secondaryPreferred。"""
    value = (mode or SOURCE_CONNECT_SECONDARY_PREFERRED).strip()
    if value not in SOURCE_CONNECT_MODES:
        raise ValueError("source_connect_mode must be one of {}, got {}".format(SOURCE_CONNECT_MODES, mode))
    return value


def normalize_stop_mode(mode: str = None) -> str:
    """infos.stop_mode：auto（追平后自动停，默认）| manual（追平后人工确认再停）。"""
    value = (mode or STOP_MODE_AUTO).strip()
    if value not in STOP_MODES:
        raise ValueError("stop_mode must be one of {}, got {}".format(STOP_MODES, mode))
    return value


def _iter_user_collection_names_js() -> str:
    """Shared JS snippet: iterate real collections (skip views / system.*) under user dbs."""
    # Use double quotes inside so shlex.quote (single-quoted) keeps type:"collection" intact.
    return (
        "var skip={admin:1,config:1,local:1};"
        "function eachUserColl(fn){"
        "db.adminCommand({listDatabases:1}).databases.forEach(function(d){"
        "if(skip[d.name]){return;}"
        "var dbo=db.getSiblingDB(d.name);"
        'dbo.getCollectionInfos({type:"collection"}).forEach(function(info){'
        "var c=info.name;"
        'if(c.indexOf("system.")===0){return;}'
        # 失败的 DTS 未清理时会留下 MongoShake checkpoint，不算用户数据。
        'if(d.name==="mongoshake"&&c.indexOf("ckpt_")===0){return;}'
        "fn(d.name,c,dbo)})})}"
    )


def check_empty_target_script(ip: str, port: int, dba_user: str, dba_password: str, connect_uri: str = "") -> str:
    """目标用户集合必须无文档。允许已做 enableSharding/shardCollection 的空表（RS→分片场景）。

    test 库可能被迁移，不能整库跳过。用 findOne 看真实文档，不用 estimatedDocumentCount。
    """
    js = (
        _iter_user_collection_names_js()
        + "var bad=[];"
        + "eachUserColl(function(dbn,c,dbo){"
        + "if(dbo.getCollection(c).findOne()){bad.push(dbn+'.'+c)}});"
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


def assert_balancer_stopped_script(ip: str, port: int, dba_user: str, dba_password: str, connect_uri: str = "") -> str:
    """直接连接 configsvr primary，从 config 元数据确认 balancer 已关闭且没有迁移。"""
    js = (
        "var cfg=db.getSiblingDB('config');"
        "var s=cfg.settings.findOne({_id:'balancer'});"
        "if(!s||!(s.stopped===true||s.mode==='off')){"
        "throw new Error('balancer must be explicitly stopped: '+JSON.stringify(s))}"
        "var m=cfg.migrations.findOne();"
        "if(m){throw new Error('active chunk migration found: '+JSON.stringify(m))}"
        "var l=cfg.locks.findOne({_id:'balancer',state:2});"
        "if(l){throw new Error('active balancer lock found: '+JSON.stringify(l))}"
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
    shard_backup_addrs: list = None,
    config_backup_addr: str = None,
    cluster_name: str = "",
):
    """
    返回 (source_urls, source_mongos_url, source_config_url, mongo_connect_mode)。
    分片源固定用 directConnection URI 连接每个 shard/configsvr backup；副本集沿用选点模式。
    """
    mode = normalize_source_connect_mode(source_connect_mode)
    if is_sharded:
        backups = shard_backup_addrs or []
        if not backups:
            raise ValueError("sharded source {} has no shard MONGO_BACKUP members".format(cluster_name or "?"))
        if not config_backup_addr:
            raise ValueError("sharded source {} has no configsvr MONGO_BACKUP member".format(cluster_name or "?"))
        source_urls = ";".join(mongo_uri(user, password, [addr], direct_connection=True) for addr in backups)
        return (
            source_urls,
            "",
            mongo_uri(user, password, [config_backup_addr], direct_connection=True),
            MONGO_CONNECT_SECONDARY_PREFERRED,
        )
    if mode == SOURCE_CONNECT_BACKUP:
        if not backup_addr:
            raise ValueError(
                "source_connect_mode=backup but cluster {} has no MONGO_BACKUP member".format(cluster_name or "?")
            )
        return (
            mongo_uri(user, password, [backup_addr], direct_connection=True),
            "",
            "",
            MONGO_CONNECT_SECONDARY_PREFERRED,
        )
    return mongo_uri(user, password, member_addrs or []), "", "", MONGO_CONNECT_SECONDARY_PREFERRED


def build_collector_conf(
    collector_id: str,
    log_dir: str,
    source_urls: str,
    source_mongos_url: str,
    target_url: str,
    source_config_url: str = "",
    namespace_white: str = "",
    transform_namespace: str = "",
    full_http_port: int = -1,
    incr_http_port: int = -1,
    mongo_connect_mode: str = MONGO_CONNECT_SECONDARY_PREFERRED,
    filter_orphan_document: bool = False,
    do_not_shard_destination: bool = False,
) -> str:
    """oplog + 全量增量。checkpoint 写到目标 mongoshake 库，不写源业务库。"""
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
        "mongo_cs_url = {}".format(source_config_url),
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
        "full_sync.executor.filter.orphan_document = {}".format(str(bool(filter_orphan_document)).lower()),
        "full_sync.do_not_shard_destination = {}".format(str(bool(do_not_shard_destination)).lower()),
        "incr_sync.mongo_fetch_method = oplog",
        "",
    ]
    return "\n".join(lines)


def mongo_dts_pkg_path(root: str = MONGO_DTS_ROOT) -> str:
    """SendMedia 把 mongo-dts.tar.gz 落到 root/install/。"""
    return "{}/install/{}".format(root.rstrip("/"), MONGO_DTS_PKG_NAME)


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


def drop_user_script(ip: str, port: int, dba_user: str, dba_password: str, user: str, connect_uri: str = "") -> str:
    js = "var admin=db.getSiblingDB('admin'); admin.dropUser({user!r});".format(user=user)
    return _mongo_shell_eval_script(ip, port, dba_user, dba_password, js, connect_uri=connect_uri)
