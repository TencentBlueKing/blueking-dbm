# -*- coding: utf-8 -*-
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.flow.utils.mysql.dts.constants import DtsLifecycleMode, FullLoadEngine, MigrateTopology
from backend.flow.utils.mysql.dts.migrate_plan import normalize_migrate_ticket_details
from backend.flow.utils.mysql.dts.task_name import TASK_NAME_MAX_LEN, build_migrate_task_name
from backend.ticket.builders import BuilderFactory
from backend.ticket.builders.mysql.dts.mysql_dts_tickets import (
    MigrateTargetSerializer,
    MysqlDtsClusterDestroyDetailSerializer,
    MysqlDtsClusterDestroyFlowBuilder,
    MysqlDtsClusterReinstallDetailSerializer,
    MysqlDtsClusterReinstallFlowBuilder,
    MysqlDtsClusterReinstallFlowParamBuilder,
    MysqlHaToClusterMigrateFlowBuilder,
    MysqlHaToClusterMigrateFlowParamBuilder,
    MysqlMigrateBaseDetailSerializer,
    MysqlToMysqlMigrateDetailSerializer,
    MysqlToMysqlMigrateFlowBuilder,
    MysqlToMysqlMigrateFlowParamBuilder,
    _maybe_create_destroy_after_migrate,
    _patch_migrate_task_names,
    _validate_mysql_to_mysql_cluster_types,
)
from backend.ticket.constants import EXCLUSIVE_TICKET_EXCEL_PATH, TicketFlowStatus, TicketStatus, TicketType
from backend.utils.excel import ExcelHandler


def _minimal_layered_details(**overrides):
    data = {
        "dts_resource": {
            "mode": DtsLifecycleMode.USE_EXISTING.value,
            "dts_cluster_id": 1,
        },
        "migrate": {
            "topology": MigrateTopology.ONE_TO_ONE.value,
            "one_to_one": {
                "source": {"cluster_id": 100, "sync_scope": {"do_dbs": ["db_a"]}},
                "target": {"cluster_id": 200},
            },
        },
        "task": {
            "task_mode": "all",
            "full_load": {"engine": FullLoadEngine.BUILTIN.value},
        },
    }
    data.update(overrides)
    return data


def _grant_cluster_filter_side_effect(*args, **kwargs):
    """Serializer 版本校验用：按 id__in 返回带可解析 major_version 的假集群。"""
    ids = list(kwargs.get("id__in") or [])
    return [
        SimpleNamespace(
            id=i,
            major_version="MySQL-5.7",
            cluster_type=ClusterType.TenDBHA.value,
        )
        for i in ids
    ]


class MysqlDtsTicketSerializerTest(SimpleTestCase):
    def setUp(self):
        super().setUp()
        patcher = patch(
            "backend.ticket.builders.mysql.dts.mysql_dts_tickets.Cluster.objects.filter",
            side_effect=_grant_cluster_filter_side_effect,
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_migrate_serializer_builds_plan(self):
        slz = MysqlMigrateBaseDetailSerializer(data=_minimal_layered_details())
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertNotIn("migrate_plan", slz.validated_data)
        self.assertIn("migrate_plan", slz.context)
        plan = slz.context["migrate_plan"]
        self.assertEqual(plan.dts_cluster_id, 1)
        self.assertEqual(plan.task_specs[0].sources[0].cluster_id, 100)
        self.assertEqual(plan.task_specs[0].target_cluster_id, 200)
        # validate 阶段无 ticket.id，允许空 task_name
        self.assertEqual(plan.task_specs[0].task_name, "")

    def test_migrate_serializer_without_task_name_valid(self):
        """AE6：无 task_name 入参、无 ticket.id 时结构校验可通过。"""
        slz = MysqlMigrateBaseDetailSerializer(data=_minimal_layered_details())
        self.assertTrue(slz.is_valid(), slz.errors)

    def test_legacy_task_name_input_ignored(self):
        """AE5：旧客户端仍传 task_name 时不驱动业务（字段已删，DRF 默认丢弃）。"""
        details = _minimal_layered_details()
        details["migrate"]["one_to_one"]["task_name"] = "client-provided-name"
        slz = MysqlMigrateBaseDetailSerializer(data=details)
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertNotIn("task_name", slz.validated_data["migrate"]["one_to_one"])
        self.assertEqual(slz.context["migrate_plan"].task_specs[0].task_name, "")

    def test_migrate_serializer_requires_topology_block(self):
        slz = MysqlMigrateBaseDetailSerializer(
            data={
                "dts_resource": {"mode": DtsLifecycleMode.USE_EXISTING.value, "dts_cluster_id": 1},
                "migrate": {"topology": MigrateTopology.ONE_TO_ONE.value},
            }
        )
        self.assertFalse(slz.is_valid())
        self.assertIn("one_to_one", str(slz.errors))

    def test_deploy_ephemeral_requires_deploy(self):
        slz = MysqlMigrateBaseDetailSerializer(
            data=_minimal_layered_details(
                dts_resource={"mode": DtsLifecycleMode.DEPLOY_EPHEMERAL.value},
            )
        )
        self.assertFalse(slz.is_valid())
        self.assertIn("deploy", str(slz.errors))

    def test_use_existing_requires_dts_cluster_id(self):
        slz = MysqlMigrateBaseDetailSerializer(
            data=_minimal_layered_details(dts_resource={"mode": DtsLifecycleMode.USE_EXISTING.value})
        )
        self.assertFalse(slz.is_valid())
        self.assertIn("dts_cluster_id", str(slz.errors))

    def test_use_existing_old_cluster_id_key_ignored(self):
        """AE2：仅传旧键 cluster_id、不传 dts_cluster_id → 缺新键失败；旧键不顶替。"""
        slz = MysqlMigrateBaseDetailSerializer(
            data=_minimal_layered_details(dts_resource={"mode": DtsLifecycleMode.USE_EXISTING.value, "cluster_id": 1})
        )
        self.assertFalse(slz.is_valid())
        self.assertIn("dts_cluster_id", str(slz.errors))

    def test_grant_cluster_empty_major_version_rejected(self):
        """AE8：授权目标集群 major_version 为空 → 拒单。"""
        with patch(
            "backend.ticket.builders.mysql.dts.mysql_dts_tickets.Cluster.objects.filter",
            side_effect=lambda *a, **kw: [
                SimpleNamespace(
                    id=i,
                    major_version="",
                    cluster_type=ClusterType.TenDBHA.value,
                )
                for i in (kw.get("id__in") or [])
            ],
        ):
            slz = MysqlMigrateBaseDetailSerializer(data=_minimal_layered_details())
            self.assertFalse(slz.is_valid())
            self.assertIn("major_version", str(slz.errors))

    def test_myloader_full_load_maps_to_plan(self):
        slz = MysqlMigrateBaseDetailSerializer(
            data=_minimal_layered_details(
                task={
                    "task_mode": "all",
                    "full_load": {
                        "engine": FullLoadEngine.MYLOADER.value,
                        "myloader": {"threads": 12, "dest_worker_ip": "127.0.0.2"},
                    },
                }
            )
        )
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertNotIn("migrate_plan", slz.validated_data)
        plan = slz.context["migrate_plan"]
        self.assertEqual(plan.dts_task_config.full_load_engine, FullLoadEngine.MYLOADER.value)
        self.assertEqual(plan.task_specs[0].sources[0].myloader.threads, 12)

    def test_destroy_after_migrate_defaults_false(self):
        """AE1：use_existing 缺省 destroy_after_migrate → false。"""
        slz = MysqlMigrateBaseDetailSerializer(data=_minimal_layered_details())
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertFalse(slz.validated_data["dts_resource"]["destroy_after_migrate"])

    def test_destroy_after_migrate_true_on_use_existing(self):
        """AE2 入参：use_existing + destroy_after_migrate=true 可通过。"""
        slz = MysqlMigrateBaseDetailSerializer(
            data=_minimal_layered_details(
                dts_resource={
                    "mode": DtsLifecycleMode.USE_EXISTING.value,
                    "dts_cluster_id": 1,
                    "destroy_after_migrate": True,
                }
            )
        )
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertTrue(slz.validated_data["dts_resource"]["destroy_after_migrate"])

    def test_destroy_after_migrate_rejected_on_deploy_ephemeral(self):
        """AE6：非 use_existing 传 true → ValidationError。"""
        slz = MysqlMigrateBaseDetailSerializer(
            data=_minimal_layered_details(
                dts_resource={
                    "mode": DtsLifecycleMode.DEPLOY_EPHEMERAL.value,
                    "destroy_after_migrate": True,
                    "deploy": {
                        "cluster_name": "dts-test",
                        "bk_cloud_id": 0,
                        "master_hosts": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
                        "worker_hosts": [{"ip": "127.0.0.3", "bk_cloud_id": 0}],
                    },
                }
            )
        )
        self.assertFalse(slz.is_valid())
        self.assertIn("destroy_after_migrate", str(slz.errors))

    def test_destroy_after_migrate_rejected_on_deploy_persistent(self):
        """AE6：deploy_persistent + true → invalid。"""
        slz = MysqlMigrateBaseDetailSerializer(
            data=_minimal_layered_details(
                dts_resource={
                    "mode": DtsLifecycleMode.DEPLOY_PERSISTENT.value,
                    "destroy_after_migrate": True,
                    "deploy": {
                        "cluster_name": "dts-persist",
                        "bk_cloud_id": 0,
                        "master_hosts": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
                        "worker_hosts": [{"ip": "127.0.0.3", "bk_cloud_id": 0}],
                    },
                }
            )
        )
        self.assertFalse(slz.is_valid())
        self.assertIn("destroy_after_migrate", str(slz.errors))

    def test_destroy_after_migrate_false_ok_on_deploy(self):
        """非 use_existing + false/缺省不因本字段失败。"""
        slz = MysqlMigrateBaseDetailSerializer(
            data=_minimal_layered_details(
                dts_resource={
                    "mode": DtsLifecycleMode.DEPLOY_EPHEMERAL.value,
                    "destroy_after_migrate": False,
                    "deploy": {
                        "cluster_name": "dts-test",
                        "bk_cloud_id": 0,
                        "master_hosts": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
                        "worker_hosts": [{"ip": "127.0.0.3", "bk_cloud_id": 0}],
                    },
                }
            )
        )
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertFalse(slz.validated_data["dts_resource"]["destroy_after_migrate"])


def _mock_cluster(cluster_id: int, cluster_type: str, proxies=None):
    class _MockProxyQS:
        def __init__(self, proxy_list):
            self._proxies = list(proxy_list)

        def filter(self, **kwargs):
            items = self._proxies
            role = kwargs.get("tendbclusterspiderext__spider_role")
            if role is not None:
                role_val = getattr(role, "value", role)
                items = [p for p in items if p.spider_role == role_val]
            ip = kwargs.get("machine__ip")
            if ip is not None:
                items = [p for p in items if p.machine.ip == ip]
            port = kwargs.get("port")
            if port is not None:
                items = [p for p in items if p.port == port]
            return _MockProxyQS(items)

        def first(self):
            return self._proxies[0] if self._proxies else None

        def exists(self):
            return bool(self._proxies)

        def __iter__(self):
            return iter(self._proxies)

    return SimpleNamespace(
        id=cluster_id,
        cluster_type=cluster_type,
        major_version="MySQL-5.7",
        proxyinstance_set=_MockProxyQS(proxies or []),
    )


def _mock_spider(ip: str, port: int, role=TenDBClusterSpiderRole.SPIDER_MASTER):
    return SimpleNamespace(
        machine=SimpleNamespace(ip=ip),
        port=port,
        spider_role=getattr(role, "value", role),
    )


class MigrateTargetSpiderSerializerTest(SimpleTestCase):
    """U1/U5：target_spider 字段校验。"""

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Cluster.objects.filter")
    def test_valid_spider_master_normalized(self, mock_filter):
        cluster = _mock_cluster(
            200,
            ClusterType.TenDBCluster.value,
            proxies=[_mock_spider("127.0.0.1", 25000)],
        )
        mock_filter.return_value.first.return_value = cluster

        slz = MigrateTargetSerializer(data={"cluster_id": 200, "target_spider": "127.0.0.1:25000"})
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertEqual(slz.validated_data["target_spider"], "127.0.0.1:25000")

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Cluster.objects.filter")
    def test_invalid_spider_endpoint_rejected(self, mock_filter):
        cluster = _mock_cluster(
            200,
            ClusterType.TenDBCluster.value,
            proxies=[_mock_spider("127.0.0.1", 25000)],
        )
        mock_filter.return_value.first.return_value = cluster

        slz = MigrateTargetSerializer(data={"cluster_id": 200, "target_spider": "127.0.0.9:25000"})
        self.assertFalse(slz.is_valid())
        self.assertIn("target_spider", slz.errors)

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Cluster.objects.filter")
    def test_spider_slave_rejected(self, mock_filter):
        cluster = _mock_cluster(
            200,
            ClusterType.TenDBCluster.value,
            proxies=[
                _mock_spider("127.0.0.1", 25000, TenDBClusterSpiderRole.SPIDER_MASTER),
                _mock_spider("127.0.0.2", 25000, TenDBClusterSpiderRole.SPIDER_SLAVE),
            ],
        )
        mock_filter.return_value.first.return_value = cluster

        slz = MigrateTargetSerializer(data={"cluster_id": 200, "target_spider": "127.0.0.2:25000"})
        self.assertFalse(slz.is_valid())
        self.assertIn("target_spider", slz.errors)

    def test_blank_target_spider_treated_as_unspecified(self):
        slz = MigrateTargetSerializer(data={"cluster_id": 200, "target_spider": "  "})
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertIsNone(slz.validated_data["target_spider"])

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Cluster.objects.filter")
    def test_mysql_to_mysql_rejects_target_spider(self, mock_filter):
        cluster = _mock_cluster(200, ClusterType.TenDBHA.value)
        mock_filter.return_value.first.return_value = cluster

        slz = MigrateTargetSerializer(data={"cluster_id": 200, "target_spider": "127.0.0.1:25000"})
        self.assertFalse(slz.is_valid())
        self.assertIn("target_spider", slz.errors)

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Cluster.objects.filter")
    def test_ha_to_cluster_layered_plan_carries_target_spider(self, mock_filter):
        cluster = _mock_cluster(
            200,
            ClusterType.TenDBCluster.value,
            proxies=[_mock_spider("127.0.0.1", 25000)],
        )

        def _filter(**kwargs):
            if "id__in" in kwargs:
                # 版本校验：返回源 100 + 目标 200
                return [
                    SimpleNamespace(id=100, major_version="MySQL-5.7", cluster_type=ClusterType.TenDBHA.value),
                    cluster,
                ]
            return SimpleNamespace(first=lambda: cluster)

        mock_filter.side_effect = _filter

        details = _minimal_layered_details()
        details["migrate"]["one_to_one"]["target"]["target_spider"] = "127.0.0.1:25000"
        slz = MysqlMigrateBaseDetailSerializer(data=details)
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertEqual(slz.context["migrate_plan"].task_specs[0].target_spider, "127.0.0.1:25000")


class MysqlToMysqlClusterTypeValidateTest(SimpleTestCase):
    def test_allows_ha_and_single(self):
        plan = SimpleNamespace(
            task_specs=[
                SimpleNamespace(
                    sources=[SimpleNamespace(cluster_id=1)],
                    target_cluster_id=2,
                )
            ]
        )
        clusters = [
            SimpleNamespace(id=1, cluster_type=ClusterType.TenDBSingle.value, major_version="MySQL-5.7"),
            SimpleNamespace(id=2, cluster_type=ClusterType.TenDBHA.value, major_version="MySQL-5.7"),
        ]
        with patch(
            "backend.ticket.builders.mysql.dts.mysql_dts_tickets.Cluster.objects.filter",
            return_value=clusters,
        ):
            _validate_mysql_to_mysql_cluster_types(plan)

    def test_rejects_tendbcluster(self):
        plan = SimpleNamespace(
            task_specs=[
                SimpleNamespace(
                    sources=[SimpleNamespace(cluster_id=1)],
                    target_cluster_id=2,
                )
            ]
        )
        clusters = [
            SimpleNamespace(id=1, cluster_type=ClusterType.TenDBHA.value, major_version="MySQL-5.7"),
            SimpleNamespace(id=2, cluster_type=ClusterType.TenDBCluster.value, major_version="MySQL-5.7"),
        ]
        with patch(
            "backend.ticket.builders.mysql.dts.mysql_dts_tickets.Cluster.objects.filter",
            return_value=clusters,
        ):
            with self.assertRaises(Exception) as ctx:
                _validate_mysql_to_mysql_cluster_types(plan)
            self.assertIn("TenDBHA/TenDBSingle", str(ctx.exception))

    def test_serializer_class_wired(self):
        self.assertTrue(issubclass(MysqlToMysqlMigrateDetailSerializer, MysqlMigrateBaseDetailSerializer))

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Cluster.objects.filter")
    def test_mysql_to_mysql_serializer_rejects_target_spider(self, mock_cluster_filter):
        """U5：MYSQL_TO_MYSQL 传 target_spider 明确拒绝。"""
        ha_cluster = _mock_cluster(200, ClusterType.TenDBHA.value)

        def _filter(**kwargs):
            if "id__in" in kwargs:
                return [
                    SimpleNamespace(id=i, major_version="MySQL-5.7", cluster_type=ClusterType.TenDBHA.value)
                    for i in kwargs["id__in"]
                ]
            if kwargs.get("id") == 200:
                return SimpleNamespace(first=lambda: ha_cluster)
            return SimpleNamespace(first=lambda: None)

        mock_cluster_filter.side_effect = _filter

        details = _minimal_layered_details()
        details["migrate"]["one_to_one"]["target"]["target_spider"] = "127.0.0.1:25000"
        slz = MysqlToMysqlMigrateDetailSerializer(data=details)
        self.assertFalse(slz.is_valid())
        self.assertIn("target_spider", str(slz.errors))


class MysqlMigrateFlowParamBuilderUidTest(SimpleTestCase):
    """单据进入 Flow 前 get_params 必须含 uid（add_common_params）与 ticket_id（format_ticket_data）。"""

    def _ticket(self, ticket_type: str):
        return SimpleNamespace(
            id=18801,
            details=_minimal_layered_details(),
            ticket_type=ticket_type,
            creator="tester",
            bk_biz_id=1,
        )

    def test_mysql_to_mysql_get_params_has_uid(self):
        builder = MysqlToMysqlMigrateFlowParamBuilder(self._ticket(TicketType.MYSQL_TO_MYSQL_MIGRATE.value))
        params = builder.get_params()
        ticket_data = params["ticket_data"]
        self.assertEqual(ticket_data["uid"], 18801)
        self.assertEqual(ticket_data["ticket_id"], 18801)
        self.assertEqual(ticket_data["migrate_type"], "mysql_to_mysql")
        self.assertEqual(ticket_data["bk_biz_id"], 1)
        self.assertEqual(ticket_data["created_by"], "tester")
        self.assertNotIn("migrate_plan", ticket_data)

    def test_ha_to_cluster_get_params_has_uid(self):
        builder = MysqlHaToClusterMigrateFlowParamBuilder(self._ticket(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.value))
        params = builder.get_params()
        ticket_data = params["ticket_data"]
        self.assertEqual(ticket_data["uid"], 18801)
        self.assertEqual(ticket_data["ticket_id"], 18801)
        self.assertEqual(ticket_data["migrate_type"], "ha_to_cluster")
        self.assertEqual(ticket_data["created_by"], "tester")
        self.assertNotIn("migrate_plan", ticket_data)


class MysqlMigrateTaskNamePatchTest(SimpleTestCase):
    """U3：patch_ticket_detail 回写三种拓扑的 task_name。"""

    def _ticket(self, details: dict, ticket_id: int = 18801):
        ticket = SimpleNamespace(id=ticket_id, details=details)
        ticket.save = MagicMock()
        return ticket

    def test_patch_one_to_one(self):
        ticket = self._ticket(_minimal_layered_details())
        _patch_migrate_task_names(ticket)
        expected = build_migrate_task_name(18801, [100], 200)
        self.assertEqual(ticket.details["migrate"]["one_to_one"]["task_name"], expected)

    def test_patch_many_to_one(self):
        details = {
            "dts_resource": {"mode": DtsLifecycleMode.USE_EXISTING.value, "dts_cluster_id": 1},
            "migrate": {
                "topology": MigrateTopology.MANY_TO_ONE.value,
                "many_to_one": {
                    "sources": [{"cluster_id": 100}, {"cluster_id": 101}],
                    "target": {"cluster_id": 200},
                },
            },
            "task": {"full_load": {"engine": FullLoadEngine.BUILTIN.value}},
        }
        ticket = self._ticket(details)
        _patch_migrate_task_names(ticket)
        expected = build_migrate_task_name(18801, [100, 101], 200)
        self.assertEqual(ticket.details["migrate"]["many_to_one"]["task_name"], expected)

    def test_patch_one_to_many(self):
        details = {
            "dts_resource": {"mode": DtsLifecycleMode.USE_EXISTING.value, "dts_cluster_id": 1},
            "migrate": {
                "topology": MigrateTopology.ONE_TO_MANY.value,
                "one_to_many": {
                    "source": {"cluster_id": 100},
                    "targets": [{"cluster_id": 201}, {"cluster_id": 202}],
                },
            },
            "task": {"full_load": {"engine": FullLoadEngine.BUILTIN.value}},
        }
        ticket = self._ticket(details)
        _patch_migrate_task_names(ticket)
        targets = ticket.details["migrate"]["one_to_many"]["targets"]
        self.assertEqual(targets[0]["task_name"], build_migrate_task_name(18801, [100], 201))
        self.assertEqual(targets[1]["task_name"], build_migrate_task_name(18801, [100], 202))
        self.assertNotEqual(targets[0]["task_name"], targets[1]["task_name"])

    def test_patch_overlong_many_to_one_fits(self):
        srcs = [{"cluster_id": cid} for cid in range(1000, 1100)]
        details = {
            "dts_resource": {"mode": DtsLifecycleMode.USE_EXISTING.value, "dts_cluster_id": 1},
            "migrate": {
                "topology": MigrateTopology.MANY_TO_ONE.value,
                "many_to_one": {"sources": srcs, "target": {"cluster_id": 200}},
            },
            "task": {"full_load": {"engine": FullLoadEngine.BUILTIN.value}},
        }
        ticket = self._ticket(details, ticket_id=999999)
        _patch_migrate_task_names(ticket)
        name = ticket.details["migrate"]["many_to_one"]["task_name"]
        self.assertLessEqual(len(name), TASK_NAME_MAX_LEN)

    def test_builder_patch_ticket_detail_persists(self):
        ticket = self._ticket(_minimal_layered_details())
        builder = MysqlToMysqlMigrateFlowBuilder(ticket)
        with (
            patch.object(builder, "patch_cluster_details"),
            patch.object(builder, "patch_spec_details"),
        ):
            builder.patch_ticket_detail()
        self.assertEqual(
            ticket.details["migrate"]["one_to_one"]["task_name"],
            build_migrate_task_name(18801, [100], 200),
        )
        ticket.save.assert_called()

    def test_ha_builder_also_patches(self):
        ticket = self._ticket(_minimal_layered_details())
        builder = MysqlHaToClusterMigrateFlowBuilder(ticket)
        with (
            patch.object(builder, "patch_cluster_details"),
            patch.object(builder, "patch_spec_details"),
        ):
            builder.patch_ticket_detail()
        self.assertEqual(
            ticket.details["migrate"]["one_to_one"]["task_name"],
            build_migrate_task_name(18801, [100], 200),
        )
        ticket.save.assert_called()


class NormalizeMigrateTicketDetailsTest(SimpleTestCase):
    def test_normalize_use_existing(self):
        flat = normalize_migrate_ticket_details(_minimal_layered_details())
        self.assertEqual(flat["migrate_topology"], MigrateTopology.ONE_TO_ONE.value)
        self.assertEqual(flat["dts_cluster_id"], 1)
        self.assertFalse(flat["auto_deploy_dts"])
        self.assertEqual(flat["dts_lifecycle"], DtsLifecycleMode.USE_EXISTING.value)
        self.assertEqual(flat["one_to_one"]["src_info"]["cluster_id"], 100)
        self.assertEqual(flat["one_to_one"]["dst_info"]["cluster_id"], 200)
        self.assertEqual(flat["dts_task_config"]["full_load_engine"], FullLoadEngine.BUILTIN.value)

    def test_normalize_deploy_ephemeral(self):
        details = _minimal_layered_details(
            dts_resource={
                "mode": DtsLifecycleMode.DEPLOY_EPHEMERAL.value,
                "deploy": {
                    "cluster_name": "dts-test",
                    "bk_cloud_id": 0,
                    "master_hosts": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
                    "worker_hosts": [{"ip": "127.0.0.3", "bk_cloud_id": 0}],
                },
            }
        )
        flat = normalize_migrate_ticket_details(details)
        self.assertTrue(flat["auto_deploy_dts"])
        self.assertTrue(flat["cleanup_after_migrate"])
        self.assertIn("deploy_subflow", flat)
        self.assertEqual(flat["deploy_subflow"]["cluster_name"], "dts-test")

    def test_normalize_many_to_one_sources(self):
        details = {
            "dts_resource": {"mode": DtsLifecycleMode.USE_EXISTING.value, "dts_cluster_id": 9},
            "migrate": {
                "topology": MigrateTopology.MANY_TO_ONE.value,
                "many_to_one": {
                    "sources": [{"cluster_id": 1}, {"cluster_id": 2}],
                    "target": {"cluster_id": 10},
                },
            },
            "task": {"full_load": {"engine": "builtin"}},
        }
        flat = normalize_migrate_ticket_details(details)
        self.assertEqual(len(flat["many_to_one"]["src_infos"]), 2)
        self.assertEqual(flat["many_to_one"]["dst_info"]["cluster_id"], 10)


def _make_destroy_builder(details: dict) -> MysqlDtsClusterDestroyFlowBuilder:
    ticket = SimpleNamespace(id=18801, details=details, ticket_type=TicketType.MYSQL_DTS_CLUSTER_DESTROY.value)
    ticket.save = MagicMock()
    return MysqlDtsClusterDestroyFlowBuilder(ticket)


class MysqlDtsClusterDestroyDetailSerializerTest(SimpleTestCase):
    """DESTROY 详情序列化：patch 后 recycle_hosts 为 list，retrieve 不可再走 BooleanField。"""

    def test_create_accepts_bool(self):
        slz = MysqlDtsClusterDestroyDetailSerializer(
            data={"dts_cluster_id": 9, "recycle_hosts": True, "force_destroy": False}
        )
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertTrue(slz.validated_data["recycle_hosts"])

    def test_create_rejects_list(self):
        slz = MysqlDtsClusterDestroyDetailSerializer(
            data={"dts_cluster_id": 9, "recycle_hosts": [{"bk_host_id": 1002}]}
        )
        self.assertFalse(slz.is_valid())
        self.assertIn("recycle_hosts", slz.errors)

    def test_to_representation_accepts_host_list(self):
        """复现单据详情 8700500：BooleanField 对 list 做 set 成员检测会 unhashable。"""
        hosts = [{"bk_host_id": 1002, "ip": "127.0.0.2"}, {"bk_host_id": 1003, "ip": "127.0.0.3"}]
        data = MysqlDtsClusterDestroyDetailSerializer().to_representation(
            {"dts_cluster_id": 9, "recycle_hosts": hosts, "force_destroy": False, "clean_data_dir": True}
        )
        self.assertEqual(data["recycle_hosts"], hosts)
        self.assertEqual(data["dts_cluster_id"], 9)

    def test_to_representation_accepts_empty_list(self):
        data = MysqlDtsClusterDestroyDetailSerializer().to_representation(
            {"dts_cluster_id": 9, "recycle_hosts": [], "force_destroy": False, "clean_data_dir": True}
        )
        self.assertEqual(data["recycle_hosts"], [])

    def test_to_representation_accepts_bool(self):
        data = MysqlDtsClusterDestroyDetailSerializer().to_representation(
            {"dts_cluster_id": 9, "recycle_hosts": False, "force_destroy": False, "clean_data_dir": True}
        )
        self.assertFalse(data["recycle_hosts"])


class MysqlDtsClusterDestroyRecyclePatchTest(SimpleTestCase):
    """DESTROY 建单 patch_recycle_dts_host_details：布尔开关 → 标准化主机列表。"""

    def _dts_cluster(self, master_nodes, worker_nodes, bk_cloud_id=0):
        return SimpleNamespace(
            id=9,
            bk_cloud_id=bk_cloud_id,
            master_nodes=master_nodes,
            worker_nodes=worker_nodes,
        )

    def test_registered_as_recycle_ticket(self):
        self.assertIn(TicketType.MYSQL_DTS_CLUSTER_DESTROY, BuilderFactory.recycle_ticket_type)

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.ResourceHandler.standardized_resource_host")
    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Machine.objects.filter")
    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.MysqlDtsCluster.objects.filter")
    def test_patch_two_distinct_ips(self, mock_dts_filter, mock_machine_filter, mock_standardize):
        mock_dts_filter.return_value.first.return_value = self._dts_cluster(
            master_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0}],
            worker_nodes=[{"ip": "127.0.0.3", "bk_cloud_id": 0}],
        )
        machines = {
            ("127.0.0.2", 0): SimpleNamespace(bk_host_id=1002),
            ("127.0.0.3", 0): SimpleNamespace(bk_host_id=1003),
        }

        def _machine_filter(**kwargs):
            machine = machines.get((kwargs["ip"], kwargs["bk_cloud_id"]))
            return SimpleNamespace(first=lambda: machine)

        mock_machine_filter.side_effect = _machine_filter
        mock_standardize.side_effect = lambda hosts: [
            {"bk_host_id": h["bk_host_id"], "ip": f"127.0.0.{h['bk_host_id'] % 10}"} for h in hosts
        ]

        builder = _make_destroy_builder({"dts_cluster_id": 9, "recycle_hosts": True})
        builder.patch_recycle_dts_host_details()

        host_ids = {h["bk_host_id"] for h in builder.ticket.details["recycle_hosts"]}
        self.assertEqual(host_ids, {1002, 1003})
        mock_standardize.assert_called_once()
        call_hosts = mock_standardize.call_args[0][0]
        self.assertEqual({h["bk_host_id"] for h in call_hosts}, {1002, 1003})

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.ResourceHandler.standardized_resource_host")
    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Machine.objects.filter")
    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.MysqlDtsCluster.objects.filter")
    def test_patch_colocated_master_worker_dedupes(self, mock_dts_filter, mock_machine_filter, mock_standardize):
        mock_dts_filter.return_value.first.return_value = self._dts_cluster(
            master_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0}],
            worker_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0}],
        )
        mock_machine_filter.return_value.first.return_value = SimpleNamespace(bk_host_id=2002)
        mock_standardize.side_effect = lambda hosts: list(hosts)

        builder = _make_destroy_builder({"dts_cluster_id": 9, "recycle_hosts": True})
        builder.patch_recycle_dts_host_details()

        self.assertEqual(len(builder.ticket.details["recycle_hosts"]), 1)
        self.assertEqual(builder.ticket.details["recycle_hosts"][0]["bk_host_id"], 2002)
        self.assertEqual(mock_machine_filter.call_count, 1)

    def test_patch_recycle_hosts_false_writes_empty_list(self):
        builder = _make_destroy_builder({"dts_cluster_id": 9, "recycle_hosts": False})
        builder.patch_recycle_dts_host_details()
        self.assertEqual(builder.ticket.details["recycle_hosts"], [])

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.ResourceHandler.standardized_resource_host")
    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Machine.objects.filter")
    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.MysqlDtsCluster.objects.filter")
    def test_patch_missing_machine_skipped(self, mock_dts_filter, mock_machine_filter, mock_standardize):
        mock_dts_filter.return_value.first.return_value = self._dts_cluster(
            master_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0}],
            worker_nodes=[{"ip": "127.0.0.3", "bk_cloud_id": 0}],
        )

        def _machine_filter(**kwargs):
            if kwargs["ip"] == "127.0.0.2":
                return SimpleNamespace(first=lambda: SimpleNamespace(bk_host_id=1002))
            return SimpleNamespace(first=lambda: None)

        mock_machine_filter.side_effect = _machine_filter
        mock_standardize.side_effect = lambda hosts: list(hosts)

        builder = _make_destroy_builder({"dts_cluster_id": 9, "recycle_hosts": True})
        builder.patch_recycle_dts_host_details()

        self.assertEqual(builder.ticket.details["recycle_hosts"], [{"bk_host_id": 1002}])
        mock_standardize.assert_called_once_with([{"bk_host_id": 1002}])

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.MysqlDtsCluster.objects.filter")
    def test_patch_missing_dts_cluster_writes_empty(self, mock_dts_filter):
        mock_dts_filter.return_value.first.return_value = None
        builder = _make_destroy_builder({"dts_cluster_id": 999, "recycle_hosts": True})
        builder.patch_recycle_dts_host_details()
        self.assertEqual(builder.ticket.details["recycle_hosts"], [])


class MysqlDtsDestroyAfterMigrateHookTest(SimpleTestCase):
    """AE1–AE6：迁移成功后串联 DESTROY（post_callback / helper）。"""

    def _ticket(self, dts_resource: dict, flow_status=TicketFlowStatus.SUCCEEDED):
        ticket = SimpleNamespace(
            id=18801,
            creator="tester",
            bk_biz_id=1,
            details=_minimal_layered_details(dts_resource=dts_resource),
            ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
        )
        ticket.current_flow = MagicMock(return_value=SimpleNamespace(status=flow_status))
        ticket.add_related_ticket = MagicMock()
        return ticket

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Ticket.create_ticket")
    def test_succeeded_creates_destroy_and_relates(self, mock_create):
        """AE2：use_existing + true + SUCCEEDED → create_ticket + add_related_ticket(done=True)。"""
        destroy = SimpleNamespace(id=99001, ticket_type=TicketType.MYSQL_DTS_CLUSTER_DESTROY.value)
        mock_create.return_value = destroy
        ticket = self._ticket(
            {
                "mode": DtsLifecycleMode.USE_EXISTING.value,
                "dts_cluster_id": 9,
                "destroy_after_migrate": True,
                "recycle_hosts": True,
            }
        )
        builder = MysqlToMysqlMigrateFlowParamBuilder(ticket)
        builder.post_callback()

        mock_create.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        self.assertEqual(kwargs["ticket_type"], TicketType.MYSQL_DTS_CLUSTER_DESTROY)
        self.assertTrue(kwargs["auto_execute"])
        self.assertEqual(kwargs["details"]["dts_cluster_id"], 9)
        self.assertTrue(kwargs["details"]["recycle_hosts"])
        ticket.add_related_ticket.assert_called_once_with(destroy, done=True)

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Ticket.create_ticket")
    def test_recycle_hosts_false_inherited(self, mock_create):
        """AE3：recycle_hosts=false 原样传入 DESTROY details。"""
        mock_create.return_value = SimpleNamespace(id=99002)
        ticket = self._ticket(
            {
                "mode": DtsLifecycleMode.USE_EXISTING.value,
                "dts_cluster_id": 9,
                "destroy_after_migrate": True,
                "recycle_hosts": False,
            }
        )
        _maybe_create_destroy_after_migrate(ticket)
        self.assertFalse(mock_create.call_args.kwargs["details"]["recycle_hosts"])

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Ticket.create_ticket")
    def test_failed_flow_skips_destroy(self, mock_create):
        """AE4：非 SUCCEEDED → 不创 DESTROY。"""
        ticket = self._ticket(
            {
                "mode": DtsLifecycleMode.USE_EXISTING.value,
                "dts_cluster_id": 9,
                "destroy_after_migrate": True,
            },
            flow_status=TicketFlowStatus.FAILED,
        )
        MysqlToMysqlMigrateFlowParamBuilder(ticket).post_callback()
        mock_create.assert_not_called()
        ticket.add_related_ticket.assert_not_called()

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Ticket.create_ticket")
    def test_destroy_flag_false_skips(self, mock_create):
        """AE1：destroy_after_migrate=false → 不创 DESTROY。"""
        ticket = self._ticket(
            {
                "mode": DtsLifecycleMode.USE_EXISTING.value,
                "dts_cluster_id": 9,
                "destroy_after_migrate": False,
            }
        )
        MysqlToMysqlMigrateFlowParamBuilder(ticket).post_callback()
        mock_create.assert_not_called()

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Ticket.create_ticket")
    def test_non_use_existing_helper_noop(self, mock_create):
        """AE6：mode 非 use_existing（脏写 true）→ helper no-op。"""
        ticket = self._ticket(
            {
                "mode": DtsLifecycleMode.DEPLOY_EPHEMERAL.value,
                "destroy_after_migrate": True,
                "cluster_id": 9,
            }
        )
        _maybe_create_destroy_after_migrate(ticket)
        mock_create.assert_not_called()

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Ticket.create_ticket")
    def test_ha_builder_also_creates_destroy(self, mock_create):
        """两个 ParamBuilder 均委托 helper；HA→Cluster 成功路径同样串联。"""
        destroy = SimpleNamespace(id=99003)
        mock_create.return_value = destroy
        ticket = self._ticket(
            {
                "mode": DtsLifecycleMode.USE_EXISTING.value,
                "dts_cluster_id": 11,
                "destroy_after_migrate": True,
                "recycle_hosts": True,
            }
        )
        ticket.ticket_type = TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.value
        MysqlHaToClusterMigrateFlowParamBuilder(ticket).post_callback()
        mock_create.assert_called_once()
        self.assertEqual(mock_create.call_args.kwargs["details"]["dts_cluster_id"], 11)
        ticket.add_related_ticket.assert_called_once_with(destroy, done=True)

    @patch("backend.ticket.builders.mysql.dts.mysql_dts_tickets.Ticket.create_ticket")
    def test_create_exception_does_not_raise(self, mock_create):
        """串联失败只记日志，不抛出影响迁移成功态。"""
        mock_create.side_effect = RuntimeError("boom")
        ticket = self._ticket(
            {
                "mode": DtsLifecycleMode.USE_EXISTING.value,
                "dts_cluster_id": 9,
                "destroy_after_migrate": True,
            }
        )
        # 不应抛出
        MysqlToMysqlMigrateFlowParamBuilder(ticket).post_callback()
        ticket.add_related_ticket.assert_not_called()


class MysqlDtsClusterDestroyRecycleSuccessHookTest(SimpleTestCase):
    """DESTROY 成功钩子：非空 recycle_hosts 触发 create_recycle_ticket；空列表 early-return。"""

    @patch("backend.ticket.flow_manager.manager.create_recycle_ticket.apply_async")
    @patch("backend.ticket.flow_manager.manager.notify.send_msg.apply_async")
    @patch("backend.ticket.flow_manager.manager.add_ticket_audit_event.apply_async")
    def test_succeeded_with_hosts_calls_create_recycle_ticket(self, _mock_audit, _mock_notify, mock_apply_async):
        from backend.ticket.flow_manager.manager import TicketFlowManager

        hosts = [{"bk_host_id": 1002, "ip": "127.0.0.2"}, {"bk_host_id": 1003, "ip": "127.0.0.3"}]
        ticket = SimpleNamespace(
            id=18801,
            ticket_type=TicketType.MYSQL_DTS_CLUSTER_DESTROY.value,
            details={"dts_cluster_id": 9, "recycle_hosts": hosts},
        )
        self.assertIn(ticket.ticket_type, BuilderFactory.recycle_ticket_type)

        manager = TicketFlowManager.__new__(TicketFlowManager)
        manager.ticket = ticket
        manager.ticket_status_trigger(TicketStatus.RUNNING, TicketStatus.SUCCEEDED)

        mock_apply_async.assert_called_once_with(args=(ticket.id, hosts, TicketType.RECYCLE_OLD_HOST))

    @patch("backend.ticket.models.ticket.Ticket.create_ticket")
    def test_create_recycle_ticket_skips_when_hosts_empty(self, mock_create_ticket):
        """空列表走 create_recycle_ticket 内部 early-return，不创建关联单。"""
        from backend.ticket.models.ticket import Ticket

        parent = SimpleNamespace(
            id=18801,
            details={},
            ticket_type=TicketType.MYSQL_DTS_CLUSTER_DESTROY.value,
            group="mysql",
            bk_biz_id=1,
            creator="tester",
        )
        with patch.object(Ticket.objects, "get", return_value=parent):
            Ticket.create_recycle_ticket(18801, [], TicketType.RECYCLE_OLD_HOST)

        mock_create_ticket.assert_not_called()

    @patch("backend.ticket.flow_manager.manager.create_recycle_ticket.apply_async")
    @patch("backend.ticket.flow_manager.manager.notify.send_msg.apply_async")
    @patch("backend.ticket.flow_manager.manager.add_ticket_audit_event.apply_async")
    def test_succeeded_with_empty_hosts_still_dispatches_task(self, _mock_audit, _mock_notify, mock_apply_async):
        """manager 仍会 apply_async；空列表由 create_recycle_ticket 内部跳过关联单。"""
        from backend.ticket.flow_manager.manager import TicketFlowManager

        ticket = SimpleNamespace(
            id=18802,
            ticket_type=TicketType.MYSQL_DTS_CLUSTER_DESTROY.value,
            details={"dts_cluster_id": 9, "recycle_hosts": []},
        )
        manager = TicketFlowManager.__new__(TicketFlowManager)
        manager.ticket = ticket
        manager.ticket_status_trigger(TicketStatus.RUNNING, TicketStatus.SUCCEEDED)

        mock_apply_async.assert_called_once_with(args=(ticket.id, [], TicketType.RECYCLE_OLD_HOST))


class MysqlDtsExclusiveTicketMapTest(SimpleTestCase):
    """DTS 迁移单据与数据校验定时任务在互斥表中应可并行（Y）。"""

    @staticmethod
    def _exclusive_bool_map():
        """与 ClusterOperateRecordManager.get_exclusive_ticket_map 相同的 Excel→互斥布尔映射。"""
        path = os.path.join(settings.BASE_DIR, EXCLUSIVE_TICKET_EXCEL_PATH)
        exclusive_matrix = ExcelHandler.paser_matrix(path)
        label_value_map = {TicketType.get_choice_label(v): v for v in TicketType.get_values()}
        exclusive_map = {}
        for row_label, inner_dict in exclusive_matrix.items():
            row_key = label_value_map[row_label]
            exclusive_map.setdefault(row_key, {})
            for col_label, value in inner_dict.items():
                col_key = label_value_map[col_label]
                exclusive_map[row_key][col_key] = value == "N"
        return exclusive_map

    def test_dts_migrate_not_exclusive_with_mysql_checksum_cron(self):
        exclusive_map = self._exclusive_bool_map()
        migrate_types = [
            TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
            TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.value,
        ]
        checksum = TicketType.MYSQL_CHECKSUM_CRON.value
        for migrate in migrate_types:
            self.assertFalse(
                exclusive_map[checksum].get(migrate, True),
                msg=f"{checksum} should not be exclusive with active {migrate}",
            )
            self.assertFalse(
                exclusive_map[migrate].get(checksum, True),
                msg=f"{migrate} should not be exclusive with active {checksum}",
            )

    def test_ha_to_cluster_migrate_not_exclusive_with_tendbcluster_checksum_cron(self):
        exclusive_map = self._exclusive_bool_map()
        migrate = TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.value
        checksum = TicketType.TENDBCLUSTER_CHECKSUM_CRON.value
        self.assertFalse(exclusive_map[checksum].get(migrate, True))
        self.assertFalse(exclusive_map[migrate].get(checksum, True))

    def test_dts_migrate_types_exclusive_with_each_other(self):
        exclusive_map = self._exclusive_bool_map()
        a = TicketType.MYSQL_TO_MYSQL_MIGRATE.value
        b = TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.value
        self.assertTrue(exclusive_map[a].get(a, True))
        self.assertTrue(exclusive_map[b].get(b, True))
        self.assertTrue(exclusive_map[a].get(b, True))
        self.assertTrue(exclusive_map[b].get(a, True))

    def test_dts_checksum_not_exclusive_with_dts_migrate(self):
        """附属 MYSQL_DTS_CHECKSUM 应可与迁移父单并行（Y）。"""
        exclusive_map = self._exclusive_bool_map()
        checksum = TicketType.MYSQL_DTS_CHECKSUM.value
        migrate_types = [
            TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
            TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.value,
        ]
        for migrate in migrate_types:
            self.assertFalse(
                exclusive_map[checksum].get(migrate, True),
                msg=f"{checksum} should not be exclusive with active {migrate}",
            )
            self.assertFalse(
                exclusive_map[migrate].get(checksum, True),
                msg=f"{migrate} should not be exclusive with active {checksum}",
            )
        self.assertTrue(exclusive_map[checksum].get(checksum, True))


class MysqlDtsClusterReinstallSerializerTest(SimpleTestCase):
    """REINSTALL 单据序列化测试。"""

    def test_dts_cluster_id_required(self):
        slz = MysqlDtsClusterReinstallDetailSerializer(data={})
        self.assertFalse(slz.is_valid())
        self.assertIn("dts_cluster_id", slz.errors)

    def test_minimal_input_valid(self):
        slz = MysqlDtsClusterReinstallDetailSerializer(data={"dts_cluster_id": 99})
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertEqual(slz.validated_data["dts_cluster_id"], 99)
        self.assertFalse(slz.validated_data["force_reinstall"])
        self.assertIsNone(slz.validated_data.get("dts_pkg_id"))

    def test_force_reinstall_true(self):
        slz = MysqlDtsClusterReinstallDetailSerializer(data={"dts_cluster_id": 99, "force_reinstall": True})
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertTrue(slz.validated_data["force_reinstall"])

    def test_dts_pkg_id_optional(self):
        slz = MysqlDtsClusterReinstallDetailSerializer(data={"dts_cluster_id": 99, "dts_pkg_id": 123})
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertEqual(slz.validated_data["dts_pkg_id"], 123)

    def test_dts_pkg_id_allows_null(self):
        slz = MysqlDtsClusterReinstallDetailSerializer(data={"dts_cluster_id": 99, "dts_pkg_id": None})
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertIsNone(slz.validated_data["dts_pkg_id"])


class MysqlDtsClusterReinstallBuilderTest(SimpleTestCase):
    """REINSTALL Builder 测试。"""

    def test_builder_registered(self):
        self.assertIn(TicketType.MYSQL_DTS_CLUSTER_REINSTALL, BuilderFactory.registry)

    def test_builder_serializer_wired(self):
        self.assertEqual(
            MysqlDtsClusterReinstallFlowBuilder.serializer,
            MysqlDtsClusterReinstallDetailSerializer,
        )

    def test_builder_inner_flow_wired(self):
        self.assertEqual(
            MysqlDtsClusterReinstallFlowBuilder.inner_flow_builder,
            MysqlDtsClusterReinstallFlowParamBuilder,
        )

    def test_flow_param_builder_controller(self):
        from backend.flow.engine.controller.mysql import MySQLController

        self.assertEqual(
            MysqlDtsClusterReinstallFlowParamBuilder.controller,
            MySQLController.mysql_dts_cluster_reinstall_scene,
        )


class MySQLDtsChecksumFlowBuilderTest(SimpleTestCase):
    def test_auto_spawned_checksum_skips_itsm(self):
        from backend.ticket.builders.mysql.mysql_checksum import MySQLChecksumFlowBuilder
        from backend.ticket.builders.mysql.mysql_dts_checksum import MySQLDtsChecksumFlowBuilder

        ticket = MagicMock()
        ticket.details = {"need_manual_confirm": False, "dts_mode": True}
        dts_builder = MySQLDtsChecksumFlowBuilder(ticket)
        base_builder = MySQLChecksumFlowBuilder(ticket)

        self.assertFalse(dts_builder.need_itsm)
        self.assertTrue(base_builder.need_itsm)
        self.assertTrue(dts_builder.need_timer)
