# -*- coding: utf-8 -*-
import re
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType
from backend.flow.utils.mysql.dts.constants import (
    MYSQL_DTS_MIGRATE_USER_MAX_LENGTH,
    MYSQL_DTS_MIGRATE_USER_PREFIX,
    MYSQL_DTS_MIGRATE_USER_SUFFIX_LENGTH,
    MYSQL_DTS_VERIFY_MAX_RETRIES,
    DtsLifecycleMode,
    MigrateTopology,
    MigrateType,
)
from backend.flow.utils.mysql.dts.context import DtsHostSpec
from backend.flow.utils.mysql.dts.deploy_helper import build_master_node_name, group_deploy_hosts, render_master_config
from backend.flow.utils.mysql.dts.migrate_credentials import (
    generate_dts_migrate_credentials,
    generate_dts_migrate_username,
)
from backend.flow.utils.mysql.dts.migrate_helper import _build_table_migrate_rules
from backend.flow.utils.mysql.dts.migrate_plan import (
    SyncScope,
    TableRoute,
    build_migrate_plan,
    build_migrate_plans,
    dts_task_spec_from_dict,
    dts_task_spec_to_dict,
    infer_dts_resource_intent,
    infer_rename_migrate_type,
    is_real_rename_route,
    iter_migrate_row_details,
    patch_deploy_cluster_names_into_details,
    resolve_ticket_destroy_policy,
    resolve_ticket_lifecycle,
)

# 内部默认名：source-{cluster_id}-{12 hex}
_SOURCE_NAME_RE = re.compile(r"^source-(\d+)-([0-9a-f]{12})$")


def _assert_default_source_name(testcase: SimpleTestCase, source_name: str, cluster_id: int):
    matched = _SOURCE_NAME_RE.match(source_name)
    testcase.assertIsNotNone(matched, msg=f"unexpected source_name: {source_name}")
    testcase.assertEqual(int(matched.group(1)), cluster_id)


class MigratePlanTest(SimpleTestCase):
    def test_build_one_to_one_plan(self):
        details = {
            "migrate_topology": MigrateTopology.ONE_TO_ONE.value,
            "one_to_one": {
                "task_name": "mysql-dts-12-1-2",
                "src_info": {"cluster_id": 1},
                "dst_info": {"cluster_id": 2},
            },
        }
        plan = build_migrate_plan(details)
        self.assertEqual(len(plan.task_specs), 1)
        self.assertEqual(plan.task_specs[0].sources[0].cluster_id, 1)
        _assert_default_source_name(self, plan.task_specs[0].sources[0].source_name, 1)
        self.assertEqual(plan.task_specs[0].target_cluster_id, 2)
        self.assertEqual(plan.task_specs[0].task_name, "mysql-dts-12-1-2")
        self.assertEqual(plan.worker_count_required, 1)

    def test_build_many_to_one_plan(self):
        details = {
            "migrate_topology": MigrateTopology.MANY_TO_ONE.value,
            "many_to_one": {
                "task_name": "mysql-dts-12-1_2-10",
                "src_infos": [{"cluster_id": 1}, {"cluster_id": 2}],
                "dst_info": {"cluster_id": 10},
            },
        }
        plan = build_migrate_plan(details)
        self.assertEqual(len(plan.task_specs), 1)
        self.assertEqual(len(plan.task_specs[0].sources), 2)
        names = [s.source_name for s in plan.task_specs[0].sources]
        self.assertEqual(len(names), len(set(names)))
        for src in plan.task_specs[0].sources:
            _assert_default_source_name(self, src.source_name, src.cluster_id)
        self.assertEqual(plan.task_specs[0].task_name, "mysql-dts-12-1_2-10")
        self.assertEqual(plan.worker_count_required, 2)

    def test_parse_deploy_subflow(self):
        details = {
            "migrate_topology": MigrateTopology.ONE_TO_ONE.value,
            "auto_deploy_dts": True,
            "bk_biz_id": 100,
            "bk_cloud_id": 0,
            "deploy_subflow": {
                "cluster_name": "dts-test",
                "master_hosts": [{"ip": "127.0.0.1", "bk_cloud_id": 0}],
                "worker_hosts": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
            },
            "one_to_one": {
                "task_name": "mysql-dts-1-1-2",
                "src_info": {"cluster_id": 1},
                "dst_info": {"cluster_id": 2},
            },
        }
        plan = build_migrate_plan(details)
        self.assertIsNotNone(plan.deploy_subflow_inp)
        self.assertEqual(plan.deploy_subflow_inp.cluster_name, "dts-test")
        self.assertEqual(len(plan.deploy_subflow_inp.worker_hosts), 1)

    def test_missing_task_name_raises(self):
        details = {
            "migrate_topology": MigrateTopology.ONE_TO_ONE.value,
            "one_to_one": {
                "src_info": {"cluster_id": 1},
                "dst_info": {"cluster_id": 2},
            },
        }
        with self.assertRaises(ValueError) as ctx:
            build_migrate_plan(details)
        self.assertIn("task_name", str(ctx.exception))

    def test_require_task_name_false_allows_empty(self):
        details = {
            "migrate_topology": MigrateTopology.ONE_TO_ONE.value,
            "one_to_one": {
                "src_info": {"cluster_id": 1},
                "dst_info": {"cluster_id": 2},
            },
        }
        plan = build_migrate_plan(details, require_task_name=False)
        self.assertEqual(plan.task_specs[0].task_name, "")

    def test_layered_details_consumes_written_task_name(self):
        details = {
            "dts_resource": {"dts_cluster_id": 9},
            "migrate": {
                "topology": MigrateTopology.ONE_TO_ONE.value,
                "one_to_one": {
                    "task_name": "mysql-dts-18801-100-200",
                    "source": {"cluster_id": 100},
                    "target": {"cluster_id": 200},
                },
            },
            "task": {"full_load": {"engine": "builtin"}},
        }
        plan = build_migrate_plan(details)
        self.assertEqual(plan.task_specs[0].task_name, "mysql-dts-18801-100-200")
        _assert_default_source_name(self, plan.task_specs[0].sources[0].source_name, 100)

    def test_ticket_source_name_ignored_uses_default(self):
        """建单若仍透传 source_name，解析时忽略并使用默认名。"""
        details = {
            "migrate_topology": MigrateTopology.ONE_TO_ONE.value,
            "one_to_one": {
                "task_name": "mysql-dts-1-1-2",
                "src_info": {"cluster_id": 1, "source_name": "custom-name"},
                "dst_info": {"cluster_id": 2},
            },
        }
        plan = build_migrate_plan(details)
        name = plan.task_specs[0].sources[0].source_name
        self.assertNotEqual(name, "custom-name")
        _assert_default_source_name(self, name, 1)

    def test_one_to_many_source_names_unique(self):
        """一对多：同一源 cluster_id 的各 task source_name 仍须互不相同。"""
        details = {
            "migrate_topology": MigrateTopology.ONE_TO_MANY.value,
            "one_to_many": {
                "src_info": {"cluster_id": 7},
                "dst_infos": [
                    {"cluster_id": 8, "task_name": "mysql-dts-1-7-8"},
                    {"cluster_id": 9, "task_name": "mysql-dts-1-7-9"},
                ],
            },
        }
        plan = build_migrate_plan(details)
        names = [ts.sources[0].source_name for ts in plan.task_specs]
        self.assertEqual(len(names), 2)
        self.assertEqual(len(set(names)), 2)
        for name in names:
            _assert_default_source_name(self, name, 7)

    def test_layered_target_spider_in_plan(self):
        """U2：分层 details 透传 target_spider 至 DtsTaskSpec。"""
        details = {
            "dts_resource": {"dts_cluster_id": 9},
            "migrate": {
                "topology": MigrateTopology.ONE_TO_ONE.value,
                "one_to_one": {
                    "task_name": "mysql-dts-18801-100-200",
                    "source": {"cluster_id": 100},
                    "target": {"cluster_id": 200, "target_spider": "127.0.0.1:25000"},
                },
            },
            "task": {"full_load": {"engine": "builtin"}},
        }
        plan = build_migrate_plan(details, require_task_name=False)
        self.assertEqual(plan.task_specs[0].target_spider, "127.0.0.1:25000")

    def test_flat_dst_info_target_spider(self):
        details = {
            "migrate_topology": MigrateTopology.ONE_TO_ONE.value,
            "one_to_one": {
                "task_name": "mysql-dts-1-1-2",
                "src_info": {"cluster_id": 1},
                "dst_info": {"cluster_id": 2, "target_spider": "127.0.0.2:25000"},
            },
        }
        plan = build_migrate_plan(details)
        self.assertEqual(plan.task_specs[0].target_spider, "127.0.0.2:25000")

    def test_dts_task_spec_round_trip_target_spider(self):
        from backend.flow.utils.mysql.dts.migrate_plan import DtsTaskConfig, DtsTaskSpec, SourceSpec

        spec = DtsTaskSpec(
            task_name="t1",
            target_cluster_id=200,
            sources=[SourceSpec(cluster_id=100, source_name="src-100-abc", sync_scope=SyncScope())],
            target_spider="127.0.0.1:25000",
            dts_task_config=DtsTaskConfig(),
        )
        restored = dts_task_spec_from_dict(dts_task_spec_to_dict(spec))
        self.assertEqual(restored.target_spider, "127.0.0.1:25000")

    def test_one_to_many_independent_target_spider(self):
        details = {
            "migrate_topology": MigrateTopology.ONE_TO_MANY.value,
            "one_to_many": {
                "src_info": {"cluster_id": 7},
                "dst_infos": [
                    {"cluster_id": 8, "task_name": "mysql-dts-1-7-8", "target_spider": "127.0.0.1:25000"},
                    {"cluster_id": 9, "task_name": "mysql-dts-1-7-9", "target_spider": "127.0.0.2:25000"},
                ],
            },
        }
        plan = build_migrate_plan(details)
        self.assertEqual(plan.task_specs[0].target_spider, "127.0.0.1:25000")
        self.assertEqual(plan.task_specs[1].target_spider, "127.0.0.2:25000")


class SyncScopeMappingTest(SimpleTestCase):
    """L1：S1–S7 sync_scope → table_migrate_rule 映射验收。"""

    def _dump_rules(self, scenario_id: str, scope: SyncScope, rules):
        payload = [
            {
                "source": r.source.model_dump(),
                "target": r.target.model_dump() if r.target else None,
            }
            for r in rules
        ]
        print(f"[DTS-UT][{scenario_id}] RULES {payload}")

    def test_s1_do_dbs_partial_database(self):
        scope = SyncScope(do_dbs=["dts_ut_db_a", "dts_ut_db_b"])
        rules = _build_table_migrate_rules("src-ut", scope)
        self._dump_rules("S1", scope, rules)
        self.assertEqual(len(rules), 2)
        self.assertEqual({r.source.schema for r in rules}, {"dts_ut_db_a", "dts_ut_db_b"})
        self.assertTrue(all(r.source.table == "*" for r in rules))

    def test_s2_do_tables_partial_table(self):
        scope = SyncScope(do_tables=[{"db": "dts_ut_db_c", "table": "t1"}])
        rules = _build_table_migrate_rules("src-ut", scope)
        self._dump_rules("S2", scope, rules)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].source.schema, "dts_ut_db_c")
        self.assertEqual(rules[0].source.table, "t1")

    def test_s3_full_db_wildcard_route(self):
        scope = SyncScope(
            table_routes=[{"source_db": "dts_ut_db_full", "source_table": "*"}],
        )
        rules = _build_table_migrate_rules("src-ut", scope)
        self._dump_rules("S3", scope, rules)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].source.schema, "dts_ut_db_full")
        self.assertEqual(rules[0].source.table, "*")

    def test_s4_rename_table(self):
        scope = SyncScope(
            table_routes=[
                {
                    "source_db": "dts_ut_db_r",
                    "source_table": "t_old",
                    "target_db": "dts_ut_db_r",
                    "target_table": "t_new",
                }
            ],
        )
        rules = _build_table_migrate_rules("src-ut", scope)
        self._dump_rules("S4", scope, rules)
        self.assertEqual(len(rules), 1)
        self.assertIsNotNone(rules[0].target)
        self.assertEqual(rules[0].target.schema, "dts_ut_db_r")
        self.assertEqual(rules[0].target.table, "t_new")

    def test_s5_rename_database(self):
        scope = SyncScope(
            table_routes=[
                {
                    "source_db": "dts_ut_src",
                    "source_table": "t1",
                    "target_db": "dts_ut_dst",
                    "target_table": "t1",
                }
            ],
        )
        rules = _build_table_migrate_rules("src-ut", scope)
        self._dump_rules("S5", scope, rules)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].source.schema, "dts_ut_src")
        self.assertEqual(rules[0].target.schema, "dts_ut_dst")

    def test_s6_ignore_dbs_whitelist_subtract(self):
        scope = SyncScope(do_dbs=["dts_ut_db_a", "dts_ut_db_b"], ignore_dbs=["dts_ut_db_b"])
        rules = _build_table_migrate_rules("src-ut", scope)
        self._dump_rules("S6", scope, rules)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].source.schema, "dts_ut_db_a")

    def test_s7_empty_scope_yields_no_rules(self):
        scope = SyncScope()
        rules = _build_table_migrate_rules("src-ut", scope)
        self._dump_rules("S7", scope, rules)
        self.assertEqual(rules, [])

    def test_build_task_rejects_empty_rules(self):
        from backend.components.mysqldtsapi.types import TargetConfig
        from backend.flow.utils.mysql.dts.constants import DtsLifecycleMode, MigrateTopology, MigrateType
        from backend.flow.utils.mysql.dts.migrate_helper import build_dts_task_request
        from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan, DtsTaskConfig, DtsTaskSpec, SourceSpec

        plan = DtsMigratePlan(
            topology=MigrateTopology.ONE_TO_ONE.value,
            migrate_type=MigrateType.MYSQL_TO_MYSQL.value,
            dts_cluster_id=None,
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
            task_name="reject-empty",
            target_cluster_id=0,
            sources=[SourceSpec(cluster_id=0, source_name="src-1", sync_scope=SyncScope())],
            target_config=TargetConfig(host="127.0.0.1", port=3306, user="u", password="p", cluster_type="mysql"),
        )
        with self.assertRaises(ValueError):
            build_dts_task_request(plan, task_spec, user="u", password="p")

    def test_do_dbs_to_table_migrate_rules(self):
        scope = SyncScope(do_dbs=["db_a", "db_b"], ignore_dbs=["db_b"])
        rules = _build_table_migrate_rules("src-1", scope)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].source.source_name, "src-1")
        self.assertEqual(rules[0].source.schema, "db_a")
        self.assertEqual(rules[0].source.table, "*")

    def test_table_routes_preferred(self):
        scope = SyncScope(
            do_dbs=["db_a"],
            table_routes=[{"source_db": "db_x", "source_table": "t1", "target_db": "db_y"}],
        )
        rules = _build_table_migrate_rules("src-1", scope)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].source.schema, "db_x")

    def test_table_route_dataclass_and_pattern_priority(self):
        from backend.flow.utils.mysql.dts.migrate_plan import TableRoute

        scope = SyncScope(
            table_routes=[
                TableRoute(
                    source_db="ignored_db",
                    source_db_pattern="shard_*",
                    source_table="ignored_t",
                    source_table_pattern="t_*",
                    target_db="dst",
                )
            ]
        )
        self.assertIsInstance(scope.table_routes[0], TableRoute)
        self.assertEqual(scope.table_routes[0].source_schema(), "shard_*")
        self.assertEqual(scope.table_routes[0].source_table_name(), "t_*")
        rules = _build_table_migrate_rules("src-1", scope)
        self.assertEqual(rules[0].source.schema, "shard_*")
        self.assertEqual(rules[0].source.table, "t_*")
        self.assertEqual(rules[0].target.schema, "dst")

    def test_sync_scope_to_dict_serializes_table_routes(self):
        from backend.flow.utils.mysql.dts.cutover_helper import sync_scope_to_dict

        scope = SyncScope(table_routes=[{"source_db": "app", "source_table": "t1", "target_db": "app2"}])
        payload = sync_scope_to_dict(scope)
        self.assertEqual(
            payload["table_routes"],
            [
                {
                    "source_name": "",
                    "source_db": "app",
                    "source_db_pattern": "",
                    "source_table": "t1",
                    "source_table_pattern": "",
                    "target_db": "app2",
                    "target_table": "",
                }
            ],
        )


class ProbeSourceEnableGtidTest(SimpleTestCase):
    """探测源/目标 gtid_mode → enable_gtid（双方都 ON 才开）。"""

    @staticmethod
    def _rpc_resp(value: str | None, *, error: str = ""):
        rows = []
        if value is not None:
            rows = [{"Variable_name": "gtid_mode", "Value": value}]
        return [
            {
                "error_msg": error,
                "cmd_results": [{"error_msg": "", "table_data": rows}] if not error else [],
            }
        ]

    @patch("backend.flow.utils.mysql.dts.migrate_helper.DRSApi.rpc")
    def test_gtid_on(self, mock_rpc):
        from backend.flow.utils.mysql.dts.migrate_helper import probe_instance_gtid_enabled

        mock_rpc.return_value = self._rpc_resp("ON")
        self.assertTrue(probe_instance_gtid_enabled(host="127.0.0.1", port=3306, bk_cloud_id=0))

    @patch("backend.flow.utils.mysql.dts.migrate_helper.DRSApi.rpc")
    def test_gtid_off(self, mock_rpc):
        from backend.flow.utils.mysql.dts.migrate_helper import probe_instance_gtid_enabled

        mock_rpc.return_value = self._rpc_resp("OFF")
        self.assertFalse(probe_instance_gtid_enabled(host="127.0.0.1", port=3306, bk_cloud_id=0))

    @patch("backend.flow.utils.mysql.dts.migrate_helper.DRSApi.rpc")
    def test_gtid_variable_missing(self, mock_rpc):
        from backend.flow.utils.mysql.dts.migrate_helper import probe_instance_gtid_enabled

        mock_rpc.return_value = self._rpc_resp(None)
        self.assertFalse(probe_instance_gtid_enabled(host="127.0.0.1", port=3306, bk_cloud_id=0))

    @patch("backend.flow.utils.mysql.dts.migrate_helper.DRSApi.rpc")
    def test_gtid_probe_exception_defaults_false(self, mock_rpc):
        from backend.flow.utils.mysql.dts.migrate_helper import probe_instance_gtid_enabled

        mock_rpc.side_effect = RuntimeError("drs down")
        self.assertFalse(probe_instance_gtid_enabled(host="127.0.0.1", port=3306, bk_cloud_id=0))

    @patch("backend.flow.utils.mysql.dts.migrate_helper.probe_instance_gtid_enabled")
    def test_decide_requires_source_and_target_both_on(self, mock_probe):
        from types import SimpleNamespace

        from backend.flow.utils.mysql.dts.migrate_helper import decide_enable_gtid

        # source ON, first target ON, second target OFF → False
        mock_probe.side_effect = [True, True, False]
        source_cluster = SimpleNamespace(id=1, bk_cloud_id=0)
        target_cluster = SimpleNamespace(id=2, bk_cloud_id=0, cluster_type="tendbha")
        master = SimpleNamespace(machine=SimpleNamespace(ip="127.0.0.2"), port=3306)
        target_cluster.storageinstance_set = SimpleNamespace(
            filter=lambda **kwargs: SimpleNamespace(first=lambda: master)
        )

        with patch(
            "backend.flow.utils.mysql.dts.migrate_helper._collect_target_gtid_probe_endpoints",
            return_value=[("127.0.0.2", 3306, 0), ("127.0.0.3", 3306, 0)],
        ):
            self.assertFalse(
                decide_enable_gtid(
                    source_host="127.0.0.1",
                    source_port=3306,
                    source_cluster=source_cluster,
                    target_cluster=target_cluster,
                    migrate_type="mysql_to_mysql",
                )
            )

    @patch("backend.flow.utils.mysql.dts.migrate_helper.probe_instance_gtid_enabled")
    def test_decide_both_on(self, mock_probe):
        from types import SimpleNamespace

        from backend.flow.utils.mysql.dts.migrate_helper import decide_enable_gtid

        mock_probe.return_value = True
        source_cluster = SimpleNamespace(id=1, bk_cloud_id=0)
        target_cluster = SimpleNamespace(id=2, bk_cloud_id=0)
        with patch(
            "backend.flow.utils.mysql.dts.migrate_helper._collect_target_gtid_probe_endpoints",
            return_value=[("127.0.0.2", 3306, 0)],
        ):
            self.assertTrue(
                decide_enable_gtid(
                    source_host="127.0.0.1",
                    source_port=3306,
                    source_cluster=source_cluster,
                    target_cluster=target_cluster,
                    migrate_type="mysql_to_mysql",
                )
            )

    @patch("backend.flow.utils.mysql.dts.migrate_helper.probe_instance_gtid_enabled")
    def test_decide_no_target_cluster_false(self, mock_probe):
        from types import SimpleNamespace

        from backend.flow.utils.mysql.dts.migrate_helper import decide_enable_gtid

        mock_probe.return_value = True
        source_cluster = SimpleNamespace(id=1, bk_cloud_id=0)
        self.assertFalse(
            decide_enable_gtid(
                source_host="127.0.0.1",
                source_port=3306,
                source_cluster=source_cluster,
                target_cluster=None,
                migrate_type="mysql_to_mysql",
            )
        )


class MigrateCredentialsTest(SimpleTestCase):
    def test_generate_dts_migrate_username_length_and_format(self):
        """旧版 MySQL 用户名 ≤16；格式 {prefix}{suffix}，suffix 固定长度小写随机串。"""
        self.assertLessEqual(
            len(MYSQL_DTS_MIGRATE_USER_PREFIX) + MYSQL_DTS_MIGRATE_USER_SUFFIX_LENGTH,
            MYSQL_DTS_MIGRATE_USER_MAX_LENGTH,
        )
        users = {generate_dts_migrate_username() for _ in range(20)}
        self.assertGreaterEqual(len(users), 2)
        for user in users:
            self.assertTrue(user.startswith(MYSQL_DTS_MIGRATE_USER_PREFIX))
            self.assertLessEqual(len(user), MYSQL_DTS_MIGRATE_USER_MAX_LENGTH)
            self.assertEqual(len(user), len(MYSQL_DTS_MIGRATE_USER_PREFIX) + MYSQL_DTS_MIGRATE_USER_SUFFIX_LENGTH)
            suffix = user[len(MYSQL_DTS_MIGRATE_USER_PREFIX) :]
            self.assertTrue(suffix.islower())
            self.assertTrue(suffix.isalnum())

    def test_generate_dts_migrate_credentials(self):
        user, password = generate_dts_migrate_credentials()
        self.assertTrue(user.startswith(MYSQL_DTS_MIGRATE_USER_PREFIX))
        self.assertLessEqual(len(user), MYSQL_DTS_MIGRATE_USER_MAX_LENGTH)
        self.assertGreaterEqual(len(password), 16)

    def test_build_dts_drop_user_uses_same_username(self):
        """drop 路径不二次生成用户名，直接使用创建时写入的 dts_user。"""
        from backend.flow.utils.mysql.dts.migrate_credentials import build_dts_drop_user_parallel_acts

        dts_user = generate_dts_migrate_username()
        acts = build_dts_drop_user_parallel_acts(
            dts_user=dts_user,
            grant_hosts=["127.0.0.3"],
            grant_targets=[{"bk_cloud_id": 0, "address": "127.0.0.2:20000", "cluster_id": 1}],
        )
        self.assertEqual(acts[0]["kwargs"]["user"], dts_user)
        self.assertLessEqual(len(acts[0]["kwargs"]["user"]), MYSQL_DTS_MIGRATE_USER_MAX_LENGTH)

    def test_verify_max_retries_defined(self):
        self.assertGreaterEqual(MYSQL_DTS_VERIFY_MAX_RETRIES, 1)

    def test_resolve_dts_grant_hosts_from_deploy(self):
        from backend.flow.utils.mysql.dts.context import DtsHostSpec, MysqlDtsDeploySubflowInput
        from backend.flow.utils.mysql.dts.migrate_credentials import resolve_dts_grant_hosts
        from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan, DtsTaskConfig

        plan = DtsMigratePlan(
            topology="one_to_one",
            migrate_type="mysql_to_mysql",
            dts_cluster_id=None,
            dts_lifecycle="deploy",
            auto_deploy_dts=True,
            deploy_subflow_inp=MysqlDtsDeploySubflowInput(
                root_id="r1",
                bk_biz_id=20,
                bk_cloud_id=0,
                cluster_name="dts-1",
                master_hosts=[DtsHostSpec(ip="127.0.0.2", bk_cloud_id=0)],
                worker_hosts=[
                    DtsHostSpec(ip="127.0.0.3", bk_cloud_id=0),
                    DtsHostSpec(ip="127.0.0.4", bk_cloud_id=0),
                ],
            ),
            cleanup_after_migrate=True,
            recycle_dts_hosts=True,
            dts_task_config=DtsTaskConfig(),
            task_specs=[],
            worker_count_required=2,
        )
        # Worker ∪ Master（cutover 从 dts-master 连源加锁需要 master@host）
        self.assertEqual(resolve_dts_grant_hosts(plan), ["127.0.0.2", "127.0.0.3", "127.0.0.4"])

    def test_build_dts_drop_user_parallel_acts(self):
        from backend.flow.utils.mysql.dts.migrate_credentials import build_dts_drop_user_parallel_acts

        acts = build_dts_drop_user_parallel_acts(
            dts_user="dts_migrate_abc",
            grant_hosts=["127.0.0.3"],
            grant_targets=[{"bk_cloud_id": 0, "address": "127.0.0.2:20000", "cluster_id": 1}],
            ignore_errors=True,
        )
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0]["act_component_code"], "mysql_drop_user")
        self.assertTrue(acts[0]["kwargs"]["ignore_errors"])
        self.assertEqual(acts[0]["kwargs"]["host"], "127.0.0.3")

    def test_extract_temp_account_snapshot_from_node_inputs(self):
        from backend.flow.utils.mysql.dts.migrate_credentials import extract_temp_account_snapshot_from_node_inputs

        snap = extract_temp_account_snapshot_from_node_inputs(
            {
                "trans_data": {
                    "migrate_context": {
                        "dts_user": "dts_m_abc",
                        "grant_hosts": ["127.0.0.3"],
                        "grant_targets": [{"bk_cloud_id": 0, "address": "127.0.0.2:20000", "cluster_id": 1}],
                    }
                }
            }
        )
        self.assertEqual(snap["user"], "dts_m_abc")
        self.assertIsNone(extract_temp_account_snapshot_from_node_inputs({"trans_data": {}}))

    @patch("backend.components.DRSApi.rpc")
    def test_best_effort_drop_ignores_unknown_user(self, mock_rpc):
        from backend.flow.utils.mysql.dts.migrate_credentials import best_effort_drop_dts_temp_accounts_from_snapshots

        mock_rpc.return_value = [
            {"error_msg": "", "cmd_results": [{"error_msg": "ERROR 1396 (HY000): Operation DROP USER failed"}]}
        ]
        # 用户不存在类错误应被忽略，不向外抛
        best_effort_drop_dts_temp_accounts_from_snapshots(
            [
                {
                    "user": "dts_m_gone",
                    "grant_hosts": ["127.0.0.3"],
                    "grant_targets": [{"bk_cloud_id": 0, "address": "127.0.0.2:20000"}],
                }
            ]
        )
        mock_rpc.assert_called_once()


class DeployHelperTest(SimpleTestCase):
    def test_group_deploy_hosts_colocated(self):
        master_hosts = [DtsHostSpec(ip="127.0.0.1", bk_cloud_id=0)]
        worker_hosts = [DtsHostSpec(ip="127.0.0.1", bk_cloud_id=0)]
        plan = group_deploy_hosts(master_hosts, worker_hosts)
        self.assertEqual(len(plan.colocated_hosts), 1)
        self.assertEqual(len(plan.master_only_hosts), 0)
        self.assertEqual(len(plan.worker_only_hosts), 0)

    def test_render_master_config(self):
        content = render_master_config(
            deploy_path="/data/dts/test/",
            node_name=build_master_node_name(1),
            advertise_ip="127.0.0.1",
        )
        self.assertIn("dm-master-1", content)
        self.assertIn("/data/dts/test/", content)
        self.assertIn("master-addr", content)
        self.assertIn("peer-urls", content)
        self.assertIn("log-file", content)
        self.assertNotIn("[log]", content)
        self.assertNotIn("[security]", content)


class InferDtsResourceIntentTest(SimpleTestCase):
    def test_id_only(self):
        intent = infer_dts_resource_intent({"dts_cluster_id": 2})
        self.assertEqual(intent.kind, DtsLifecycleMode.USE_EXISTING.value)
        self.assertFalse(intent.default_cleanup)
        self.assertEqual(intent.dts_cluster_id, 2)
        self.assertIsNone(intent.deploy)

    def test_deploy_only(self):
        deploy = {"cluster_name": "dts-1", "master_hosts": [{"ip": "127.0.0.2"}]}
        intent = infer_dts_resource_intent({"deploy": deploy})
        self.assertEqual(intent.kind, DtsLifecycleMode.DEPLOY.value)
        self.assertTrue(intent.default_cleanup)
        self.assertIsNone(intent.dts_cluster_id)
        self.assertEqual(intent.deploy, deploy)

    def test_deploy_destroy_defaults_cleanup_false(self):
        intent = infer_dts_resource_intent({"deploy": {"cluster_name": "dts-1"}, "destroy_after_migrate": True})
        self.assertEqual(intent.kind, DtsLifecycleMode.DEPLOY.value)
        self.assertFalse(intent.default_cleanup)

    def test_both_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            infer_dts_resource_intent({"dts_cluster_id": 2, "deploy": {"cluster_name": "x"}})
        self.assertIn("不能同时", str(ctx.exception))

    def test_neither_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            infer_dts_resource_intent({})
        self.assertIn("之一", str(ctx.exception))

    def test_legacy_mode_rejected(self):
        with self.assertRaises(ValueError):
            infer_dts_resource_intent({"mode": "deploy_ephemeral", "deploy": {"cluster_name": "x"}})

    def test_mode_conflicts_with_fields(self):
        with self.assertRaises(ValueError) as ctx:
            infer_dts_resource_intent({"mode": DtsLifecycleMode.USE_EXISTING.value, "deploy": {"cluster_name": "x"}})
        self.assertIn("不一致", str(ctx.exception))

    def test_wrap_plan_auto_deploy_defaults_cleanup(self):
        plan = build_migrate_plan(
            {
                "migrate_topology": MigrateTopology.ONE_TO_ONE.value,
                "auto_deploy_dts": True,
                "one_to_one": {
                    "task_name": "mysql-dts-1-1-2",
                    "src_info": {"cluster_id": 1},
                    "dst_info": {"cluster_id": 2},
                },
            }
        )
        self.assertEqual(plan.dts_lifecycle, DtsLifecycleMode.DEPLOY.value)
        self.assertTrue(plan.cleanup_after_migrate)


class MultiRowMigratePlanTest(SimpleTestCase):
    def _infos_row(self, src, dst, *, cluster_name="", master_ip="127.0.0.2", worker_ip="127.0.0.3"):
        deploy = {
            "bk_cloud_id": 0,
            "master_hosts": [{"ip": master_ip, "bk_cloud_id": 0}],
            "worker_hosts": [{"ip": worker_ip, "bk_cloud_id": 0}],
        }
        if cluster_name:
            deploy["cluster_name"] = cluster_name
        return {
            "dts_resource": {"deploy": deploy},
            "migrate": {
                "topology": MigrateTopology.ONE_TO_ONE.value,
                "one_to_one": {
                    "task_name": f"mysql-dts-12-{src}-{dst}",
                    "source": {"cluster_id": src},
                    "target": {"cluster_id": dst},
                },
            },
        }

    def test_build_migrate_plans_two_deploy_rows(self):
        details = {
            "ticket_id": 19943,
            "bk_biz_id": 1,
            "infos": [
                self._infos_row(100, 200, master_ip="127.0.0.2", worker_ip="127.0.0.3"),
                self._infos_row(101, 201, master_ip="127.0.0.4", worker_ip="127.0.0.5"),
            ],
        }
        plans = build_migrate_plans(details)
        self.assertEqual(len(plans), 2)
        self.assertEqual(plans[0].task_specs[0].sources[0].cluster_id, 100)
        self.assertEqual(plans[1].task_specs[0].target_cluster_id, 201)
        name0 = plans[0].deploy_subflow_inp.cluster_name
        name1 = plans[1].deploy_subflow_inp.cluster_name
        self.assertRegex(name0, r"^dts-migrate-19943-0-[0-9a-f]{12}$")
        self.assertRegex(name1, r"^dts-migrate-19943-1-[0-9a-f]{12}$")
        self.assertNotEqual(name0, name1)
        self.assertFalse(plans[0].cleanup_after_migrate)
        self.assertTrue(plans[0].recycle_dts_hosts)

    def test_iter_rows_injects_ticket_lifecycle(self):
        details = {
            "ticket_id": 19943,
            "bk_biz_id": 1,
            "destroy_after_migrate": False,
            "recycle_hosts": False,
            "cleanup_after_migrate": True,
            "infos": [
                self._infos_row(100, 200, master_ip="127.0.0.2", worker_ip="127.0.0.3"),
                self._infos_row(101, 201, master_ip="127.0.0.4", worker_ip="127.0.0.5"),
            ],
        }
        rows = iter_migrate_row_details(details)
        for row in rows:
            resource = row["dts_resource"]
            self.assertFalse(resource["destroy_after_migrate"])
            self.assertFalse(resource["recycle_hosts"])
            self.assertTrue(resource["cleanup_after_migrate"])
        self.assertNotIn("destroy_after_migrate", details["infos"][0]["dts_resource"])
        plans = build_migrate_plans(details)
        self.assertTrue(plans[0].cleanup_after_migrate)
        self.assertFalse(plans[0].recycle_dts_hosts)
        self.assertTrue(plans[1].cleanup_after_migrate)
        self.assertFalse(plans[1].recycle_dts_hosts)

    def test_patch_same_src_dst_cluster_names_get_random(self):
        """同源同目标、迁移对象不同：两行 deploy cluster_name 仍须唯一。"""
        details = {
            "infos": [
                self._infos_row(100, 200, cluster_name="gamedb.src", master_ip="127.0.0.2", worker_ip="127.0.0.3"),
                self._infos_row(100, 200, cluster_name="gamedb.src", master_ip="127.0.0.4", worker_ip="127.0.0.5"),
            ]
        }
        patch_deploy_cluster_names_into_details(details, 19943)
        name0 = details["infos"][0]["dts_resource"]["deploy"]["cluster_name"]
        name1 = details["infos"][1]["dts_resource"]["deploy"]["cluster_name"]
        self.assertRegex(name0, r"^gamedb.src-[0-9a-f]{12}$")
        self.assertRegex(name1, r"^gamedb.src-[0-9a-f]{12}$")
        self.assertNotEqual(name0, name1)
        patch_deploy_cluster_names_into_details(details, 19943)
        self.assertEqual(details["infos"][0]["dts_resource"]["deploy"]["cluster_name"], name0)
        self.assertEqual(details["infos"][1]["dts_resource"]["deploy"]["cluster_name"], name1)

    def test_single_row_keeps_ticket_cluster_name(self):
        details = {
            "ticket_id": 12,
            "bk_biz_id": 1,
            "dts_resource": {
                "deploy": {
                    "bk_cloud_id": 0,
                    "master_hosts": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
                    "worker_hosts": [{"ip": "127.0.0.3", "bk_cloud_id": 0}],
                }
            },
            "migrate": {
                "topology": MigrateTopology.ONE_TO_ONE.value,
                "one_to_one": {
                    "task_name": "mysql-dts-12-1-2",
                    "source": {"cluster_id": 1},
                    "target": {"cluster_id": 2},
                },
            },
        }
        plans = build_migrate_plans(details)
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].deploy_subflow_inp.cluster_name, "dts-migrate-12")

    def test_build_migrate_plan_rejects_infos(self):
        with self.assertRaises(ValueError) as ctx:
            build_migrate_plan({"infos": [self._infos_row(1, 2)]})
        self.assertIn("build_migrate_plans", str(ctx.exception))


class RenameMigrateTypeHelperTest(SimpleTestCase):
    def test_is_real_rename_route(self):
        self.assertTrue(is_real_rename_route(TableRoute(source_db="a", target_db="b")))
        self.assertTrue(is_real_rename_route(TableRoute(source_db="a", source_table="t1", target_table="t2")))
        self.assertFalse(is_real_rename_route(TableRoute(source_db="a", source_table="t1")))
        self.assertFalse(
            is_real_rename_route(TableRoute(source_db="a", source_table="t1", target_db="a", target_table="t1"))
        )

    def test_infer_rename_migrate_type(self):
        self.assertEqual(
            infer_rename_migrate_type({ClusterType.TenDBHA.value}, ClusterType.TenDBHA.value),
            MigrateType.MYSQL_TO_MYSQL.value,
        )
        self.assertEqual(
            infer_rename_migrate_type({ClusterType.TenDBHA.value}, ClusterType.TenDBCluster.value),
            MigrateType.HA_TO_CLUSTER.value,
        )
        with self.assertRaises(ValueError):
            infer_rename_migrate_type({ClusterType.TenDBCluster.value}, ClusterType.TenDBHA.value)


class TicketLifecyclePolicyTest(SimpleTestCase):
    """P2-8：单行读 dts_resource，多行读单据顶层，同一套默认值。"""

    def test_infos_reads_top_level(self):
        details = {
            "destroy_after_migrate": False,
            "recycle_hosts": False,
            "cleanup_after_migrate": True,
            "infos": [{"dts_resource": {"dts_cluster_id": 1, "destroy_after_migrate": True}}],
        }
        self.assertEqual(
            resolve_ticket_lifecycle(details),
            {"destroy_after_migrate": False, "recycle_hosts": False, "cleanup_after_migrate": True},
        )
        self.assertEqual(
            resolve_ticket_destroy_policy(details),
            {"destroy_after_migrate": False, "recycle_hosts": False},
        )

    def test_single_row_reads_dts_resource_not_top_level(self):
        details = {
            "destroy_after_migrate": False,
            "recycle_hosts": False,
            "cleanup_after_migrate": True,
            "dts_resource": {"dts_cluster_id": 1, "destroy_after_migrate": True, "recycle_hosts": True},
        }
        self.assertEqual(
            resolve_ticket_lifecycle(details),
            {"destroy_after_migrate": True, "recycle_hosts": True, "cleanup_after_migrate": False},
        )
        self.assertEqual(
            resolve_ticket_destroy_policy(details),
            {"destroy_after_migrate": True, "recycle_hosts": True},
        )

    def test_defaults(self):
        infos_defaults = resolve_ticket_lifecycle({"infos": [{"dts_resource": {"dts_cluster_id": 1}}]})
        single_defaults = resolve_ticket_lifecycle({"dts_resource": {"dts_cluster_id": 1}})
        expected = {"destroy_after_migrate": True, "recycle_hosts": True, "cleanup_after_migrate": False}
        self.assertEqual(infos_defaults, expected)
        self.assertEqual(single_defaults, expected)
