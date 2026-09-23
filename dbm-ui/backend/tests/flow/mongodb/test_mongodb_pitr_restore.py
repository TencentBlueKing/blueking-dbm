# -*- coding: utf-8 -*-
"""MongoDB PITR 回档：源shard与临时shard的配对一致性测试."""

import pytest

from backend.db_meta.enums import InstanceRole
from backend.flow.consts import MongoDBClusterRole
from backend.flow.engine.bamboo.scene.mongodb.mongodb_pitr_restore import MongoPitrRestoreFlow
from backend.flow.utils.mongodb.mongodb_repo import MongoNode, ReplicaSet, ShardedCluster


def _member(ip, port=27001, role=InstanceRole.MONGO_M1.value):
    return MongoNode(ip, port, role, 0, "mongodb")


def _shard(set_name, ip):
    return ReplicaSet(MongoDBClusterRole.ShardSvr.value, set_name=set_name, members=[_member(ip)])


def _cluster(name, shards):
    return ShardedCluster(
        bk_cloud_id=0,
        cluster_id=1001,
        name=name,
        major_version="4.4.18",
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


def _scaled_out_src_cluster():
    """扩容过的源集群：nosqlstoragesetdtl 主键序不是编号序"""
    return _cluster(
        "src",
        [
            _shard("src-s20", "127.0.0.1"),
            _shard("src-s50", "127.0.0.2"),
            _shard("src-s24", "127.0.0.3"),
            _shard("src-s3", "127.0.0.4"),
        ],
    )


def _fresh_tmp_cluster():
    """临时集群一次部署，编号连续"""
    return _cluster(
        "tmp",
        [
            _shard("tmp-s1", "127.0.1.1"),
            _shard("tmp-s2", "127.0.1.2"),
            _shard("tmp-s3", "127.0.1.3"),
            _shard("tmp-s4", "127.0.1.4"),
        ],
    )


class TestPitrShardMap:
    def test_shard_map_pairs_by_set_name_order(self):
        src, dst = _scaled_out_src_cluster(), _fresh_tmp_cluster()
        shard_map = MongoPitrRestoreFlow.build_shard_map(
            src.get_shards(with_config=False, sort_by_set_name=True),
            dst.get_shards(with_config=False, sort_by_set_name=True),
        )

        assert shard_map == [
            {"src_set_name": "src-s3", "dst_set_name": "tmp-s1"},
            {"src_set_name": "src-s20", "dst_set_name": "tmp-s2"},
            {"src_set_name": "src-s24", "dst_set_name": "tmp-s3"},
            {"src_set_name": "src-s50", "dst_set_name": "tmp-s4"},
        ]

    def test_shard_map_differs_from_cmdb_index_zip(self):
        """CMDB列表下标zip会把 src-s20 绑到 tmp-s1，而回档实际把 src-s3 灌到 tmp-s1"""
        src, dst = _scaled_out_src_cluster(), _fresh_tmp_cluster()
        index_zip = [{"src_set_name": s.set_name, "dst_set_name": d.set_name} for s, d in zip(src.shards, dst.shards)]
        shard_map = MongoPitrRestoreFlow.build_shard_map(
            src.get_shards(with_config=False, sort_by_set_name=True),
            dst.get_shards(with_config=False, sort_by_set_name=True),
        )
        assert shard_map != index_zip

    def test_shard_map_matches_restore_and_identity_pairing(self):
        """与 process_cluster 灌备份、rebuild_cluster 写shardIdentity 用的是同一份配对"""
        src, dst = _scaled_out_src_cluster(), _fresh_tmp_cluster()
        # process_cluster 带configsvr，rebuild_cluster的shardsvr循环不带
        restore_pairs = [
            (s.set_name, d.set_name)
            for s, d in zip(
                src.get_shards(with_config=True, sort_by_set_name=True),
                dst.get_shards(with_config=True, sort_by_set_name=True),
            )
            if s.set_type != MongoDBClusterRole.ConfigSvr.value
        ]
        shard_map = MongoPitrRestoreFlow.build_shard_map(
            src.get_shards(with_config=False, sort_by_set_name=True),
            dst.get_shards(with_config=False, sort_by_set_name=True),
        )

        assert [(m["src_set_name"], m["dst_set_name"]) for m in shard_map] == restore_pairs

    def test_cluster_json_shards_are_sorted(self):
        """下发给actuator的payload也必须是排序后的，避免老逻辑按下标推导时错位"""
        src = _scaled_out_src_cluster()
        assert [s["set_name"] for s in src.__json__()["shards"]] == ["src-s3", "src-s20", "src-s24", "src-s50"]

    @pytest.mark.parametrize(
        "names,expected",
        [
            # 带编号：按编号数值排，不是字典序
            (["c-s20", "c-s50", "c-s24", "c-s3"], ["c-s3", "c-s20", "c-s24", "c-s50"]),
            # 现网存在的不带编号名字：编号一律取0，用名字兜底，不依赖CMDB行序
            (["c-shard-c", "c-shard-a", "c-shard-b"], ["c-shard-a", "c-shard-b", "c-shard-c"]),
            # 编号与不带编号混用
            (["c-s2", "c-backup", "c-s1", "c-archive"], ["c-archive", "c-backup", "c-s1", "c-s2"]),
            # 超长数字后缀不能溢出
            (["c-s99999999999999999999", "c-s2", "c-s1"], ["c-s1", "c-s2", "c-s99999999999999999999"]),
        ],
    )
    def test_sort_by_set_name_is_deterministic(self, names, expected):
        """排序键必须与 actuator 的 compareShardSetName 完全一致"""
        cluster = _cluster("c", [_shard(n, "127.0.0.1") for n in names])
        assert [s.set_name for s in cluster.get_shards(sort_by_set_name=True)] == expected

    def test_unnumbered_shard_names_pair_consistently(self):
        """shard名不带编号时，shard_map 仍要与灌备份/identity 的配对一致"""
        src = _cluster("src", [_shard(n, "127.0.0.1") for n in ["src-shard-b", "src-shard-a", "src-s2"]])
        dst = _cluster("tmp", [_shard(n, "127.0.1.1") for n in ["tmp-s3", "tmp-s1", "tmp-s2"]])

        shard_map = MongoPitrRestoreFlow.build_shard_map(
            src.get_shards(with_config=False, sort_by_set_name=True),
            dst.get_shards(with_config=False, sort_by_set_name=True),
        )
        restore_pairs = [
            (s.set_name, d.set_name)
            for s, d in zip(
                src.get_shards(with_config=True, sort_by_set_name=True),
                dst.get_shards(with_config=True, sort_by_set_name=True),
            )
            if s.set_type != MongoDBClusterRole.ConfigSvr.value
        ]

        assert [(m["src_set_name"], m["dst_set_name"]) for m in shard_map] == restore_pairs
        assert [(m["src_set_name"], m["dst_set_name"]) for m in shard_map] == [
            ("src-shard-a", "tmp-s1"),
            ("src-shard-b", "tmp-s2"),
            ("src-s2", "tmp-s3"),
        ]

    def test_shard_count_mismatch_rejected(self):
        src, dst = _scaled_out_src_cluster(), _fresh_tmp_cluster()
        with pytest.raises(Exception, match="different shards"):
            MongoPitrRestoreFlow.build_shard_map(
                src.get_shards(with_config=False, sort_by_set_name=True),
                dst.get_shards(with_config=False, sort_by_set_name=True)[:3],
            )
