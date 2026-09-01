# -*- coding: utf-8 -*-
"""本单维度 purge_relay → delete_task → dump rm → delete_source 组件单测。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from backend.components.mysqldtsapi.types import (
    GetSourceResponse,
    PurgeRelayRequest,
    RelayConfig,
    RelayStatus,
    SourceStatus,
    SourceStatusListResponse,
)
from backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source import (
    MysqlDtsDeleteTaskSourceService,
)
from backend.flow.utils.mysql.dts.constants import FullLoadEngine, get_full_migrate_data_dir
from backend.utils.string import base64_decode


def _status_with_binlog(source_name: str, master_binlog: str) -> SourceStatusListResponse:
    return SourceStatusListResponse(
        total=1,
        data=[
            SourceStatus(
                source_name=source_name,
                worker_name="dm-worker-1",
                relay_status=RelayStatus(master_binlog=master_binlog),
            )
        ],
    )


def _source_with_relay(source_name: str, enable_relay: bool) -> GetSourceResponse:
    return GetSourceResponse(
        source_name=source_name,
        host="127.0.0.2",
        port=3306,
        user="dts_m_abc",
        enable_gtid=True,
        enable=True,
        relay_config=RelayConfig(enable_relay=enable_relay),
    )


class MysqlDtsDeleteTaskSourceServiceTest(SimpleTestCase):
    def _make_service(self):
        service = MysqlDtsDeleteTaskSourceService()
        service.log_info = MagicMock()
        service.log_warning = MagicMock()
        service.log_error = MagicMock()
        return service

    def _run(self, kwargs, *, trans_data=None):
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": kwargs,
            "trans_data": trans_data,
        }.get(key)
        return self._make_service()._execute(data, parent_data=None)

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_deletes_tasks_then_sources_in_order(self, mock_api):
        ok = self._run(
            {
                "master_addr": "127.0.0.4:8261",
                "bk_cloud_id": 0,
                "task_names": ["t1", "t2"],
                "source_names": ["s1", "s2"],
                "ignore_errors": True,
            }
        )
        self.assertTrue(ok)
        self.assertEqual(
            mock_api.mock_calls,
            [
                call.delete_task("127.0.0.4:8261", "t1", force=True, bk_cloud_id=0),
                call.delete_task("127.0.0.4:8261", "t2", force=True, bk_cloud_id=0),
                call.delete_source("127.0.0.4:8261", "s1", force=True, bk_cloud_id=0),
                call.delete_source("127.0.0.4:8261", "s2", force=True, bk_cloud_id=0),
            ],
        )
        mock_api.list_tasks.assert_not_called()
        mock_api.list_sources.assert_not_called()
        mock_api.get_source_status.assert_not_called()
        mock_api.purge_relay.assert_not_called()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_ignore_errors_partial_failure_still_succeeds(self, mock_api):
        mock_api.delete_task.side_effect = [None, RuntimeError("gone")]
        mock_api.delete_source.side_effect = RuntimeError("missing")
        ok = self._run(
            {
                "master_addr": "127.0.0.4:8261",
                "bk_cloud_id": 0,
                "task_names": ["t1", "t2"],
                "source_names": ["s1"],
                "ignore_errors": True,
            }
        )
        self.assertTrue(ok)
        self.assertEqual(mock_api.delete_task.call_count, 2)
        self.assertEqual(mock_api.delete_source.call_count, 1)

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_empty_names_skips(self, mock_api):
        self.assertTrue(
            self._run({"master_addr": "127.0.0.4:8261", "bk_cloud_id": 0, "task_names": [], "source_names": []})
        )
        self.assertTrue(self._run({"master_addr": "", "task_names": [], "source_names": []}))
        mock_api.delete_task.assert_not_called()
        mock_api.delete_source.assert_not_called()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_empty_master_with_names_fails(self, mock_api):
        self.assertFalse(
            self._run({"master_addr": "", "bk_cloud_id": 0, "task_names": ["t1"], "source_names": ["s1"]})
        )
        # ignore_errors 也不能把「无 Master」当成成功
        self.assertFalse(
            self._run(
                {
                    "master_addr": "",
                    "bk_cloud_id": 0,
                    "task_names": ["t1"],
                    "source_names": [],
                    "ignore_errors": True,
                }
            )
        )
        mock_api.delete_task.assert_not_called()
        mock_api.delete_source.assert_not_called()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_strict_mode_partial_failure_returns_false(self, mock_api):
        mock_api.delete_task.side_effect = [None, RuntimeError("gone")]
        mock_api.delete_source.return_value = None
        ok = self._run(
            {
                "master_addr": "127.0.0.4:8261",
                "bk_cloud_id": 0,
                "task_names": ["t1", "t2"],
                "source_names": ["s1"],
                # 默认 ignore_errors=False
            }
        )
        self.assertFalse(ok)
        self.assertEqual(mock_api.delete_task.call_count, 2)
        self.assertEqual(mock_api.delete_source.call_count, 1)

    def _incremental_builtin_kwargs(self, **overrides):
        kwargs = {
            "master_addr": "127.0.0.4:8261",
            "bk_cloud_id": 0,
            "task_names": ["t1"],
            "source_names": ["s1"],
            "task_mode": "all",
            "full_load_engine": FullLoadEngine.BUILTIN.value,
            "dts_cluster_id": 9,
        }
        kwargs.update(overrides)
        return kwargs

    def _mock_cluster(self, mock_load, *, name="dts-prod", workers=None):
        cluster = MagicMock()
        cluster.name = name
        cluster.worker_nodes = workers if workers is not None else [{"ip": "127.0.0.2", "bk_cloud_id": 0}]
        mock_load.return_value = cluster
        return cluster

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_incremental_builtin_order_purge_then_dump_then_delete_source(self, mock_api, mock_load, mock_job):
        mock_api.get_source.return_value = _source_with_relay("s1", True)
        mock_api.get_source_status.return_value = _status_with_binlog("s1", "(mysql-bin.000005, 4)")
        self._mock_cluster(mock_load)
        ok = self._run(self._incremental_builtin_kwargs())
        self.assertTrue(ok)
        self.assertEqual(
            mock_api.mock_calls,
            [
                call.get_source("127.0.0.4:8261", "s1", bk_cloud_id=0),
                call.get_source_status("127.0.0.4:8261", "s1", bk_cloud_id=0),
                call.purge_relay(
                    "127.0.0.4:8261",
                    "s1",
                    PurgeRelayRequest(relay_binlog_name="mysql-bin.000005"),
                    bk_cloud_id=0,
                ),
                call.delete_task("127.0.0.4:8261", "t1", force=True, bk_cloud_id=0),
                call.delete_source("127.0.0.4:8261", "s1", force=True, bk_cloud_id=0),
            ],
        )
        mock_api.list_tasks.assert_not_called()
        mock_api.list_sources.assert_not_called()
        mock_job.fast_execute_script.assert_called_once()
        body = mock_job.fast_execute_script.call_args.args[0]
        script = base64_decode(body["script_content"])
        dump_dir = get_full_migrate_data_dir("dts-prod", "t1")
        self.assertIn(dump_dir, script)
        self.assertNotIn("other-task", script)
        self.assertNotIn("/data/dbbak", script)
        self.assertEqual(body["target_server"]["ip_list"], [{"bk_cloud_id": 0, "ip": "127.0.0.2"}])

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_parses_binlog_coord_not_raw_string(self, mock_api, mock_load, mock_job):
        mock_api.get_source.return_value = _source_with_relay("s1", True)
        mock_api.get_source_status.return_value = _status_with_binlog("s1", "(mysql-bin.000005, 4)")
        self._mock_cluster(mock_load)
        self._run(self._incremental_builtin_kwargs())
        req = mock_api.purge_relay.call_args.args[2]
        self.assertEqual(req.relay_binlog_name, "mysql-bin.000005")
        self.assertNotEqual(req.relay_binlog_name, "(mysql-bin.000005, 4)")
        self.assertIsNone(req.relay_dir)

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_purge_relay_failure_strict_mode_fails(self, mock_api, mock_load, mock_job):
        mock_api.get_source.return_value = _source_with_relay("s1", True)
        mock_api.get_source_status.return_value = _status_with_binlog("s1", "(mysql-bin.000005, 4)")
        mock_api.purge_relay.side_effect = RuntimeError("disk full")
        self._mock_cluster(mock_load)
        ok = self._run(self._incremental_builtin_kwargs())
        self.assertFalse(ok)
        mock_api.delete_source.assert_called_once()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_relay_disabled_skips_purge_without_status_query(self, mock_api, mock_load, mock_job):
        mock_api.get_source.return_value = _source_with_relay("s1", False)
        self._mock_cluster(mock_load)
        ok = self._run(self._incremental_builtin_kwargs())
        self.assertTrue(ok)
        mock_api.get_source_status.assert_not_called()
        mock_api.purge_relay.assert_not_called()
        mock_api.delete_task.assert_called_once()
        mock_api.delete_source.assert_called_once()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_purge_relay_49001_not_treated_as_failure(self, mock_api, mock_load, mock_job):
        # relay 启用状态与 Master 实际不一致时（无 relay worker），49001 不应判死清理节点
        mock_api.get_source.return_value = _source_with_relay("s1", True)
        mock_api.get_source_status.return_value = _status_with_binlog("s1", "(mysql-bin.000005, 4)")
        mock_api.purge_relay.side_effect = RuntimeError(
            '{"error_code": 49001, "error_msg": "relay worker for source s1 not found, `enable-relay` first"}'
        )
        self._mock_cluster(mock_load)
        ok = self._run(self._incremental_builtin_kwargs())
        self.assertTrue(ok)
        mock_api.delete_task.assert_called_once()
        mock_api.delete_source.assert_called_once()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_get_source_failure_still_attempts_purge(self, mock_api, mock_load, mock_job):
        mock_api.get_source.side_effect = RuntimeError("master unreachable")
        mock_api.get_source_status.return_value = _status_with_binlog("s1", "(mysql-bin.000005, 4)")
        self._mock_cluster(mock_load)
        ok = self._run(self._incremental_builtin_kwargs())
        self.assertTrue(ok)
        mock_api.purge_relay.assert_called_once()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_unparseable_binlog_skips_purge_still_deletes_source(self, mock_api, mock_load, mock_job):
        mock_api.get_source.return_value = _source_with_relay("s1", True)
        mock_api.get_source_status.return_value = _status_with_binlog("s1", "not-a-coord")
        self._mock_cluster(mock_load)
        ok = self._run(self._incremental_builtin_kwargs())
        self.assertTrue(ok)
        mock_api.purge_relay.assert_not_called()
        mock_api.delete_source.assert_called_once()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_runtime_cluster_from_kwargs_name(self, mock_api, mock_load, mock_job):
        mock_api.get_source.return_value = _source_with_relay("s1", True)
        mock_api.get_source_status.return_value = _status_with_binlog("s1", "(mysql-bin.000005, 4)")
        self._mock_cluster(mock_load)
        trans_data = SimpleNamespace(
            migrate_context=SimpleNamespace(dts_cluster_id=9, master_addr="", bk_cloud_id=None)
        )
        ok = self._run(
            self._incremental_builtin_kwargs(dts_cluster_id=None, cluster_name="dts-prod", bk_biz_id=20),
            trans_data=trans_data,
        )
        self.assertTrue(ok)
        mock_load.assert_called_once_with(dts_cluster_id=None, bk_biz_id=20, cluster_name="dts-prod")
        mock_job.fast_execute_script.assert_called_once()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_full_mode_skips_purge_still_rms_dump(self, mock_api, mock_load, mock_job):
        self._mock_cluster(mock_load)
        ok = self._run(self._incremental_builtin_kwargs(task_mode="full"))
        self.assertTrue(ok)
        mock_api.get_source.assert_not_called()
        mock_api.get_source_status.assert_not_called()
        mock_api.purge_relay.assert_not_called()
        mock_job.fast_execute_script.assert_called_once()
        mock_api.delete_source.assert_called_once()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_myloader_skips_dump_rm(self, mock_api, mock_load, mock_job):
        mock_api.get_source.return_value = _source_with_relay("s1", True)
        mock_api.get_source_status.return_value = _status_with_binlog("s1", "(mysql-bin.000005, 4)")
        ok = self._run(self._incremental_builtin_kwargs(full_load_engine=FullLoadEngine.MYLOADER.value))
        self.assertTrue(ok)
        mock_job.fast_execute_script.assert_not_called()
        mock_load.assert_not_called()
        mock_api.purge_relay.assert_called_once()
        mock_api.delete_source.assert_called_once()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.JobApi")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.load_active_dts_cluster")
    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source.MySQLDTSApi")
    def test_builtin_missing_cluster_id_fails(self, mock_api, mock_load, mock_job):
        mock_load.return_value = None
        ok = self._run(self._incremental_builtin_kwargs(dts_cluster_id=None, task_mode="full"))
        self.assertFalse(ok)
        mock_job.fast_execute_script.assert_not_called()
        mock_api.delete_source.assert_called_once()
