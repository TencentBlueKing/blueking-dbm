# -*- coding: utf-8 -*-
import pytest

from backend.flow.utils.mongodb.mongoshake_conf import (
    MONGO_CONNECT_STANDALONE,
    SOURCE_CONNECT_BACKUP,
    SOURCE_CONNECT_SECONDARY_PREFERRED,
    STOP_MODE_AUTO,
    STOP_MODE_MANUAL,
    assert_balancer_stopped_script,
    assert_mongoshake_supported_version,
    build_collector_conf,
    collector_http_ports,
    create_user_script,
    mongo_uri,
    namespace_list,
    normalize_source_connect_mode,
    normalize_stop_mode,
    replica_set_connect_uri,
    resolve_source_connect,
)

TEST_USER = "xxxx"
TEST_PASSWORD = "xxxx"


def _test_mongo_uri(addrs, direct_connection=False):
    return mongo_uri(TEST_USER, TEST_PASSWORD, addrs, direct_connection=direct_connection)


def test_sharded_source_reads_backups_and_checkpoint_on_target():
    source_urls = ";".join(
        (
            _test_mongo_uri(["127.0.0.1:27017"], direct_connection=True),
            _test_mongo_uri(["127.0.0.2:27017"], direct_connection=True),
        )
    )
    source_config_url = _test_mongo_uri(["127.0.0.3:27019"], direct_connection=True)
    target_url = _test_mongo_uri(["127.0.0.2:27021"])
    conf = build_collector_conf(
        collector_id="mongodts1",
        log_dir="/data/mongoshake/mongodts1/logs",
        source_urls=source_urls,
        source_mongos_url="",
        source_config_url=source_config_url,
        target_url=target_url,
        namespace_white="app.orders;logs",
        transform_namespace="app:app_new",
        filter_orphan_document=True,
    )
    assert "sync_mode = all" in conf
    assert "incr_sync.mongo_fetch_method = oplog" in conf
    assert "full_sync.collection_exist_drop = false" in conf
    assert "full_sync.executor.filter.orphan_document = true" in conf
    assert "full_sync.do_not_shard_destination = false" in conf
    assert "filter.ddl_enable = false" in conf
    assert "mongo_urls = {}".format(source_urls) in conf
    assert "mongo_cs_url = {}".format(source_config_url) in conf
    assert "mongo_s_url = \n" in conf
    assert "mongo_connect_mode = secondaryPreferred" in conf
    assert "checkpoint.storage.url = {}".format(target_url) in conf
    assert "filter.namespace.white = app.orders;logs" in conf
    assert "transform.namespace = app:app_new" in conf
    assert "full_sync.http_port = -1" in conf


def test_replica_source_uses_member_urls():
    source_urls = _test_mongo_uri(["127.0.0.3:27017", "127.0.0.4:27017"])
    conf = build_collector_conf(
        collector_id="mongodts2",
        log_dir="/data/mongoshake/mongodts2/logs",
        source_urls=source_urls,
        source_mongos_url="",
        target_url=_test_mongo_uri(["127.0.0.5:27017"]),
    )
    assert "mongo_urls = {}".format(source_urls) in conf
    assert "mongo_s_url = \n" in conf or "mongo_s_url = \n" in conf
    assert "mongo_connect_mode = secondaryPreferred" in conf


def test_build_conf_standalone_for_backup_node():
    source_urls = _test_mongo_uri(["127.0.0.9:27017"])
    conf = build_collector_conf(
        collector_id="mongodts_bk",
        log_dir="/data/mongoshake/mongodts_bk/logs",
        source_urls=source_urls,
        source_mongos_url="",
        target_url=_test_mongo_uri(["127.0.0.5:27017"]),
        mongo_connect_mode=MONGO_CONNECT_STANDALONE,
    )
    assert "mongo_urls = {}".format(source_urls) in conf
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


def test_resolve_source_connect_backup_uses_direct_uri():
    urls, mongos, config, mode = resolve_source_connect(
        SOURCE_CONNECT_BACKUP,
        TEST_USER,
        TEST_PASSWORD,
        is_sharded=False,
        member_addrs=["127.0.0.3:27017", "127.0.0.9:27017"],
        backup_addr="127.0.0.9:27017",
        cluster_name="rs1",
    )
    assert urls == _test_mongo_uri(["127.0.0.9:27017"], direct_connection=True)
    assert mongos == ""
    assert config == ""
    assert mode == SOURCE_CONNECT_SECONDARY_PREFERRED


def test_resolve_source_connect_backup_requires_backup_member():
    with pytest.raises(ValueError, match="no MONGO_BACKUP"):
        resolve_source_connect(
            SOURCE_CONNECT_BACKUP,
            TEST_USER,
            TEST_PASSWORD,
            is_sharded=False,
            member_addrs=["127.0.0.3:27017"],
            backup_addr=None,
            cluster_name="rs1",
        )


def test_resolve_sharded_source_uses_shard_and_config_backups():
    urls, mongos, config, mode = resolve_source_connect(
        SOURCE_CONNECT_SECONDARY_PREFERRED,
        TEST_USER,
        TEST_PASSWORD,
        is_sharded=True,
        shard_backup_addrs=["127.0.0.3:27017", "127.0.0.4:27017"],
        config_backup_addr="127.0.0.5:27019",
        cluster_name="sh1",
    )
    assert urls == ";".join(
        (
            _test_mongo_uri(["127.0.0.3:27017"], direct_connection=True),
            _test_mongo_uri(["127.0.0.4:27017"], direct_connection=True),
        )
    )
    assert mongos == ""
    assert config == _test_mongo_uri(["127.0.0.5:27019"], direct_connection=True)
    assert mode == SOURCE_CONNECT_SECONDARY_PREFERRED


def test_resolve_sharded_source_requires_every_backup_group():
    with pytest.raises(ValueError, match="configsvr MONGO_BACKUP"):
        resolve_source_connect(
            SOURCE_CONNECT_BACKUP,
            TEST_USER,
            TEST_PASSWORD,
            is_sharded=True,
            shard_backup_addrs=["127.0.0.3:27017"],
            config_backup_addr=None,
            cluster_name="sh1",
        )


def test_dts_sharded_source_requires_multiple_shard_backups():
    from backend.flow.engine.bamboo.scene.mongodb.mongodb_dts import MongoDBDtsFlow

    class Node:
        def __init__(self, ip, port):
            self.ip = ip
            self.port = port

        def addr(self):
            return "{}:{}".format(self.ip, self.port)

    class ReplicaSet:
        def __init__(self, name, backup):
            self.set_name = name
            self.backup = backup

        def get_backup_node(self):
            return self.backup

    class Cluster:
        name = "sh1"

        def __init__(self, shards):
            self.shards = shards
            self.config = ReplicaSet("cfg", Node("127.0.0.5", 27019))

        @staticmethod
        def is_sharded_cluster():
            return True

        def get_shards(self, **_kwargs):
            return self.shards

        def get_config(self):
            return self.config

    shards = [
        ReplicaSet("shard1", Node("127.0.0.3", 27017)),
        ReplicaSet("shard2", Node("127.0.0.4", 27017)),
    ]
    urls, mongos, config, mode = MongoDBDtsFlow._source_addrs(
        Cluster(shards), "xxxx", "xxxx", SOURCE_CONNECT_SECONDARY_PREFERRED
    )
    assert "127.0.0.3:27017/?directConnection=true" in urls
    assert "127.0.0.4:27017/?directConnection=true" in urls
    assert mongos == ""
    assert "127.0.0.5:27019/?directConnection=true" in config
    assert mode == SOURCE_CONNECT_SECONDARY_PREFERRED

    with pytest.raises(ValueError, match="at least two shards"):
        MongoDBDtsFlow._source_addrs(Cluster(shards[:1]), "xxxx", "xxxx", SOURCE_CONNECT_SECONDARY_PREFERRED)


def test_namespace_rejects_regex():
    with pytest.raises(ValueError):
        namespace_list(["app.*"])


def test_password_at_is_rejected():
    with pytest.raises(ValueError):
        mongo_uri("user", "a@b", ["127.0.0.1:27017"])


def test_conf_sets_collector_http_ports():
    full_port, incr_port = collector_http_ports("mongodts1")
    conf = build_collector_conf(
        collector_id="mongodts1",
        log_dir="/data/mongoshake/mongodts1/logs",
        source_urls=_test_mongo_uri(["127.0.0.3:27017"]),
        source_mongos_url="",
        target_url=_test_mongo_uri(["127.0.0.5:27017"]),
        full_http_port=full_port,
        incr_http_port=incr_port,
    )
    assert "full_sync.http_port = {}".format(full_port) in conf
    assert "incr_sync.http_port = {}".format(incr_port) in conf


def test_check_empty_uses_findone_and_includes_test_db():
    from backend.flow.utils.mongodb.mongoshake_conf import check_empty_target_script

    script = check_empty_target_script("127.0.0.1", 27017, "xxxx", "xxxx")
    assert "countDocuments({})" not in script
    assert "estimatedDocumentCount" not in script
    assert "findOne()" in script
    assert "test:1" not in script
    assert "getCollectionInfos" in script
    assert "getCollectionNames" not in script
    # 未清理的 MongoShake checkpoint 不算目标上的用户数据
    assert 'd.name==="mongoshake"&&c.indexOf("ckpt_")===0' in script


def test_assert_sharded_requires_config_collections():
    from backend.flow.utils.mongodb.mongoshake_conf import assert_target_user_collections_sharded_script

    script = assert_target_user_collections_sharded_script("127.0.0.1", 27017, "xxxx", "xxxx")
    assert "config" in script
    assert "not sharded" in script or "shardCollection" in script


def test_balancer_check_uses_configsvr_status():
    uri = replica_set_connect_uri(["127.0.0.3:27019", "127.0.0.4:27019"], "cfg")
    script = assert_balancer_stopped_script("127.0.0.3", 27019, "xxxx", "xxxx", connect_uri=uri)
    assert "cfg.settings.findOne" in script
    assert "s.stopped" in script and "s.mode" in script
    assert "cfg.migrations.findOne" in script
    assert "cfg.locks.findOne" in script
    assert uri in script


def test_replica_set_connect_uri_includes_members_and_set_name():
    uri = replica_set_connect_uri(["127.0.0.3:27017", "127.0.0.4:27017"], "rs0")
    assert uri == "mongodb://127.0.0.3:27017,127.0.0.4:27017/?replicaSet=rs0"
    script = create_user_script(
        "127.0.0.3",
        27017,
        "xxxx",
        "xxxx",
        "mongodts_src_x",
        "xxxx",
        '[{role:"readAnyDatabase",db:"admin"}]',
        connect_uri=uri,
    )
    assert "mongodb://127.0.0.3:27017,127.0.0.4:27017/?replicaSet=rs0" in script
    assert "--host" not in script
    # shell 探测逐个检查，避免 ls 多 glob + set -e 提前退出
    assert "ls -1 /usr/local/mongodb" not in script
    assert "command -v mongosh >/dev/null 2>&1" in script
    assert 'if [ -x "$d/bin/mongosh" ]' in script


def test_mongoshake_rejects_mongodb_8_and_allows_7():
    assert_mongoshake_supported_version("mongodb-7.0.28")
    with pytest.raises(Exception, match="major version >= 8"):
        assert_mongoshake_supported_version("mongodb-8.0.4")


def test_do_not_shard_destination_for_shard_to_rs():
    from backend.flow.utils.mongodb.mongoshake_conf import build_collector_conf

    conf = build_collector_conf(
        collector_id="mongodts1",
        log_dir="/tmp/logs",
        source_urls=_test_mongo_uri(["127.0.0.1:27017"], direct_connection=True),
        source_mongos_url="",
        source_config_url=_test_mongo_uri(["127.0.0.2:27017"], direct_connection=True),
        target_url=_test_mongo_uri(["127.0.0.3:27017"]),
        filter_orphan_document=True,
        do_not_shard_destination=True,
    )
    assert "full_sync.do_not_shard_destination = true" in conf
    assert "full_sync.executor.filter.orphan_document = true" in conf
