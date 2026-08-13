# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.flow.utils.mysql.dts.constants import MigrateType
from backend.flow.utils.mysql.dts.migrate_helper import (
    _build_cluster_target_config,
    _build_mysql_target_config,
    _collect_target_grant_endpoints,
    _collect_target_gtid_probe_endpoints,
    build_dts_task_request,
    resolve_cluster_target_spider_endpoint,
    resolve_source_endpoint,
)
from backend.flow.utils.mysql.dts.migrate_plan import SourceSpec, SyncScope


def _role_value(role):
    return getattr(role, "value", role)


class _StorageQS:
    def __init__(self, storages):
        self._storages = list(storages)

    def filter(self, **kwargs):
        items = self._storages
        if "instance_role" in kwargs:
            items = [s for s in items if s.instance_role == kwargs["instance_role"]]
        if "is_stand_by" in kwargs:
            items = [s for s in items if getattr(s, "is_stand_by", False) == kwargs["is_stand_by"]]
        return _StorageQS(items)

    def exists(self):
        return bool(self._storages)

    def first(self):
        return self._storages[0] if self._storages else None

    def get(self, **kwargs):
        for s in self._storages:
            if all(getattr(s, k) == v for k, v in kwargs.items()):
                return s
        raise LookupError(kwargs)

    def __iter__(self):
        return iter(self._storages)


class _ProxyQS:
    def __init__(self, proxies):
        self._proxies = list(proxies)

    def filter(self, **kwargs):
        items = self._proxies
        role = kwargs.get("tendbclusterspiderext__spider_role")
        if role is not None:
            role_val = _role_value(role)
            items = [p for p in items if p.spider_role == role_val]
        roles = kwargs.get("tendbclusterspiderext__spider_role__in")
        if roles is not None:
            role_vals = {_role_value(r) for r in roles}
            items = [p for p in items if p.spider_role in role_vals]
        return _ProxyQS(items)

    def first(self):
        return self._proxies[0] if self._proxies else None

    def __iter__(self):
        return iter(self._proxies)


def _ins(ip: str, port: int, role: str, is_stand_by: bool = False):
    return SimpleNamespace(
        machine=SimpleNamespace(ip=ip),
        port=port,
        instance_role=role,
        is_stand_by=is_stand_by,
    )


def _proxy(ip: str, port: int, spider_role, admin_port: int = 0):
    return SimpleNamespace(
        machine=SimpleNamespace(ip=ip),
        port=port,
        admin_port=admin_port,
        spider_role=_role_value(spider_role),
    )


def _cluster(cluster_type: str, storages: list, bk_cloud_id: int = 0, proxies: list | None = None):
    cluster = MagicMock()
    cluster.id = 1
    cluster.cluster_type = cluster_type
    cluster.bk_cloud_id = bk_cloud_id
    cluster.storageinstance_set = _StorageQS(storages)
    cluster.proxyinstance_set = _ProxyQS(proxies or [])
    return cluster


class ResolveSourceEndpointTest(SimpleTestCase):
    def test_tendbsingle_defaults_to_orphan(self):
        cluster = _cluster(
            ClusterType.TenDBSingle.value,
            [_ins("127.0.0.10", 20000, InstanceRole.ORPHAN.value)],
        )
        spec = SourceSpec(cluster_id=1, source_name="s1", sync_scope=SyncScope())
        ip, port = resolve_source_endpoint(spec, cluster)
        self.assertEqual((ip, port), ("127.0.0.10", 20000))

    def test_tendbha_prefers_standby_slave(self):
        cluster = _cluster(
            ClusterType.TenDBHA.value,
            [
                _ins("127.0.0.11", 20000, InstanceRole.BACKEND_SLAVE.value, is_stand_by=False),
                _ins("127.0.0.12", 20000, InstanceRole.BACKEND_SLAVE.value, is_stand_by=True),
            ],
        )
        spec = SourceSpec(cluster_id=1, source_name="s1", sync_scope=SyncScope())
        ip, port = resolve_source_endpoint(spec, cluster)
        self.assertEqual((ip, port), ("127.0.0.12", 20000))


class TargetEndpointTest(SimpleTestCase):
    def test_single_target_grant_uses_orphan(self):
        cluster = _cluster(
            ClusterType.TenDBSingle.value,
            [_ins("127.0.0.20", 20000, InstanceRole.ORPHAN.value)],
        )
        endpoints = _collect_target_grant_endpoints(cluster, migrate_type="mysql_to_mysql")
        self.assertEqual(endpoints, [("127.0.0.20", 20000)])

    def test_single_target_config_uses_orphan(self):
        cluster = _cluster(
            ClusterType.TenDBSingle.value,
            [_ins("127.0.0.21", 20001, InstanceRole.ORPHAN.value)],
        )
        cfg = _build_mysql_target_config(cluster, user="u", password="p")
        self.assertEqual(cfg.host, "127.0.0.21")
        self.assertEqual(cfg.port, 20001)

    def test_ha_target_config_uses_master(self):
        cluster = _cluster(
            ClusterType.TenDBHA.value,
            [_ins("127.0.0.22", 20000, InstanceRole.BACKEND_MASTER.value)],
        )
        cfg = _build_mysql_target_config(cluster, user="u", password="p")
        self.assertEqual(cfg.host, "127.0.0.22")

    def test_cluster_target_grant_tdbctl_primary_only(self):
        """HA→Cluster：spider 全量 + tdbctl 仅 Primary + remote master。"""
        primary = _proxy(
            "127.0.0.15",
            25000,
            TenDBClusterSpiderRole.SPIDER_MASTER,
            admin_port=26000,
        )
        secondary = _proxy(
            "127.0.0.141",
            25000,
            TenDBClusterSpiderRole.SPIDER_MASTER,
            admin_port=26000,
        )
        cluster = _cluster(
            ClusterType.TenDBCluster.value,
            [_ins("127.0.0.40", 20000, InstanceRole.REMOTE_MASTER.value)],
            proxies=[secondary, primary],
        )
        cluster.tendbcluster_ctl_primary_address.return_value = "127.0.0.15:26000"

        endpoints = _collect_target_grant_endpoints(cluster, MigrateType.HA_TO_CLUSTER.value)

        self.assertIn(("127.0.0.15", 25000), endpoints)
        self.assertIn(("127.0.0.141", 25000), endpoints)
        self.assertIn(("127.0.0.40", 20000), endpoints)
        self.assertEqual([e for e in endpoints if e[1] == 26000], [("127.0.0.15", 26000)])
        self.assertNotIn(("127.0.0.141", 26000), endpoints)

    def test_cluster_target_grant_tdbctl_fallback_uses_admin_port(self):
        """Primary 探测失败时，回退到首个 spider_master 的 admin_port（元数据端口，非硬编码）。"""
        spider = _proxy(
            "127.0.0.16",
            25000,
            TenDBClusterSpiderRole.SPIDER_MASTER,
            admin_port=26111,
        )
        cluster = _cluster(
            ClusterType.TenDBCluster.value,
            [_ins("127.0.0.41", 20000, InstanceRole.REMOTE_MASTER.value)],
            proxies=[spider],
        )
        cluster.tendbcluster_ctl_primary_address.side_effect = RuntimeError("rpc failed")

        endpoints = _collect_target_grant_endpoints(cluster, MigrateType.HA_TO_CLUSTER.value)

        self.assertIn(("127.0.0.16", 25000), endpoints)
        self.assertIn(("127.0.0.16", 26111), endpoints)
        self.assertIn(("127.0.0.41", 20000), endpoints)


class TargetGtidProbeEndpointTest(SimpleTestCase):
    def test_single_target_gtid_probe_uses_orphan(self):
        cluster = _cluster(
            ClusterType.TenDBSingle.value,
            [_ins("127.0.0.30", 20000, InstanceRole.ORPHAN.value)],
            bk_cloud_id=1,
        )
        endpoints = _collect_target_gtid_probe_endpoints(cluster, MigrateType.MYSQL_TO_MYSQL.value)
        self.assertEqual(endpoints, [("127.0.0.30", 20000, 1)])

    def test_ha_target_gtid_probe_uses_master(self):
        cluster = _cluster(
            ClusterType.TenDBHA.value,
            [_ins("127.0.0.31", 20000, InstanceRole.BACKEND_MASTER.value)],
            bk_cloud_id=2,
        )
        endpoints = _collect_target_gtid_probe_endpoints(cluster, MigrateType.MYSQL_TO_MYSQL.value)
        self.assertEqual(endpoints, [("127.0.0.31", 20000, 2)])

    def test_cluster_target_gtid_probe_uses_remote_master(self):
        cluster = _cluster(
            ClusterType.TenDBCluster.value,
            [_ins("127.0.0.32", 20000, InstanceRole.REMOTE_MASTER.value)],
            bk_cloud_id=3,
        )
        endpoints = _collect_target_gtid_probe_endpoints(cluster, MigrateType.HA_TO_CLUSTER.value)
        self.assertEqual(endpoints, [("127.0.0.32", 20000, 3)])


class ClusterTargetSpiderResolveTest(SimpleTestCase):
    """U3/U4：指定 target_spider 仅覆盖顶层 host/port。"""

    def _cluster_with_two_spider_masters(self):
        primary = _proxy("127.0.0.15", 25000, TenDBClusterSpiderRole.SPIDER_MASTER, admin_port=26000)
        secondary = _proxy("127.0.0.141", 25000, TenDBClusterSpiderRole.SPIDER_MASTER, admin_port=26001)
        cluster = _cluster(
            ClusterType.TenDBCluster.value,
            [_ins("127.0.0.40", 20000, InstanceRole.REMOTE_MASTER.value)],
            proxies=[primary, secondary],
        )
        cluster.tendbcluster_ctl_primary_address.return_value = "127.0.0.15:26000"
        return cluster, primary, secondary

    def test_resolve_endpoint_explicit_target_spider(self):
        cluster, unused_primary, unused_secondary = self._cluster_with_two_spider_masters()
        host, port = resolve_cluster_target_spider_endpoint(cluster, "127.0.0.5:25000")
        self.assertEqual((host, port), ("127.0.0.5", 25000))

    def test_resolve_endpoint_default_uses_first_spider_master(self):
        cluster, primary, unused_secondary = self._cluster_with_two_spider_masters()
        host, port = resolve_cluster_target_spider_endpoint(cluster, None)
        self.assertEqual((host, port), (primary.machine.ip, primary.port))

    def test_resolve_endpoint_invalid_format_raises(self):
        cluster, unused_primary, unused_secondary = self._cluster_with_two_spider_masters()
        with self.assertRaises(ValueError):
            resolve_cluster_target_spider_endpoint(cluster, "127.0.0.141")

    def test_resolve_endpoint_no_spider_raises(self):
        cluster = _cluster(ClusterType.TenDBCluster.value, [], proxies=[])
        with self.assertRaises(ValueError):
            resolve_cluster_target_spider_endpoint(cluster, None)

    def test_default_uses_first_spider_master(self):
        cluster, primary, unused_secondary = self._cluster_with_two_spider_masters()
        default_cfg = _build_cluster_target_config(cluster, user="u", password="p")
        self.assertEqual((default_cfg.host, default_cfg.port), (primary.machine.ip, primary.port))

    def test_specified_second_spider_master(self):
        cluster, unused_primary, secondary = self._cluster_with_two_spider_masters()
        specified_cfg = _build_cluster_target_config(
            cluster, user="u", password="p", target_spider="127.0.0.141:25000"
        )
        self.assertEqual((specified_cfg.host, specified_cfg.port), (secondary.machine.ip, secondary.port))

    def test_invalid_target_spider_format_raises(self):
        cluster, unused_primary, unused_secondary = self._cluster_with_two_spider_masters()
        with self.assertRaises(ValueError):
            _build_cluster_target_config(cluster, user="u", password="p", target_spider="127.0.0.141")

    def test_build_cluster_target_config_top_level_only_changes(self):
        cluster, primary, secondary = self._cluster_with_two_spider_masters()
        default_cfg = _build_cluster_target_config(cluster, user="u", password="p")
        specified_cfg = _build_cluster_target_config(
            cluster, user="u", password="p", target_spider="127.0.0.141:25000"
        )

        self.assertEqual(default_cfg.host, primary.machine.ip)
        self.assertEqual(specified_cfg.host, secondary.machine.ip)
        self.assertEqual(specified_cfg.port, secondary.port)
        self.assertEqual(default_cfg.spider.tdbctl.host, specified_cfg.spider.tdbctl.host)
        self.assertEqual(default_cfg.spider.tdbctl.port, specified_cfg.spider.tdbctl.port)
        self.assertEqual(len(default_cfg.spider.shards), len(specified_cfg.spider.shards))
        self.assertEqual(default_cfg.spider.shards[0].host, specified_cfg.spider.shards[0].host)

    def test_build_dts_task_request_uses_target_spider(self):
        from backend.flow.utils.mysql.dts.constants import DtsLifecycleMode, MigrateTopology
        from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan, DtsTaskConfig, DtsTaskSpec

        cluster, primary, secondary = self._cluster_with_two_spider_masters()
        plan = DtsMigratePlan(
            topology=MigrateTopology.ONE_TO_ONE.value,
            migrate_type=MigrateType.HA_TO_CLUSTER.value,
            dts_cluster_id=1,
            dts_lifecycle=DtsLifecycleMode.USE_EXISTING.value,
            auto_deploy_dts=False,
            deploy_subflow_inp=None,
            cleanup_after_migrate=False,
            recycle_dts_hosts=False,
            dts_task_config=DtsTaskConfig(),
            task_specs=[],
            worker_count_required=1,
        )
        task_spec = DtsTaskSpec(
            task_name="ha-to-cluster-1",
            target_cluster_id=cluster.id,
            sources=[SourceSpec(cluster_id=1, source_name="src-1", sync_scope=SyncScope(do_dbs=["db_a"]))],
            target_spider="127.0.0.141:25000",
            dts_task_config=DtsTaskConfig(),
        )

        with patch(
            "backend.flow.utils.mysql.dts.migrate_helper.Cluster.objects.get",
            return_value=cluster,
        ):
            request = build_dts_task_request(plan, task_spec, user="u", password="p", cluster_name="dts-ut")

        self.assertEqual(request.task.target_config.host, secondary.machine.ip)
        self.assertEqual(request.task.target_config.port, secondary.port)
        self.assertEqual(request.task.target_config.spider.tdbctl.host, "127.0.0.15")
        self.assertNotEqual(request.task.target_config.host, primary.machine.ip)
