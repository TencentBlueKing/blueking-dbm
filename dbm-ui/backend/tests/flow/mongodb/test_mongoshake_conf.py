# -*- coding: utf-8 -*-
from types import SimpleNamespace

import pytest

from backend.flow.utils.mongodb.mongoshake_conf import (
    MONGO_CONNECT_STANDALONE,
    SOURCE_CONNECT_BACKUP,
    SOURCE_CONNECT_SECONDARY_PREFERRED,
    STOP_MODE_AUTO,
    STOP_MODE_MANUAL,
    assert_mongoshake_supported_version,
    build_collector_conf,
    collector_http_ports,
    create_user_script,
    dts_host_from_extension,
    mongo_uri,
    namespace_list,
    normalize_source_connect_mode,
    normalize_stop_mode,
    repl_caught_up,
    replica_set_connect_uri,
    resolve_source_connect,
    start_collector_script,
    stop_collector_script,
    wait_and_stop_script,
)


def test_sharded_source_reads_mongos_and_checkpoint_on_target():
    conf = build_collector_conf(
        collector_id="mongodts1",
        log_dir="/data/mongoshake/mongodts1/logs",
        source_urls="",
        source_mongos_url="mongodb://src:pw@192.168.0.1:27021",
        target_url="mongodb://dst:pw@192.168.0.2:27021",
        namespace_white="app.orders;logs",
        transform_namespace="app:app_new",
    )
    assert "sync_mode = all" in conf
    assert "incr_sync.mongo_fetch_method = change_stream" in conf
    assert "full_sync.collection_exist_drop = false" in conf
    assert "filter.ddl_enable = false" in conf
    assert "mongo_urls = \n" in conf or conf.endswith("mongo_urls = ") or "mongo_urls = \n" in conf
    assert "mongo_s_url = mongodb://src:pw@192.168.0.1:27021" in conf
    assert "checkpoint.storage.url = mongodb://dst:pw@192.168.0.2:27021" in conf
    assert "filter.namespace.white = app.orders;logs" in conf
    assert "transform.namespace = app:app_new" in conf
    assert "full_sync.http_port = -1" in conf


def test_replica_source_uses_member_urls():
    conf = build_collector_conf(
        collector_id="mongodts2",
        log_dir="/data/mongoshake/mongodts2/logs",
        source_urls="mongodb://src:pw@192.168.0.3:27017,192.168.0.4:27017",
        source_mongos_url="",
        target_url="mongodb://dst:pw@192.168.0.5:27017",
    )
    assert "mongo_urls = mongodb://src:pw@192.168.0.3:27017,192.168.0.4:27017" in conf
    assert "mongo_s_url = \n" in conf or "mongo_s_url = \n" in conf
    assert "mongo_connect_mode = secondaryPreferred" in conf


def test_build_conf_standalone_for_backup_node():
    conf = build_collector_conf(
        collector_id="mongodts_bk",
        log_dir="/data/mongoshake/mongodts_bk/logs",
        source_urls="mongodb://src:pw@192.168.0.9:27017",
        source_mongos_url="",
        target_url="mongodb://dst:pw@192.168.0.5:27017",
        mongo_connect_mode=MONGO_CONNECT_STANDALONE,
    )
    assert "mongo_urls = mongodb://src:pw@192.168.0.9:27017" in conf
    assert "mongo_connect_mode = standalone" in conf


def test_normalize_source_connect_mode():
    assert normalize_source_connect_mode(None) == SOURCE_CONNECT_SECONDARY_PREFERRED
    assert normalize_source_connect_mode("backup") == SOURCE_CONNECT_BACKUP
    with pytest.raises(ValueError):
        normalize_source_connect_mode("primary")


def test_normalize_stop_mode():
    assert normalize_stop_mode(None) == STOP_MODE_AUTO
    assert normalize_stop_mode("manual") == STOP_MODE_MANUAL
    with pytest.raises(ValueError):
        normalize_stop_mode("force")


def test_stop_collector_script_uses_pid():
    script = stop_collector_script("/data/mongo-dts/mongodts1")
    assert "collector.pid" in script
    assert "kill -9" in script


def test_resolve_source_connect_backup_uses_standalone():
    urls, mongos, mode = resolve_source_connect(
        SOURCE_CONNECT_BACKUP,
        "u",
        "p",
        is_sharded=False,
        member_addrs=["192.168.0.3:27017", "192.168.0.9:27017"],
        backup_addr="192.168.0.9:27017",
        cluster_name="rs1",
    )
    assert urls == "mongodb://u:p@192.168.0.9:27017"
    assert mongos == ""
    assert mode == MONGO_CONNECT_STANDALONE


def test_resolve_source_connect_backup_requires_backup_member():
    with pytest.raises(ValueError, match="no MONGO_BACKUP"):
        resolve_source_connect(
            SOURCE_CONNECT_BACKUP,
            "u",
            "p",
            is_sharded=False,
            member_addrs=["192.168.0.3:27017"],
            backup_addr=None,
            cluster_name="rs1",
        )


def test_namespace_rejects_regex():
    with pytest.raises(ValueError):
        namespace_list(["app.*"])


def test_password_at_is_rejected():
    with pytest.raises(ValueError):
        mongo_uri("user", "a@b", ["192.168.0.1:27017"])


def test_dts_host_requires_registered_ip():
    with pytest.raises(Exception, match="MONGODB_DTS"):
        dts_host_from_extension(SimpleNamespace(details={}))
    host = dts_host_from_extension(SimpleNamespace(details={"ip": "192.168.1.8"}))
    assert host == {"ip": "192.168.1.8"}


def test_repl_caught_up_requires_ack_near_now():
    assert repl_caught_up({"lsn_ack": {"unix": 100}, "now": {"unix": 110}})
    assert not repl_caught_up({"lsn_ack": {"unix": 0}, "now": {"unix": 100}})
    assert not repl_caught_up({"lsn_ack": {"unix": 100}, "now": {"unix": 200}})


def test_wait_script_stops_after_catchup():
    full_port, incr_port = collector_http_ports("mongodts1")
    script = wait_and_stop_script("/data/mongoshake/mongodts1", full_port, incr_port)
    assert "/progress" in script
    assert "/repl" in script
    assert "SIGTERM" in script
    assert str(full_port) in script
    assert str(incr_port) in script
    conf = build_collector_conf(
        collector_id="mongodts1",
        log_dir="/data/mongoshake/mongodts1/logs",
        source_urls="mongodb://src:pw@192.168.0.3:27017",
        source_mongos_url="",
        target_url="mongodb://dst:pw@192.168.0.5:27017",
        full_http_port=full_port,
        incr_http_port=incr_port,
    )
    assert "full_sync.http_port = {}".format(full_port) in conf
    assert "incr_sync.http_port = {}".format(incr_port) in conf


def test_start_script_writes_conf_and_pid():
    script = start_collector_script("/data/mongo-dts/mongodts1", "id = mongodts1\n")
    assert "collector.conf" in script
    assert "collector.pid" in script
    assert "tar -xzf /data/mongo-dts/install/mongo-dts.tar.gz" in script
    assert "collector.linux not found in mongo-dts.tar.gz" in script
    assert "-conf=/data/mongo-dts/mongodts1/collector.conf" in script
    assert "chmod 600 /data/mongo-dts/mongodts1/collector.conf" in script
    assert "rm -rf /data/mongo-dts/mongodts1/pkg" in script
    assert "rm -rf /data/mongo-dts/pkg" not in script


def test_wait_script_requires_ack_after_full():
    script = wait_and_stop_script("/data/mongo-dts/mongodts1", 21000, 21001)
    assert "ack == 0" not in script
    assert "full_done_at" in script
    assert "shutil.rmtree" not in script
    assert "collector.conf" in script
    assert "mongoshake_catchup_watcher" in script or "Require a real incr ack" in script


def test_cleanup_script_only_removes_conf():
    from backend.flow.utils.mongodb.mongoshake_conf import cleanup_dts_work_script

    script = cleanup_dts_work_script("/data/mongo-dts/mongodtsabc")
    assert "rm -f /data/mongo-dts/mongodtsabc/collector.conf" in script
    assert "rm -rf /data/mongo-dts/mongodtsabc" not in script


def test_check_empty_uses_estimated_or_findone():
    from backend.flow.utils.mongodb.mongoshake_conf import check_empty_target_script

    script = check_empty_target_script("192.168.0.1", 27017, "u", "p")
    assert "countDocuments({})" not in script
    assert "estimatedDocumentCount" in script or "findOne" in script
    assert "getCollectionInfos" in script
    assert "getCollectionNames" not in script


def test_assert_sharded_requires_config_collections():
    from backend.flow.utils.mongodb.mongoshake_conf import assert_target_user_collections_sharded_script

    script = assert_target_user_collections_sharded_script("192.168.0.1", 27017, "u", "p")
    assert "config" in script
    assert "not sharded" in script or "shardCollection" in script


def test_catchup_watcher_has_no_future_annotations():
    from pathlib import Path

    # parents: tests/flow/mongodb -> tests/flow -> tests -> backend
    text = (
        Path(__file__)
        .resolve()
        .parents[3]
        .joinpath("flow/utils/mongodb/mongoshake_catchup_watcher.py")
        .read_text(encoding="utf-8")
    )
    assert "from __future__ import annotations" not in text


def test_replica_set_connect_uri_includes_members_and_set_name():
    uri = replica_set_connect_uri(["192.168.0.3:27017", "192.168.0.4:27017"], "rs0")
    assert uri == "mongodb://192.168.0.3:27017,192.168.0.4:27017/?replicaSet=rs0"
    script = create_user_script(
        "192.168.0.3",
        27017,
        "dba",
        "dbapw",
        "mongodts_src_x",
        "pw",
        '[{role:"readAnyDatabase",db:"admin"}]',
        connect_uri=uri,
    )
    assert "mongodb://192.168.0.3:27017,192.168.0.4:27017/?replicaSet=rs0" in script
    assert "--host" not in script
    # shell 探测逐个检查，避免 ls 多 glob + set -e 提前退出
    assert "ls -1 /usr/local/mongodb" not in script
    assert "command -v mongosh >/dev/null 2>&1" in script
    assert 'if [ -x "$d/bin/mongosh" ]' in script


def test_mongoshake_rejects_mongodb_8_and_allows_7():
    assert_mongoshake_supported_version("mongodb-7.0.28")
    with pytest.raises(Exception, match="major version >= 8"):
        assert_mongoshake_supported_version("mongodb-8.0.4")
