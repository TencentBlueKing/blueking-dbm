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
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from backend.db_meta.models.mysql_dts import MysqlDtsInfo, MysqlDtsStatus
from backend.flow.consts import StateType
from backend.flow.signal.callback_map import TICKET_TYPE_HANDLERS
from backend.ticket.constants import TicketType


class MysqlDtsMigrateHandlerRecycleTest(TestCase):
    """迁移单据终态回调：仅回收 DTS 临时账号（非完整 dts-task-clean）。

    成功路径账号清理由总流程 dts-task-clean 覆盖，本模块不测成功编排。
    """

    def setUp(self):
        self.ticket_id = 87801
        self.snapshot = {
            "user": "dts_m_rfpxuw8",
            "grant_hosts": ["127.0.0.3"],
            "grant_targets": [{"bk_cloud_id": 0, "address": "127.0.0.2:20000", "cluster_id": 1}],
        }
        MysqlDtsInfo.objects.create(
            bk_biz_id=3,
            source_cluster_ids=[1],
            target_cluster_id=2,
            dts_cluster_id=0,
            migrate_type="ha_to_cluster",
            ticket_id=self.ticket_id,
            root_id="root-recycle-1",
            status=MysqlDtsStatus.FullOnline.value,
            temp_account_snapshot=self.snapshot,
            dts_task_id="task-1",
            creator="tester",
            updater="tester",
        )

    def _mock_engine(self, node_inputs: dict):
        mock_engine = MagicMock()
        mock_engine.get_node_input_data.return_value = MagicMock(data=node_inputs)
        return mock_engine

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_ha_to_cluster_failed_does_not_recycle_temp_accounts(self, mock_engine_cls, mock_drop):
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        self.assertIsNotNone(handler)
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.FAILED)

        mock_drop.assert_not_called()
        info = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id)
        self.assertEqual(info.status, MysqlDtsStatus.FullFailed.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_mysql_to_mysql_failed_does_not_recycle_temp_accounts(self, mock_engine_cls, mock_drop):
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_DTS_DATA_MIGRATE.lower())
        self.assertIsNotNone(handler)
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.FAILED)

        mock_drop.assert_not_called()
        info = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id)
        self.assertEqual(info.status, MysqlDtsStatus.FullFailed.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_revoked_recycles_temp_accounts(self, mock_engine_cls, mock_drop):
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_DTS_DATA_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.REVOKED)

        mock_drop.assert_called_once()
        info = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id)
        self.assertEqual(info.status, MysqlDtsStatus.Terminated.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_ha_to_cluster_revoked_recycles_temp_accounts(self, mock_engine_cls, mock_drop):
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.REVOKED)

        mock_drop.assert_called_once()
        snapshots = mock_drop.call_args[0][0]
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["user"], "dts_m_rfpxuw8")
        info = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id)
        self.assertEqual(info.status, MysqlDtsStatus.Terminated.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_finished_does_not_recycle_temp_accounts(self, mock_engine_cls, mock_drop):
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.FINISHED)

        mock_drop.assert_not_called()
        info = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id)
        self.assertEqual(info.status, MysqlDtsStatus.FullOnline.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_finished_does_not_overwrite_cutover_disconnected(self, mock_engine_cls, mock_drop):
        """cutover_meta 写入 disconnected 后，节点 FINISHED 不得刷回 full_online。"""
        MysqlDtsInfo.objects.filter(ticket_id=self.ticket_id).update(status=MysqlDtsStatus.Disconnected.value)
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-cutover-meta", status=StateType.FINISHED)

        mock_drop.assert_not_called()
        info = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id)
        self.assertEqual(info.status, MysqlDtsStatus.Disconnected.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_running_does_not_overwrite_cutover_disconnected(self, mock_engine_cls, mock_drop):
        """cutover 后 dts-task-clean 等节点 RUNNING 不得刷回 full_online。"""
        MysqlDtsInfo.objects.filter(ticket_id=self.ticket_id).update(status=MysqlDtsStatus.Disconnected.value)
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-task-clean", status=StateType.RUNNING)

        mock_drop.assert_not_called()
        info = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id)
        self.assertEqual(info.status, MysqlDtsStatus.Disconnected.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_failed_does_not_overwrite_cutover_disconnected(self, mock_engine_cls, mock_drop):
        """cutover 后节点 FAILED 不得把 disconnected 盖成 full_failed。"""
        MysqlDtsInfo.objects.filter(ticket_id=self.ticket_id).update(status=MysqlDtsStatus.Disconnected.value)
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-task-clean", status=StateType.FAILED)

        mock_drop.assert_not_called()
        info = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id)
        self.assertEqual(info.status, MysqlDtsStatus.Disconnected.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_revoked_does_not_overwrite_cutover_disconnected(self, mock_engine_cls, mock_drop):
        """同单已 cutover 成功的行，REVOKED 不得盖成 Terminated。"""
        MysqlDtsInfo.objects.filter(ticket_id=self.ticket_id).update(status=MysqlDtsStatus.Disconnected.value)
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.REVOKED)

        mock_drop.assert_called_once()
        info = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id)
        self.assertEqual(info.status, MysqlDtsStatus.Disconnected.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_revoked_terminates_online_but_keeps_disconnected(self, mock_engine_cls, mock_drop):
        """同单多 task：REVOKED 只终止进行中行，保留已 Disconnected 行。"""
        MysqlDtsInfo.objects.filter(ticket_id=self.ticket_id).update(
            status=MysqlDtsStatus.Disconnected.value, dts_task_id="task-done"
        )
        MysqlDtsInfo.objects.create(
            bk_biz_id=3,
            source_cluster_ids=[1],
            target_cluster_id=2,
            dts_cluster_id=0,
            migrate_type="ha_to_cluster",
            ticket_id=self.ticket_id,
            root_id="root-recycle-1",
            status=MysqlDtsStatus.FullOnline.value,
            temp_account_snapshot=self.snapshot,
            dts_task_id="task-running",
            creator="tester",
            updater="tester",
        )
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.REVOKED)

        done = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id, dts_task_id="task-done")
        running = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id, dts_task_id="task-running")
        self.assertEqual(done.status, MysqlDtsStatus.Disconnected.value)
        self.assertEqual(running.status, MysqlDtsStatus.Terminated.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_running_does_not_overwrite_terminated(self, mock_engine_cls, mock_drop):
        """已终止后，其它节点 RUNNING 不得刷回 full_online。"""
        MysqlDtsInfo.objects.filter(ticket_id=self.ticket_id).update(status=MysqlDtsStatus.Terminated.value)
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_TO_MYSQL_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.RUNNING)

        mock_drop.assert_not_called()
        info = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id)
        self.assertEqual(info.status, MysqlDtsStatus.Terminated.value)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_fallback_to_migrate_context_when_no_snapshot(self, mock_engine_cls, mock_drop):
        MysqlDtsInfo.objects.filter(ticket_id=self.ticket_id).update(temp_account_snapshot={})
        mock_engine_cls.return_value = self._mock_engine(
            {
                "global_data": {"ticket_id": self.ticket_id},
                "trans_data": {
                    "migrate_context": {
                        "dts_user": "dts_m_fromctx",
                        "grant_hosts": ["127.0.0.4"],
                        "grant_targets": [{"bk_cloud_id": 0, "address": "127.0.0.5:20000", "cluster_id": 9}],
                    }
                },
            }
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.FAILED)

        mock_drop.assert_not_called()

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_revoked_fallback_to_migrate_context_when_no_snapshot(self, mock_engine_cls, mock_drop):
        MysqlDtsInfo.objects.filter(ticket_id=self.ticket_id).update(temp_account_snapshot={})
        mock_engine_cls.return_value = self._mock_engine(
            {
                "global_data": {"ticket_id": self.ticket_id},
                "trans_data": {
                    "migrate_context": {
                        "dts_user": "dts_m_fromctx",
                        "grant_hosts": ["127.0.0.4"],
                        "grant_targets": [{"bk_cloud_id": 0, "address": "127.0.0.5:20000", "cluster_id": 9}],
                    }
                },
            }
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.REVOKED)

        mock_drop.assert_called_once()
        self.assertEqual(mock_drop.call_args[0][0][0]["user"], "dts_m_fromctx")

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_recycle_exception_does_not_raise(self, mock_engine_cls, mock_drop):
        mock_drop.side_effect = RuntimeError("rpc down")
        mock_engine_cls.return_value = self._mock_engine({"global_data": {"ticket_id": self.ticket_id}})
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        # 不得阻断终止回调
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.REVOKED)

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_failed_does_not_orchestrate_task_clean_or_stop_source(self, mock_engine_cls, mock_drop):
        """终止路径仅 best_effort drop，不编排 dts-task-clean / delete_task|source / stop_task。"""
        import backend.flow.signal.mysql_dts_migrate_handler as handler_mod

        # handler 未导入 clean / delete_task_source / stop_tasks 编排能力；终止只走 best_effort_drop
        self.assertFalse(hasattr(handler_mod, "mysql_dts_task_clean_subflow"))
        self.assertFalse(hasattr(handler_mod, "mysql_dts_delete_task_source_subflow"))
        self.assertFalse(hasattr(handler_mod, "MysqlDtsDeleteTaskSourceComponent"))
        self.assertFalse(hasattr(handler_mod, "MysqlDtsStopTasksComponent"))
        self.assertFalse(hasattr(handler_mod, "MySQLDTSApi"))
        self.assertFalse(hasattr(handler_mod, "JobApi"))
        with open(handler_mod.__file__, encoding="utf-8") as handler_src:
            handler_text = handler_src.read()
        self.assertNotIn("purge_relay", handler_text)
        self.assertNotIn("exported_data", handler_text)
        self.assertNotIn("get_full_migrate_data_dir", handler_text)

        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "created_by": "tester"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.FAILED)
        mock_drop.assert_not_called()

    def _create_sibling(self, dts_task_id: str, status=MysqlDtsStatus.FullOnline.value):
        MysqlDtsInfo.objects.create(
            bk_biz_id=3,
            source_cluster_ids=[1],
            target_cluster_id=3,
            dts_cluster_id=0,
            migrate_type="ha_to_cluster",
            ticket_id=self.ticket_id,
            root_id="root-recycle-1",
            status=status,
            temp_account_snapshot=self.snapshot,
            dts_task_id=dts_task_id,
            creator="tester",
            updater="tester",
        )

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_failed_only_updates_matching_task(self, mock_engine_cls, mock_drop):
        """多行并行：一行 FAILED 只把对应 dts_task_id 打成 FullFailed。"""
        self._create_sibling("task-2")
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "task_name": "task-1"}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.FAILED)

        failed = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id, dts_task_id="task-1")
        sibling = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id, dts_task_id="task-2")
        self.assertEqual(failed.status, MysqlDtsStatus.FullFailed.value)
        self.assertEqual(sibling.status, MysqlDtsStatus.FullOnline.value)
        mock_drop.assert_not_called()

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_failed_skips_when_multi_row_without_task_id(self, mock_engine_cls, mock_drop):
        """多行且节点无 dts_task_id：不回写，避免误伤兄弟行。"""
        self._create_sibling("task-2")
        mock_engine_cls.return_value = self._mock_engine({"global_data": {"ticket_id": self.ticket_id}})
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.FAILED)

        statuses = set(MysqlDtsInfo.objects.filter(ticket_id=self.ticket_id).values_list("status", flat=True))
        self.assertEqual(statuses, {MysqlDtsStatus.FullOnline.value})
        mock_drop.assert_not_called()

    @patch("backend.flow.signal.mysql_dts_migrate_handler.best_effort_drop_dts_temp_accounts_from_snapshots")
    @patch("backend.flow.signal.mysql_dts_migrate_handler.BambooEngine")
    def test_running_only_updates_matching_task(self, mock_engine_cls, mock_drop):
        """RUNNING 同样按行过滤，不把兄弟行刷成 FullOnline。"""
        MysqlDtsInfo.objects.filter(ticket_id=self.ticket_id, dts_task_id="task-1").update(
            status=MysqlDtsStatus.ToDo.value
        )
        self._create_sibling("task-2", status=MysqlDtsStatus.ToDo.value)
        mock_engine_cls.return_value = self._mock_engine(
            {"global_data": {"ticket_id": self.ticket_id, "dts_task_ids": ["task-1"]}}
        )
        handler = TICKET_TYPE_HANDLERS.get(TicketType.MYSQL_TO_MYSQL_MIGRATE.lower())
        handler(root_id="root-recycle-1", node_id="node-1", status=StateType.RUNNING)

        running = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id, dts_task_id="task-1")
        sibling = MysqlDtsInfo.objects.get(ticket_id=self.ticket_id, dts_task_id="task-2")
        self.assertEqual(running.status, MysqlDtsStatus.FullOnline.value)
        self.assertEqual(sibling.status, MysqlDtsStatus.ToDo.value)


class FinalizeCleanupDtsTest(SimpleTestCase):
    """终态回收 DTS 只认 cleanup_after_migrate。"""

    @patch("backend.flow.signal.mysql_dts_migrate_handler.MysqlDtsInfo.objects.filter")
    def test_skips_when_cleanup_false(self, mock_filter):
        from backend.flow.signal.mysql_dts_migrate_handler import _finalize_ephemeral_dts

        _finalize_ephemeral_dts(
            {
                "ticket_id": 1,
                "migrate_plan": {"dts_lifecycle": "deploy", "cleanup_after_migrate": False},
            }
        )
        mock_filter.assert_not_called()

    @patch("backend.flow.signal.mysql_dts_migrate_handler.MysqlDtsInfo.objects.filter")
    def test_looks_up_when_cleanup_true(self, mock_filter):
        from backend.flow.signal.mysql_dts_migrate_handler import _finalize_ephemeral_dts

        mock_filter.return_value.first.return_value = None
        _finalize_ephemeral_dts(
            {
                "ticket_id": 1,
                "migrate_plan": {"dts_lifecycle": "use_existing", "cleanup_after_migrate": True},
            }
        )
        mock_filter.assert_called_once()


class ExtractDtsTaskIdsTest(SimpleTestCase):
    """P1-2：节点 inputs 按行提取 dts_task_id。"""

    def test_from_global_data_task_name(self):
        from backend.flow.signal.mysql_dts_migrate_handler import _extract_dts_task_ids

        self.assertEqual(_extract_dts_task_ids({"global_data": {"task_name": "task-1"}}), ["task-1"])

    def test_from_kwargs_task_spec_and_list(self):
        from backend.flow.signal.mysql_dts_migrate_handler import _extract_dts_task_ids

        self.assertEqual(
            _extract_dts_task_ids(
                {
                    "kwargs": {
                        "task_spec": {"task_name": "task-1"},
                        "dts_task_ids": ["task-1", "task-2"],
                    }
                }
            ),
            ["task-1", "task-2"],
        )

    def test_empty_when_missing(self):
        from backend.flow.signal.mysql_dts_migrate_handler import _extract_dts_task_ids

        self.assertEqual(_extract_dts_task_ids({"global_data": {"ticket_id": 1}}), [])
