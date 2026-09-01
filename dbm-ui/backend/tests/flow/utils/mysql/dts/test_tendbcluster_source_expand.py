# -*- coding: utf-8 -*-
"""TenDBCluster 源分片 helper 单测（不挂现网 HA 单据 / build_migrate_plan）。"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.utils.mysql.dts.backup_helper import resolve_dest_worker_ip
from backend.flow.utils.mysql.dts.constants import FullLoadEngine, MigrateTopology
from backend.flow.utils.mysql.dts.migrate_helper import (
    assign_source_workers,
    build_create_source_request,
    expand_tendbcluster_source_specs,
)
from backend.flow.utils.mysql.dts.migrate_plan import (
    DtsMigratePlan,
    DtsTaskConfig,
    MyloaderSpec,
    SourceSpec,
    SyncScope,
)


def _make_shard(shard_id: int, instance_id: int):
    slave = MagicMock()
    slave.id = instance_id
    slave.is_stand_by = True
    slave.machine.ip = f"127.0.0.{10 + shard_id}"
    slave.port = 3306
    master = MagicMock()
    master.id = instance_id + 100
    master.machine.ip = f"127.0.0.{20 + shard_id}"
    master.port = 3306
    tuple_obj = MagicMock()
    tuple_obj.receiver = slave
    tuple_obj.ejector = master
    shard = MagicMock()
    shard.shard_id = shard_id
    shard.storage_instance_tuple = tuple_obj
    return shard


class ExpandTendbclusterSourceTest(SimpleTestCase):
    @patch("backend.flow.utils.mysql.dts.migrate_helper.Cluster.objects.get")
    def test_expand_four_shards(self, mock_get):
        cluster = MagicMock()
        cluster.id = 100
        cluster.cluster_type = ClusterType.TenDBCluster.value
        cluster.immute_domain = "spider.db.test"
        shards = [_make_shard(i, 1000 + i) for i in range(4)]
        cluster.tendbclusterstorageset_set.all.return_value.order_by.return_value = shards
        mock_get.return_value = cluster

        base = SourceSpec(cluster_id=100, source_name="remote", sync_scope=SyncScope())
        task_cfg = DtsTaskConfig(
            full_load_engine=FullLoadEngine.MYLOADER.value, myloader=MyloaderSpec(backup_id="bk-1")
        )
        expanded = expand_tendbcluster_source_specs(base, task_cfg=task_cfg)

        self.assertEqual(len(expanded), 4)
        self.assertEqual([s.shard_index for s in expanded], [0, 1, 2, 3])
        self.assertEqual(expanded[0].shard_count, 4)
        self.assertEqual(expanded[0].spider_cluster_id, "spider.db.test")
        self.assertEqual(expanded[0].source_name, "remote-0")
        self.assertEqual(expanded[0].source_instance_id, 1100)
        self.assertEqual(expanded[2].myloader.shard_id, 2)
        self.assertEqual(expanded[2].myloader.backup_id, "bk-1")

    @patch("backend.flow.utils.mysql.dts.migrate_helper.Cluster.objects.get")
    def test_expand_honors_remote_slave_role(self, mock_get):
        cluster = MagicMock()
        cluster.id = 100
        cluster.cluster_type = ClusterType.TenDBCluster.value
        cluster.immute_domain = "spider.db.test"
        cluster.tendbclusterstorageset_set.all.return_value.order_by.return_value = [_make_shard(0, 1000)]
        mock_get.return_value = cluster

        base = SourceSpec(
            cluster_id=100,
            source_name="remote",
            sync_scope=SyncScope(),
            source_instance_role=InstanceRole.REMOTE_SLAVE.value,
        )
        expanded = expand_tendbcluster_source_specs(base)
        self.assertEqual(expanded[0].source_instance_id, 1000)

    @patch("backend.flow.utils.mysql.dts.migrate_helper.Cluster.objects.get")
    def test_expand_without_ejector_fails(self, mock_get):
        cluster = MagicMock()
        cluster.id = 100
        cluster.cluster_type = ClusterType.TenDBCluster.value
        cluster.immute_domain = "spider.db.test"
        shard = _make_shard(0, 1000)
        shard.storage_instance_tuple.ejector = None
        cluster.tendbclusterstorageset_set.all.return_value.order_by.return_value = [shard]
        mock_get.return_value = cluster

        base = SourceSpec(cluster_id=100, source_name="remote", sync_scope=SyncScope())
        with self.assertRaises(ValueError):
            expand_tendbcluster_source_specs(base)

    @patch("backend.flow.utils.mysql.dts.migrate_helper.Cluster.objects.get")
    def test_skip_already_expanded(self, mock_get):
        src = SourceSpec(
            cluster_id=100,
            source_name="remote-0",
            sync_scope=SyncScope(),
            shard_index=0,
            shard_count=4,
        )
        result = expand_tendbcluster_source_specs(src)
        self.assertEqual(result, [src])
        mock_get.assert_not_called()

    @patch("backend.flow.utils.mysql.dts.migrate_helper.Cluster.objects.get")
    def test_non_cluster_passthrough(self, mock_get):
        cluster = MagicMock()
        cluster.cluster_type = ClusterType.TenDBHA.value
        mock_get.return_value = cluster
        src = SourceSpec(cluster_id=1, source_name="src-1", sync_scope=SyncScope())
        result = expand_tendbcluster_source_specs(src)
        self.assertEqual(result, [src])


class BuildCreateSourceSpiderTest(SimpleTestCase):
    @patch("backend.flow.utils.mysql.dts.migrate_helper.decide_enable_gtid", return_value=True)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_source_endpoint", return_value=("127.0.0.11", 3306))
    def test_spider_shard_when_meta_present(self, _mock_ep, _mock_gtid):
        cluster = MagicMock()
        cluster.id = 100
        cluster.cluster_type = ClusterType.TenDBCluster.value
        cluster.immute_domain = "spider.db.test"
        src = SourceSpec(
            cluster_id=100,
            source_name="remote-1",
            sync_scope=SyncScope(),
            shard_index=1,
            shard_count=4,
            spider_cluster_id="spider.db.test",
            worker_name="worker-2",
        )
        req = build_create_source_request(src, cluster, user="u", password="p")
        self.assertEqual(req.source.cluster_type, "spider-shard")
        self.assertIsNotNone(req.source.spider)
        self.assertEqual(req.source.spider.shard_index, 1)
        self.assertEqual(req.worker_name, "worker-2")

    @patch("backend.flow.utils.mysql.dts.migrate_helper.decide_enable_gtid", return_value=True)
    @patch("backend.flow.utils.mysql.dts.migrate_helper.resolve_source_endpoint", return_value=("127.0.0.11", 3306))
    def test_spider_without_meta_keeps_compat(self, _mock_ep, _mock_gtid):
        cluster = MagicMock()
        cluster.cluster_type = ClusterType.TenDBCluster.value
        cluster.immute_domain = "spider.db.test"
        src = SourceSpec(cluster_id=100, source_name="src", sync_scope=SyncScope())
        req = build_create_source_request(src, cluster, user="u", password="p")
        self.assertEqual(req.source.cluster_type, "spider")
        self.assertIsNone(req.source.spider)


class AssignSourceWorkersTest(SimpleTestCase):
    def test_bind_one_to_one(self):
        sources = [
            SourceSpec(
                cluster_id=1,
                source_name="remote-1",
                sync_scope=SyncScope(),
                shard_index=1,
                myloader=MyloaderSpec(),
            ),
            SourceSpec(
                cluster_id=1,
                source_name="remote-0",
                sync_scope=SyncScope(),
                shard_index=0,
                myloader=MyloaderSpec(),
            ),
        ]
        workers = [
            {"name": "worker-a", "ip": "127.0.0.2"},
            {"name": "worker-b", "ip": "127.0.0.3"},
        ]
        assign_source_workers(sources, workers)
        by_name = {s.source_name: s for s in sources}
        self.assertEqual(by_name["remote-0"].worker_name, "worker-a")
        self.assertEqual(by_name["remote-0"].myloader.dest_worker_ip, "127.0.0.2")
        self.assertEqual(by_name["remote-1"].worker_name, "worker-b")

    def test_fail_when_workers_insufficient(self):
        sources = [
            SourceSpec(cluster_id=1, source_name="a", sync_scope=SyncScope(), shard_index=0),
            SourceSpec(cluster_id=1, source_name="b", sync_scope=SyncScope(), shard_index=1),
        ]
        with self.assertRaises(ValueError):
            assign_source_workers(sources, [{"name": "w1", "ip": "127.0.0.2"}])


class ResolveDestWorkerIpTest(SimpleTestCase):
    def test_prefer_worker_name_binding(self):
        plan = DtsMigratePlan(
            topology=MigrateTopology.ONE_TO_ONE.value,
            migrate_type="mysql_to_mysql",
            dts_cluster_id=9,
            dts_lifecycle="use_existing",
            auto_deploy_dts=False,
            deploy_subflow_inp=None,
            cleanup_after_migrate=False,
            recycle_dts_hosts=True,
            dts_task_config=DtsTaskConfig(),
            task_specs=[],
            worker_count_required=1,
        )
        src = SourceSpec(
            cluster_id=1,
            source_name="remote-0",
            sync_scope=SyncScope(),
            worker_name="worker-b",
            myloader=MyloaderSpec(),
        )
        with patch("backend.flow.utils.mysql.dts.backup_helper.MysqlDtsCluster.objects.filter") as mock_filter:
            dts = MagicMock()
            dts.worker_nodes = [
                {"name": "worker-a", "ip": "127.0.0.2"},
                {"name": "worker-b", "ip": "127.0.0.3"},
            ]
            mock_filter.return_value.first.return_value = dts
            ip = resolve_dest_worker_ip(plan, src, source_index=0)
        self.assertEqual(ip, "127.0.0.3")
