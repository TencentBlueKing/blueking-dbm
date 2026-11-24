# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import importlib
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.utils import timezone

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_report.enums import MysqlConfigConsistencySubType, ReportStateType


def _load_modules():
    """延迟加载 local_tasks 下模块，并屏蔽 register_periodic_task 在单测时的写库行为。"""
    with (
        patch("backend.db_periodic_task.models.DBPeriodicTask.create_or_update_periodic_task"),
        patch("backend.db_periodic_task.models.DBPeriodicTask.delete_legacy_periodic_task"),
    ):
        config_mod = importlib.import_module("backend.db_periodic_task.local_tasks.mysql_config_consistency.config")
        checker_mod = importlib.import_module("backend.db_periodic_task.local_tasks.mysql_config_consistency.checker")
        tasks_mod = importlib.import_module("backend.db_periodic_task.local_tasks.mysql_config_consistency.tasks")
    return config_mod, checker_mod, tasks_mod


class _BaseConsistencyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config_mod, cls.checker_mod, cls.tasks_mod = _load_modules()


class TestMysqlConfigConsistencyConfig(_BaseConsistencyTest):
    def test_default_whitelist_excludes_sync_binlog_and_flush_log(self):
        cfg = self.config_mod.MysqlConfigConsistencyConfig()
        self.assertNotIn("sync_binlog", cfg.storage_whitelist)
        self.assertNotIn("innodb_flush_log_at_trx_commit", cfg.storage_whitelist)
        self.assertNotIn("gtid_mode", cfg.storage_whitelist)
        self.assertNotIn("enforce_gtid_consistency", cfg.storage_whitelist)
        self.assertIn("sql_mode", cfg.storage_whitelist)
        self.assertIn("spider_bgs_mode", cfg.spider_whitelist)
        # 模拟执行 4 项全部归入存储高危项
        for var_name in (
            "innodb_large_prefix",
            "innodb_strict_mode",
            "rocksdb_large_prefix",
            "rocksdb_strict_collation_check",
        ):
            self.assertIn(var_name, self.config_mod.STORAGE_HIGH_IMPACT_VARS)
            self.assertNotIn(var_name, self.config_mod.STORAGE_WARN_VARS)
        self.assertEqual(cfg.retention_days, 90)
        self.assertTrue(cfg.check_spider_version)
        self.assertIn("version", cfg.tendbcluster_query_variables)
        self.assertNotIn("version", cfg.spider_whitelist)
        cfg_no_ver = self.config_mod.MysqlConfigConsistencyConfig(check_spider_version=False)
        self.assertNotIn("version", cfg_no_ver.tendbcluster_query_variables)

    def test_from_settings_override(self):
        override = {
            "enabled": False,
            "bizs_ignored": [100],
            "clusters_ignored": [200],
            "check_spider_version": False,
            # 白名单变量不允许通过 SystemSettings 覆盖，应被忽略
            "storage_warn_vars": ["wait_timeout"],
            "storage_high_impact_vars": ["sql_mode"],
            "spider_high_impact_vars": ["sql_mode"],
            "spider_warn_vars": ["wait_timeout"],
            "bool_normalize_vars": [],
            "retention_days": None,
            "dispatch_window_seconds": None,
            "unknown_key": "ignored",
        }
        with patch.object(self.config_mod.SystemSettings, "get_setting_value", return_value=override):
            cfg = self.config_mod.MysqlConfigConsistencyConfig.from_settings()
        self.assertFalse(cfg.enabled)
        self.assertEqual(cfg.bizs_ignored, [100])
        self.assertEqual(cfg.clusters_ignored, [200])
        self.assertFalse(cfg.check_spider_version)
        self.assertEqual(cfg.retention_days, 90)
        self.assertEqual(cfg.dispatch_window_seconds, 1800)
        self.assertEqual(
            cfg.storage_whitelist,
            self.config_mod._dedup_vars(self.config_mod.STORAGE_HIGH_IMPACT_VARS, self.config_mod.STORAGE_WARN_VARS),
        )
        self.assertEqual(
            cfg.spider_whitelist,
            self.config_mod._dedup_vars(self.config_mod.SPIDER_HIGH_IMPACT_VARS, self.config_mod.SPIDER_WARN_VARS),
        )


class TestEvaluators(_BaseConsistencyTest):
    def test_tendbha_normal_warning_abnormal_and_errors(self):
        normal = self.checker_mod.evaluate_tendbha_diff({"replication_pairs": []})
        self.assertEqual(normal.state, ReportStateType.NORMAL.value)
        self.assertEqual(normal.diff_count, 0)
        self.assertEqual(normal.diff_variables, [])

        warn = self.checker_mod.evaluate_tendbha_diff(
            {
                "replication_pairs": [
                    {
                        "scope": "master_slave",
                        "master": "127.0.0.1:20000",
                        "slave": "127.0.0.2:20000",
                        "mismatches": [
                            {
                                "variable_name": "wait_timeout",
                                "master_value": "28800",
                                "slave_value": "3600",
                                "severity": "warn",
                            }
                        ],
                    }
                ]
            }
        )
        self.assertEqual(warn.state, ReportStateType.WARNING.value)
        self.assertEqual(warn.diff_count, 1)
        self.assertEqual(warn.high_impact_count, 0)
        self.assertEqual(warn.diff_variables, ["wait_timeout"])

        abnormal = self.checker_mod.evaluate_tendbha_diff(
            {
                "replication_pairs": [
                    {
                        "scope": "replica_group",
                        "master": "127.0.0.1:20000",
                        "affected_slaves": ["127.0.0.2:20000", "127.0.0.3:20000"],
                        "mismatches": [
                            {
                                "variable_name": "sql_mode",
                                "master_value": "STRICT",
                                "slave_value": "TRADITIONAL",
                                "severity": "high",
                            }
                        ],
                    }
                ]
            },
            addr_errors={"127.0.0.4:20000": "timeout"},
        )
        self.assertEqual(abnormal.state, ReportStateType.ABNORMAL.value)
        self.assertEqual(abnormal.high_impact_count, 1)
        self.assertIn("127.0.0.4:20000", abnormal.msg)

    def test_tendbcluster_spider_version_and_group_mismatch(self):
        diff_res = {
            "spider_version": {
                "consistent": False,
                "by_version": {
                    "tspider-3.7.5": ["127.0.0.10:25000"],
                    "tspider-3.7.8": ["127.0.0.11:25000"],
                },
            },
            "spider_groups": [
                {
                    "group": "spider_master",
                    "mismatches": [
                        {
                            "variable_name": "spider_net_read_timeout",
                            "severity": "warn",
                            "by_value": {
                                "3600": ["127.0.0.10:25000"],
                                "600": ["127.0.0.11:25000"],
                            },
                        }
                    ],
                }
            ],
        }
        ev = self.checker_mod.evaluate_tendbcluster_spider_diff(
            diff_res,
            spider_errors={"127.0.0.12:25000": "timeout"},
            check_version=True,
        )
        # 版本不一致时跳过参数对比，只报 version + 保留失联错误
        self.assertEqual(ev.state, ReportStateType.ABNORMAL.value)
        self.assertEqual(ev.diff_variables, ["version"])
        self.assertEqual(ev.high_impact_count, 1)
        self.assertTrue(ev.diff_detail["skipped_param_diff"])
        self.assertEqual(ev.diff_detail["spider_groups"], [])
        self.assertIn("tspider-3.7.5", ev.msg)
        self.assertIn("127.0.0.12:25000", ev.msg)

        ev_no_ver = self.checker_mod.evaluate_tendbcluster_spider_diff(diff_res, check_version=False)
        self.assertEqual(ev_no_ver.state, ReportStateType.WARNING.value)
        self.assertEqual(ev_no_ver.diff_variables, ["spider_net_read_timeout"])
        self.assertFalse(ev_no_ver.diff_detail["skipped_param_diff"])

    def test_tendbcluster_shard_group_and_remote_master_summary(self):
        diff_res = {
            "shard_pairs": [
                {
                    "scope": "shard_group",
                    "affected_shards": ["0", "1", "2"],
                    "master": "127.0.0.20:20000",
                    "slave": "127.0.0.21:20000",
                    "mismatches": [
                        {
                            "variable_name": "character_set_server",
                            "master_value": "utf8mb4",
                            "slave_value": "utf8",
                            "severity": "high",
                        }
                    ],
                }
            ],
            "remote_master_mismatches": [
                {
                    "variable_name": "innodb_large_prefix",
                    "severity": "high",
                    "by_value": {
                        "ON": ["127.0.0.20:20000"],
                        "OFF": ["127.0.0.22:20000"],
                    },
                }
            ],
        }
        ev = self.checker_mod.evaluate_tendbcluster_shard_diff(diff_res)
        self.assertEqual(ev.state, ReportStateType.ABNORMAL.value)
        self.assertEqual(ev.diff_variables, ["character_set_server", "innodb_large_prefix"])
        self.assertEqual(ev.high_impact_count, 2)
        self.assertIn("0,1,2", ev.msg)
        self.assertIn("innodb_large_prefix", ev.msg)


class TestWeeklyFailedDays(_BaseConsistencyTest):
    def test_weekly_accumulation_same_day_rerun_and_recovery(self):
        calc = self.checker_mod.calculate_failed_days
        now = timezone.now()
        self.assertEqual(calc(None, ReportStateType.ABNORMAL.value, now), 1)

        last_abn = SimpleNamespace(
            state=ReportStateType.ABNORMAL.value, failed_days=1, create_at=now - timedelta(days=7)
        )
        self.assertEqual(calc(last_abn, ReportStateType.NORMAL.value, now), 0)
        self.assertEqual(calc(last_abn, ReportStateType.WARNING.value, now), 8)

        same_day = SimpleNamespace(
            state=ReportStateType.ABNORMAL.value, failed_days=8, create_at=now - timedelta(hours=2)
        )
        self.assertEqual(calc(same_day, ReportStateType.ABNORMAL.value, now), 8)

        last_ok = SimpleNamespace(state=ReportStateType.NORMAL.value, failed_days=0, create_at=now - timedelta(days=7))
        self.assertEqual(calc(last_ok, ReportStateType.WARNING.value, now), 1)

        stale_abn = SimpleNamespace(
            state=ReportStateType.ABNORMAL.value, failed_days=15, create_at=now - timedelta(days=14)
        )
        self.assertEqual(calc(stale_abn, ReportStateType.ABNORMAL.value, now), 1)

    def test_save_consistency_report_overwrites_existing_record_on_recovery(self):
        now = timezone.now()
        cluster = SimpleNamespace(
            id=201,
            bk_biz_id=10,
            bk_cloud_id=0,
            immute_domain="ha.recover.db",
            cluster_type=ClusterType.TenDBHA.value,
        )
        existing = MagicMock(
            state=ReportStateType.ABNORMAL.value,
            failed_days=8,
            create_at=now - timedelta(days=3),
        )
        qs = MagicMock()
        qs.order_by.return_value.first.return_value = existing

        normal_eval = self.checker_mod.CheckEvaluation(
            state=ReportStateType.NORMAL.value,
            diff_count=0,
            high_impact_count=0,
            diff_variables=[],
            msg="配置一致",
            diff_detail={},
        )

        with (
            patch.object(self.checker_mod.MysqlConfigConsistencyReport.objects, "filter", return_value=qs),
            patch.object(self.checker_mod.MysqlConfigConsistencyReport.objects, "create") as mock_create,
            patch.object(self.checker_mod.timezone, "now", return_value=now),
        ):
            res = self.checker_mod.save_consistency_report(
                cluster, MysqlConfigConsistencySubType.MASTER_SLAVE.value, normal_eval
            )

        self.assertIs(res, existing)
        mock_create.assert_not_called()
        existing.save.assert_called_once()
        self.assertEqual(existing.state, ReportStateType.NORMAL.value)
        self.assertTrue(existing.status)
        self.assertEqual(existing.failed_days, 0)
        self.assertEqual(existing.diff_variables, [])
        self.assertEqual(existing.create_at, now)
        self.assertEqual(existing.update_at, now)

    def test_save_consistency_report_handles_concurrent_integrity_error(self):
        now = timezone.now()
        cluster = SimpleNamespace(
            id=202,
            bk_biz_id=10,
            bk_cloud_id=0,
            immute_domain="ha.race.db",
            cluster_type=ClusterType.TenDBHA.value,
        )
        qs = MagicMock()
        qs.order_by.return_value.first.return_value = None
        existing = MagicMock(
            state=ReportStateType.NORMAL.value,
            failed_days=0,
            create_at=now - timedelta(days=7),
        )
        abn_eval = self.checker_mod.CheckEvaluation(
            state=ReportStateType.ABNORMAL.value,
            diff_count=1,
            high_impact_count=1,
            diff_variables=["sql_mode"],
            msg="diff",
            diff_detail={},
        )
        with (
            patch.object(self.checker_mod.MysqlConfigConsistencyReport.objects, "filter", return_value=qs),
            patch.object(
                self.checker_mod.MysqlConfigConsistencyReport.objects,
                "create",
                side_effect=self.checker_mod.IntegrityError("duplicate"),
            ),
            patch.object(self.checker_mod.MysqlConfigConsistencyReport.objects, "get", return_value=existing),
            patch.object(self.checker_mod.timezone, "now", return_value=now),
        ):
            res = self.checker_mod.save_consistency_report(
                cluster, MysqlConfigConsistencySubType.MASTER_SLAVE.value, abn_eval
            )
        self.assertIs(res, existing)
        existing.save.assert_called_once()
        self.assertEqual(existing.state, ReportStateType.ABNORMAL.value)
        self.assertEqual(existing.failed_days, 1)


class TestSingleClusterFlowAndDispatch(_BaseConsistencyTest):
    def test_should_skip_filters(self):
        cfg = self.config_mod.MysqlConfigConsistencyConfig(bizs_ignored=[99], clusters_ignored=[88])
        self.assertTrue(
            self.checker_mod.should_skip_cluster(
                SimpleNamespace(
                    id=1,
                    bk_biz_id=1,
                    cluster_type=ClusterType.TenDBSingle.value,
                    phase=ClusterPhase.ONLINE.value,
                    immute_domain="a.db",
                ),
                cfg,
            )
        )
        self.assertTrue(
            self.checker_mod.should_skip_cluster(
                SimpleNamespace(
                    id=2,
                    bk_biz_id=1,
                    cluster_type=ClusterType.TenDBHA.value,
                    phase=ClusterPhase.OFFLINE.value,
                    immute_domain="a.db",
                ),
                cfg,
            )
        )
        self.assertTrue(
            self.checker_mod.should_skip_cluster(
                SimpleNamespace(
                    id=3,
                    bk_biz_id=1,
                    cluster_type=ClusterType.TenDBHA.value,
                    phase=ClusterPhase.ONLINE.value,
                    immute_domain="foo-tmp20261124-1234567.db",
                ),
                cfg,
            )
        )
        self.assertFalse(
            self.checker_mod.should_skip_cluster(
                SimpleNamespace(
                    id=4,
                    bk_biz_id=1,
                    cluster_type=ClusterType.TenDBHA.value,
                    phase=ClusterPhase.ONLINE.value,
                    immute_domain="prod.db",
                ),
                cfg,
            )
        )

    def test_check_tendbcluster_creates_two_subtype_reports(self):
        cluster = SimpleNamespace(
            id=101,
            bk_biz_id=10,
            bk_cloud_id=0,
            immute_domain="spider.prod.db",
            cluster_type=ClusterType.TenDBCluster.value,
            phase=ClusterPhase.ONLINE.value,
        )
        fake_runtime = {
            "spiders": [
                {
                    "address": "127.0.0.10:25000",
                    "instance_role": "spider_master",
                    "machine_type": "spider",
                    "version": "tspider-3.7.8",
                    "variables": {"sql_mode": "STRICT", "spider_bgs_mode": "1"},
                },
                {
                    "address": "127.0.0.11:25000",
                    "instance_role": "spider_master",
                    "machine_type": "spider",
                    "version": "tspider-3.7.8",
                    "variables": {"sql_mode": "STRICT", "spider_bgs_mode": "0"},
                },
            ],
            "shards": {
                "0": {
                    "master": {
                        "address": "127.0.0.20:20000",
                        "instance_role": "remote_master",
                        "machine_type": "remote",
                        "variables": {"sql_mode": "STRICT"},
                    },
                    "slave": {
                        "address": "127.0.0.21:20000",
                        "instance_role": "remote_slave",
                        "machine_type": "remote",
                        "variables": {"sql_mode": "STRICT"},
                    },
                }
            },
            "errors": {"127.0.0.21:20000": "connect refused"},
        }
        saved_calls = []

        def fake_save(cluster_obj, subtype, evaluation, creator="system"):
            saved_calls.append((subtype, evaluation))
            return SimpleNamespace(subtype=subtype, state=evaluation.state)

        with (
            patch.object(self.checker_mod.Cluster.objects, "get", return_value=cluster),
            patch.object(self.checker_mod, "should_skip_cluster", return_value=False),
            patch.object(self.checker_mod, "collect_cluster_runtime_variables", return_value=fake_runtime),
            patch.object(self.checker_mod, "save_consistency_report", side_effect=fake_save),
        ):
            reports = self.checker_mod.check_single_cluster_config_consistency(
                101, config=self.config_mod.MysqlConfigConsistencyConfig()
            )

        self.assertEqual(len(reports), 2)
        by_sub = {sub: ev for sub, ev in saved_calls}
        self.assertEqual(
            by_sub[MysqlConfigConsistencySubType.SPIDER_CONFIG.value].state, ReportStateType.ABNORMAL.value
        )
        self.assertEqual(by_sub[MysqlConfigConsistencySubType.SPIDER_CONFIG.value].diff_variables, ["spider_bgs_mode"])
        self.assertEqual(
            by_sub[MysqlConfigConsistencySubType.STORAGE_SHARD.value].state, ReportStateType.ABNORMAL.value
        )
        self.assertIn("127.0.0.21:20000", by_sub[MysqlConfigConsistencySubType.STORAGE_SHARD.value].msg)

    def test_periodic_task_respects_enabled_flag_and_dispatches(self):
        cfg_disabled = self.config_mod.MysqlConfigConsistencyConfig(enabled=False)
        with (
            patch.object(self.tasks_mod.MysqlConfigConsistencyConfig, "from_settings", return_value=cfg_disabled),
            patch.object(self.tasks_mod, "delete_old_consistency_reports") as mock_del,
        ):
            self.tasks_mod.mysql_config_consistency_check_task()
        mock_del.assert_not_called()

        cfg_enabled = self.config_mod.MysqlConfigConsistencyConfig(
            enabled=True, dispatch_window_seconds=7200, retention_days=90
        )
        mock_span = MagicMock()
        mock_span.__enter__.return_value = None
        mock_span.__exit__.return_value = False
        with (
            patch.object(self.tasks_mod.MysqlConfigConsistencyConfig, "from_settings", return_value=cfg_enabled),
            patch.object(self.tasks_mod, "delete_old_consistency_reports") as mock_del,
            patch.object(self.tasks_mod, "delete_inactive_cluster_reports") as mock_del_inactive,
            patch.object(self.tasks_mod, "_list_candidate_cluster_ids", return_value=[11, 22]),
            patch.object(self.tasks_mod.cache, "add", side_effect=[True, False]) as mock_cache_add,
            patch.object(self.tasks_mod, "start_new_span", return_value=mock_span),
            patch.object(self.tasks_mod.run_cluster_config_consistency_check, "apply_async") as mock_apply,
        ):
            self.tasks_mod.mysql_config_consistency_check_task()
        mock_del.assert_called_once_with(days=90)
        mock_del_inactive.assert_called_once_with()
        mock_apply.assert_called_once()
        self.assertEqual(mock_apply.call_args.kwargs["args"][0], 11)
        expected_ttl = 7200 + self.tasks_mod.WORKER_HARD_TIME_LIMIT + 600
        self.assertEqual(mock_cache_add.call_args_list[0].kwargs["timeout"], expected_ttl)

    def test_delete_inactive_cluster_reports_removes_offline_and_deleted(self):
        report_qs = MagicMock()
        report_qs.distinct.return_value = [1, 2, 3]
        cluster_qs = MagicMock()
        cluster_qs.values_list.return_value = [1]

        with (
            patch.object(
                self.checker_mod.MysqlConfigConsistencyReport.objects,
                "values_list",
                return_value=report_qs,
            ),
            patch.object(self.checker_mod.Cluster.objects, "filter", return_value=cluster_qs),
            patch.object(self.checker_mod, "delete_cluster_consistency_reports", return_value=2) as mock_del,
        ):
            deleted = self.checker_mod.delete_inactive_cluster_reports()

        self.assertEqual(deleted, 2)
        mock_del.assert_called_once_with([2, 3])

    def test_delete_old_consistency_reports_filters_by_create_at(self):
        now = timezone.now()
        qs = MagicMock()
        qs.delete.return_value = (4, {})
        with (
            patch.object(self.checker_mod.timezone, "now", return_value=now),
            patch.object(self.checker_mod.MysqlConfigConsistencyReport.objects, "filter", return_value=qs) as mock_flt,
        ):
            deleted = self.checker_mod.delete_old_consistency_reports(days=90)
        self.assertEqual(deleted, 4)
        mock_flt.assert_called_once_with(create_at__lt=now - timedelta(days=90))

    def test_check_single_cluster_deletes_reports_when_offline_or_missing(self):
        offline_cluster = SimpleNamespace(
            id=301,
            bk_biz_id=10,
            bk_cloud_id=0,
            immute_domain="offline.prod.db",
            cluster_type=ClusterType.TenDBHA.value,
            phase=ClusterPhase.OFFLINE.value,
        )
        with (
            patch.object(self.checker_mod.Cluster.objects, "get", return_value=offline_cluster),
            patch.object(self.checker_mod, "delete_cluster_consistency_reports") as mock_del,
        ):
            res = self.checker_mod.check_single_cluster_config_consistency(
                301, config=self.config_mod.MysqlConfigConsistencyConfig()
            )
        self.assertEqual(res, [])
        mock_del.assert_called_once_with([301])

        with (
            patch.object(self.checker_mod.Cluster.objects, "get", side_effect=self.checker_mod.Cluster.DoesNotExist),
            patch.object(self.checker_mod, "delete_cluster_consistency_reports") as mock_del_missing,
        ):
            res_missing = self.checker_mod.check_single_cluster_config_consistency(
                302, config=self.config_mod.MysqlConfigConsistencyConfig()
            )
        self.assertEqual(res_missing, [])
        mock_del_missing.assert_called_once_with([302])

    def test_worker_releases_lock_on_exception(self):
        with (
            patch.object(
                self.tasks_mod,
                "check_single_cluster_config_consistency",
                side_effect=RuntimeError("boom"),
            ),
            patch.object(self.tasks_mod.cache, "delete") as mock_delete,
        ):
            self.tasks_mod.run_cluster_config_consistency_check(999, "lock:999")
        mock_delete.assert_called_once_with("lock:999")
