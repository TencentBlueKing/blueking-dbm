from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.revoke.mysql_dts_revoke_downloads import (
    BackupDownloadPending,
    ensure_backup_downloads_finished,
)

MOD = "backend.flow.plugins.components.collections.mysql.revoke.mysql_dts_revoke_downloads"


def _result(data, success=True):
    return SimpleNamespace(result=success, data=data)


def _record(bill_id=1, cloud_id=0, version="v1"):
    return {
        "version": version,
        "inputs": {"kwargs": {"dest_ip": "127.0.0.3", "bk_cloud_id": cloud_id}},
        "outputs": {"backup_bill_id": bill_id},
    }


def _node(status="REVOKED", version="v1", expired=False):
    return SimpleNamespace(
        status=status,
        started_at=None if status == "CREATED" else "2026-10-28",
        version_id=version,
        is_expired=expired,
    )


class MysqlDtsRevokeDownloadsTest(SimpleTestCase):
    def setUp(self):
        self.tree = SimpleNamespace(
            status="REVOKED",
            is_expired=False,
            tree={
                "activities": {
                    "subflow": {
                        "pipeline": {"activities": {"download": {"component": {"code": "mysql_download_backup_file"}}}}
                    },
                    "other": {"component": {"code": "mysql_dts_start_task"}},
                }
            },
        )
        self.nodes = [_node()]
        self.engine = MagicMock()
        self.engine.get_node_histories.return_value = _result([])
        self.engine.get_node_execution_data.return_value = _result(_record())
        self.engine.get_node_state.return_value = SimpleNamespace(version="v1")
        self.query = MagicMock(return_value={"total": {"todo": 0, "doing": 0, "fail": 0}})
        patches = [
            patch(f"{MOD}.FlowTree.objects.get", return_value=self.tree),
            patch(f"{MOD}.FlowNode.objects.filter", side_effect=lambda **kwargs: self.nodes),
            patch(f"{MOD}.BambooEngine", return_value=self.engine),
            patch(f"{MOD}.MysqlBackupApi.download_result", self.query),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_nested_download_finished_in_cloud_zero_passes(self):
        ensure_backup_downloads_finished("root")
        self.engine.get_node_histories.assert_called_once_with(node_id="download")
        self.query.assert_called_once_with({"bill_id": 1, "bk_cloud_id": 0})

    def test_queued_or_running_download_blocks_even_with_failed_files(self):
        for todo, doing, failed in ((1, 0, 0), (0, 1, 0), (0, 1, 2)):
            with self.subTest(todo=todo, doing=doing, failed=failed):
                self.query.return_value = {"total": {"todo": todo, "doing": doing, "fail": failed}}
                with self.assertRaises(BackupDownloadPending):
                    ensure_backup_downloads_finished("root")

    def test_failed_download_with_no_remaining_work_allows_cleanup(self):
        self.query.return_value = {"total": {"todo": 0, "doing": 0, "fail": 2}}
        ensure_backup_downloads_finished("root")

    def test_incomplete_or_invalid_response_never_passes(self):
        for response in (None, {}, {"total": {}}, {"total": {"todo": -1, "doing": 0, "fail": 0}}):
            with self.subTest(response=response):
                self.query.return_value = response
                with self.assertRaises(BackupDownloadPending):
                    ensure_backup_downloads_finished("root")

    def test_query_failure_is_retryable(self):
        self.query.side_effect = RuntimeError("unavailable")
        with self.assertRaises(BackupDownloadPending):
            ensure_backup_downloads_finished("root")

    def test_dispatch_without_persisted_bill_never_passes(self):
        self.engine.get_node_execution_data.return_value = _result(_record(bill_id=None))
        with self.assertRaises(BackupDownloadPending):
            ensure_backup_downloads_finished("root")
        self.query.assert_not_called()

    def test_never_started_node_does_not_need_a_bill(self):
        self.nodes = [_node(status="CREATED", version="")]
        ensure_backup_downloads_finished("root")
        self.engine.get_node_execution_data.assert_not_called()
        self.query.assert_not_called()

    def test_all_retry_bills_are_checked_with_their_own_cloud(self):
        self.nodes = [_node(version="v0"), _node()]
        self.engine.get_node_histories.return_value = _result([_record(bill_id=2, cloud_id=7, version="v0")])
        ensure_backup_downloads_finished("root")
        self.assertEqual(
            self.query.call_args_list,
            [call({"bill_id": 2, "bk_cloud_id": 7}), call({"bill_id": 1, "bk_cloud_id": 0})],
        )

    def test_old_retry_bill_still_running_blocks_cleanup(self):
        self.engine.get_node_histories.return_value = _result([_record(bill_id=2, version="v0")])
        self.query.side_effect = lambda params: {"total": {"todo": 0, "doing": int(params["bill_id"] == 2), "fail": 0}}
        with self.assertRaises(BackupDownloadPending):
            ensure_backup_downloads_finished("root")

    def test_duplicate_bill_is_queried_once(self):
        self.engine.get_node_histories.return_value = _result([_record(version="v0")])
        ensure_backup_downloads_finished("root")
        self.query.assert_called_once()

    def test_lost_history_or_execution_data_blocks_cleanup(self):
        self.nodes = [_node(version="v0"), _node()]
        with self.assertRaises(BackupDownloadPending):
            ensure_backup_downloads_finished("root")
        self.nodes = [_node()]
        self.engine.get_node_execution_data.return_value = _result(None, success=False)
        with self.assertRaises(BackupDownloadPending):
            ensure_backup_downloads_finished("root")
        self.query.assert_not_called()

    def test_unreadable_history_blocks_even_created_node(self):
        self.nodes = [_node(status="CREATED")]
        self.engine.get_node_histories.return_value = _result(None, success=False)
        with self.assertRaises(BackupDownloadPending):
            ensure_backup_downloads_finished("root")

    def test_pipeline_must_have_stopped_and_runtime_must_exist(self):
        self.tree.status = "RUNNING"
        with self.assertRaises(BackupDownloadPending):
            ensure_backup_downloads_finished("root")
        self.tree.status = "REVOKED"
        self.tree.is_expired = True
        with self.assertRaises(BackupDownloadPending):
            ensure_backup_downloads_finished("root")
        self.tree.is_expired = False
        self.nodes = []
        with self.assertRaises(BackupDownloadPending):
            ensure_backup_downloads_finished("root")
        self.query.assert_not_called()

    def test_multiple_parallel_download_nodes_are_all_checked(self):
        self.tree.tree["activities"]["download2"] = {"component": {"code": "mysql_download_backup_file"}}
        self.engine.get_node_execution_data.side_effect = [_result(_record()), _result(_record(bill_id=2))]
        ensure_backup_downloads_finished("root")
        self.assertEqual(self.query.call_count, 2)
