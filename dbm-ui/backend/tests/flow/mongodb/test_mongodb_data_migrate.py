# -*- coding: utf-8 -*-
"""MongoDB 数据迁移：分片配对、版本校验、备份文件选择。"""

import pytest

from backend.db_meta.enums import InstanceRole
from backend.flow.consts import MongoDBClusterRole
from backend.flow.engine.bamboo.scene.mongodb.mongodb_data_migrate import MongoDBDataMigrateFlow
from backend.flow.utils.mongodb.mongodb_repo import MongoNode, ReplicaSet, ReplicaSetCluster, ShardedCluster


def _member(ip, port=27001, role=InstanceRole.MONGO_M1.value):
    return MongoNode(ip, port, role, 0, "mongodb")


def _shard(set_name, ip, set_type=MongoDBClusterRole.ShardSvr.value):
    return ReplicaSet(set_type, set_name=set_name, members=[_member(ip)])


def _sharded(name, cluster_id, shards, major_version="4.4.18"):
    return ShardedCluster(
        bk_cloud_id=0,
        cluster_id=cluster_id,
        name=name,
        major_version=major_version,
        bk_biz_id=3,
        immute_domain="{}.mongodb.db".format(name),
        shards=shards,
        mongos=[MongoNode("127.0.0.100", 27017, MongoDBClusterRole.Mongos.value, 0, "mongos")],
        configsvr=ReplicaSet(
            MongoDBClusterRole.ConfigSvr.value,
            set_name="{}-conf".format(name),
            members=[_member("127.0.0.200", 27019)],
        ),
    )


class TestDataMigratePairs:
    def test_sharded_sources_skip_configsvr(self):
        src = _sharded(
            "src",
            1,
            [
                _shard("src-s20", "127.0.0.1"),
                _shard("src-s3", "127.0.0.2"),
            ],
        )
        dst = _sharded(
            "dst",
            2,
            [
                _shard("dst-s2", "127.0.0.11"),
                _shard("dst-s1", "127.0.0.12"),
            ],
        )
        MongoDBDataMigrateFlow.ensure_same_topology(src, dst)
        sources = MongoDBDataMigrateFlow.iter_source_shards(src)
        assert [src_rs.set_name for src_rs in sources] == ["src-s3", "src-s20"]

    def test_shard_count_can_differ(self):
        src = _sharded("src", 1, [_shard("src-s1", "127.0.0.1"), _shard("src-s2", "127.0.0.2")])
        dst = _sharded("dst", 2, [_shard("dst-s1", "127.0.0.11")])
        MongoDBDataMigrateFlow.ensure_same_topology(src, dst)
        sources = MongoDBDataMigrateFlow.iter_source_shards(src)
        assert [src_rs.set_name for src_rs in sources] == ["src-s1", "src-s2"]

    def test_cluster_mode_sharded_source_dumps_via_mongos(self):
        src = _sharded("src", 1, [_shard("src-s1", "127.0.0.1"), _shard("src-s2", "127.0.0.2")])
        rs = MongoDBDataMigrateFlow.source_mongos_set(src)
        assert rs.set_name == "mongos"
        assert [m.ip for m in rs.members] == ["127.0.0.100"]
        assert MongoDBDataMigrateFlow.pick_exec_node(rs).ip == "127.0.0.100"

    def test_replicaset_pair(self):
        src = ReplicaSetCluster(
            bk_cloud_id=0,
            cluster_id=1,
            name="src-rs",
            major_version="5.0.14",
            bk_biz_id=3,
            immute_domain="src.mongodb.db",
            shard=_shard("src-rs", "127.0.0.1", MongoDBClusterRole.Replicaset.value),
        )
        dst = ReplicaSetCluster(
            bk_cloud_id=0,
            cluster_id=2,
            name="dst-rs",
            major_version="5.0.14",
            bk_biz_id=3,
            immute_domain="dst.mongodb.db",
            shard=_shard("dst-rs", "127.0.0.2", MongoDBClusterRole.Replicaset.value),
        )
        pairs = MongoDBDataMigrateFlow.iter_migrate_pairs(src, dst)
        assert len(pairs) == 1
        assert pairs[0][0].set_name == "src-rs"
        assert pairs[0][1].set_name == "dst-rs"

    def test_reject_lower_target_version(self):
        src = ReplicaSetCluster(
            bk_cloud_id=0,
            cluster_id=1,
            name="src-rs",
            major_version="5.0.14",
            bk_biz_id=3,
            immute_domain="src.mongodb.db",
            shard=_shard("src-rs", "127.0.0.1", MongoDBClusterRole.Replicaset.value),
        )
        dst = ReplicaSetCluster(
            bk_cloud_id=0,
            cluster_id=2,
            name="dst-rs",
            major_version="4.4.18",
            bk_biz_id=3,
            immute_domain="dst.mongodb.db",
            shard=_shard("dst-rs", "127.0.0.2", MongoDBClusterRole.Replicaset.value),
        )
        with pytest.raises(Exception, match="lower than source"):
            MongoDBDataMigrateFlow.ensure_same_topology(src, dst)

    def test_prefixed_package_version_is_accepted(self):
        src = ReplicaSetCluster(
            bk_cloud_id=0,
            cluster_id=1,
            name="src-rs",
            major_version="mongodb-7.0.28",
            bk_biz_id=3,
            immute_domain="src.mongodb.db",
            shard=_shard("src-rs", "127.0.0.1", MongoDBClusterRole.Replicaset.value),
        )
        dst = ReplicaSetCluster(
            bk_cloud_id=0,
            cluster_id=2,
            name="dst-rs",
            major_version="mongodb-7.0.28",
            bk_biz_id=3,
            immute_domain="dst.mongodb.db",
            shard=_shard("dst-rs", "127.0.0.2", MongoDBClusterRole.Replicaset.value),
        )
        MongoDBDataMigrateFlow.ensure_same_topology(src, dst)

    def test_sharded_to_replicaset_is_allowed(self):
        src = _sharded("src", 1, [_shard("src-s1", "127.0.0.1"), _shard("src-s2", "127.0.0.2")])
        dst = ReplicaSetCluster(
            bk_cloud_id=0,
            cluster_id=2,
            name="dst-rs",
            major_version="5.0.14",
            bk_biz_id=3,
            immute_domain="dst.mongodb.db",
            shard=_shard("dst-rs", "127.0.0.3", MongoDBClusterRole.Replicaset.value),
        )
        MongoDBDataMigrateFlow.ensure_same_topology(src, dst)

    def test_replicaset_to_sharded_is_allowed(self):
        src = ReplicaSetCluster(
            bk_cloud_id=0,
            cluster_id=1,
            name="src-rs",
            major_version="5.0.14",
            bk_biz_id=3,
            immute_domain="src.mongodb.db",
            shard=_shard("src-rs", "127.0.0.1", MongoDBClusterRole.Replicaset.value),
        )
        dst = _sharded("dst", 2, [_shard("dst-s1", "127.0.0.11")], major_version="5.0.14")
        MongoDBDataMigrateFlow.ensure_same_topology(src, dst)

    def test_replicaset_to_lower_version_sharded_rejected(self):
        src = ReplicaSetCluster(
            bk_cloud_id=0,
            cluster_id=1,
            name="src-rs",
            major_version="5.0.14",
            bk_biz_id=3,
            immute_domain="src.mongodb.db",
            shard=_shard("src-rs", "127.0.0.1", MongoDBClusterRole.Replicaset.value),
        )
        dst = _sharded("dst", 2, [_shard("dst-s1", "127.0.0.11")], major_version="4.4.18")
        with pytest.raises(Exception, match="lower than source"):
            MongoDBDataMigrateFlow.ensure_same_topology(src, dst)


class TestPickBackupFiles:
    def test_pick_latest_non_empty_per_set(self):
        logs = [
            {"set_name": "s1", "bs_taskid": "old", "file_name": "a.tar", "end_time": "2026-01-01T00:00:00"},
            {
                "set_name": "s1",
                "bs_taskid": "empty",
                "file_name": "empty.tar",
                "end_time": "2026-02-01T00:00:00",
                "is_empty_backup": 1,
            },
            {"set_name": "s1", "bs_taskid": "new", "file_name": "b.tar", "end_time": "2026-01-15T00:00:00"},
            {"set_name": "conf", "bs_taskid": "c1", "file_name": "c.tar", "end_time": "2026-01-01T00:00:00"},
        ]
        picked = MongoDBDataMigrateFlow.pick_backup_files(logs, ["s1", "conf"])
        assert picked["s1"] == {"task_id": "new", "file_name": "b.tar"}
        assert picked["conf"]["task_id"] == "c1"

    def test_missing_set(self):
        with pytest.raises(Exception, match="missing for set_name"):
            MongoDBDataMigrateFlow.pick_backup_files([], ["s1"])

    def test_all_empty_backups_raise(self):
        logs = [
            {
                "set_name": "s1",
                "bs_taskid": "empty",
                "file_name": "empty.tar",
                "end_time": "2026-02-01T00:00:00",
                "is_empty_backup": 1,
            },
        ]
        with pytest.raises(Exception, match="all backups are empty"):
            MongoDBDataMigrateFlow.pick_backup_files(logs, ["s1"])


class TestUserDataNsFilter:
    def test_default_drops_cluster_metadata_dbs(self):
        ns_filter = MongoDBDataMigrateFlow.user_data_ns_filter(None)
        assert ns_filter["db_patterns"] == ["*"]
        assert set(ns_filter["ignore_dbs"]) == {"admin", "config", "local"}

    def test_keeps_caller_ignore_and_adds_system_dbs(self):
        ns_filter = MongoDBDataMigrateFlow.user_data_ns_filter(
            {
                "db_patterns": ["app*"],
                "table_patterns": ["*"],
                "ignore_dbs": ["app_tmp"],
                "ignore_tables": [],
            }
        )
        assert ns_filter["db_patterns"] == ["app*"]
        assert "app_tmp" in ns_filter["ignore_dbs"]
        assert "config" in ns_filter["ignore_dbs"]


class TestArchiveName:
    def test_sanitize(self):
        name = MongoDBDataMigrateFlow.archive_base_name("root/1", "set name")
        assert "/" not in name
        assert " " not in name
        assert name.startswith("migrate-")

    def test_exec_node_skips_backup_role(self):
        rs = ReplicaSet(
            MongoDBClusterRole.ShardSvr.value,
            set_name="s1",
            members=[
                _member("127.0.0.1", role=InstanceRole.MONGO_BACKUP.value),
                _member("127.0.0.2", role=InstanceRole.MONGO_M1.value),
            ],
        )
        assert MongoDBDataMigrateFlow.pick_exec_node(rs).ip == "127.0.0.2"
