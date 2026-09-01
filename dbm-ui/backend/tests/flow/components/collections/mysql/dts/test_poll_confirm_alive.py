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
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.components.mysqldtsapi.types import SyncStatus, TaskStatusItem, TaskStatusListResponse
from backend.db_services.flow_node_baseline.constants import EXCLUDED_COMPONENT_CODES
from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_confirm_alive import (
    MysqlDtsPollConfirmAliveComponent,
    MysqlDtsPollConfirmAliveService,
    evaluate_poll_confirm_alive_tick,
)


def _item(
    *,
    sbm: int = 12,
    master: str = "(binlog.000001, 100)",
    syncer: str = "(binlog.000001, 90)",
    error_msg: str | None = None,
    stage: str = "Running",
    unit: str = "Sync",
    source_name: str = "src1",
    name: str = "t1",
) -> TaskStatusItem:
    return TaskStatusItem(
        name=name,
        source_name=source_name,
        stage=stage,
        unit=unit,
        worker_name="worker-1",
        error_msg=error_msg,
        sync_status=SyncStatus(
            master_binlog=master,
            syncer_binlog=syncer,
            seconds_behind_master=sbm,
            master_binlog_gtid="master-gtid",
            syncer_binlog_gtid="syncer-gtid",
            binlog_type="file",
            synced=True,
        ),
    )


class EvaluatePollConfirmAliveTickTest(SimpleTestCase):
    def test_paused_finishes_fail(self):
        r = evaluate_poll_confirm_alive_tick(items=[_item(stage="Paused")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)

    def test_stopped_finishes_fail(self):
        r = evaluate_poll_confirm_alive_tick(items=[_item(stage="Stopped")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)

    def test_failed_stage_finishes_fail(self):
        r = evaluate_poll_confirm_alive_tick(items=[_item(stage="Failed")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)

    def test_error_msg_finishes_fail(self):
        r = evaluate_poll_confirm_alive_tick(items=[_item(error_msg="disk full")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)

    def test_unscheduled_finishes_fail(self):
        r = evaluate_poll_confirm_alive_tick(items=[_item(stage="Unscheduled")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)

    def test_running_load_continues(self):
        r = evaluate_poll_confirm_alive_tick(items=[_item(unit="Load")], fail_streak=3)
        self.assertFalse(r.finished)
        self.assertEqual(r.fail_streak, 0)

    def test_running_sync_continues_even_with_lag(self):
        r = evaluate_poll_confirm_alive_tick(items=[_item(sbm=99)], fail_streak=2)
        self.assertFalse(r.finished)
        self.assertEqual(r.fail_streak, 0)
        self.assertIn("延迟=99s", r.reason)
        self.assertIn("上游位点=(binlog.000001, 100)", r.reason)
        self.assertIn("已同步位点=(binlog.000001, 90)", r.reason)

    def test_running_load_continues_with_unknown_positions(self):
        item = TaskStatusItem(
            name="t1",
            source_name="src1",
            stage="Running",
            unit="Load",
            worker_name="worker-1",
            error_msg=None,
            sync_status=None,
        )
        r = evaluate_poll_confirm_alive_tick(items=[item], fail_streak=0)
        self.assertFalse(r.finished)
        self.assertIn("延迟=未知", r.reason)
        self.assertIn("上游位点=未知", r.reason)

    def test_multi_source_running_reason_includes_max_and_per_source(self):
        items = [
            _item(source_name="shard-a", sbm=8, master="(bin-a, 100)", syncer="(bin-a, 90)"),
            _item(source_name="shard-b", sbm=12, master="(bin-b, 200)", syncer="(bin-b, 180)"),
        ]
        r = evaluate_poll_confirm_alive_tick(items=items, fail_streak=0)
        self.assertFalse(r.finished)
        self.assertIn("最大延迟=12s", r.reason)
        self.assertIn("shard-a", r.reason)
        self.assertIn("shard-b", r.reason)
        self.assertIn("延迟=8s", r.reason)
        self.assertIn("延迟=12s", r.reason)

    def test_api_error_below_threshold_continues(self):
        r = evaluate_poll_confirm_alive_tick(items=None, fail_streak=0, max_fail_streak=3, api_error="timeout")
        self.assertFalse(r.finished)
        self.assertEqual(r.fail_streak, 1)

    def test_api_error_at_threshold_finishes_fail(self):
        r = evaluate_poll_confirm_alive_tick(items=None, fail_streak=2, max_fail_streak=3, api_error="timeout")
        self.assertTrue(r.finished)
        self.assertFalse(r.success)
        self.assertEqual(r.fail_streak, 3)

    def test_multi_source_one_stopped_fails(self):
        items = [_item(source_name="a"), _item(source_name="b", stage="Stopped")]
        r = evaluate_poll_confirm_alive_tick(items=items, fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)


class MysqlDtsPollConfirmAliveServiceTest(SimpleTestCase):
    def _make_service(self):
        service = MysqlDtsPollConfirmAliveService()
        service.log_info = MagicMock()
        service.log_error = MagicMock()
        service.finish_schedule = MagicMock()
        return service

    def _make_data(self, *, fail_streak=0, callback_kwargs=None, global_data=None):
        outputs = SimpleNamespace(fail_streak=fail_streak, callback_data=None)
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": callback_kwargs
            if callback_kwargs is not None
            else {
                "master_addr": "127.0.0.2:8261",
                "bk_cloud_id": 0,
                "task_name": "mysql-dts-confirm-alive",
                "source_name_list": ["src1"],
                "max_fail_streak": 20,
            },
            "trans_data": None,
            "global_data": global_data or {"uid": "12345"},
        }.get(key)
        data.get_one_of_outputs.side_effect = lambda key, default=None: getattr(outputs, key, default)
        data.outputs = outputs
        return data

    def test_callback_finishes_success_without_status(self):
        service = self._make_service()
        data = self._make_data()
        with patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.poll_confirm_alive.MySQLDTSApi.get_task_status"
        ) as mock_status:
            result = service._schedule(data, parent_data=None, callback_data={"confirmed": True})
        self.assertTrue(result)
        service.finish_schedule.assert_called_once()
        mock_status.assert_not_called()
        self.assertEqual(data.outputs.callback_data, {"confirmed": True})

    def test_callback_after_running_still_skips_status(self):
        service = self._make_service()
        data = self._make_data(fail_streak=0)
        with patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.poll_confirm_alive.MySQLDTSApi.get_task_status"
        ) as mock_status:
            result = service._schedule(data, parent_data=None, callback_data={"action": "callback"})
        self.assertTrue(result)
        mock_status.assert_not_called()
        service.finish_schedule.assert_called_once()

    @patch(
        "backend.flow.plugins.components.collections.mysql.dts.migrate.poll_confirm_alive.MySQLDTSApi.get_task_status"
    )
    def test_running_tick_logs_sync_positions(self, mock_status):
        mock_status.return_value = TaskStatusListResponse(
            total=1,
            data=[_item(sbm=8, master="(mysql-bin.000012, 482917632)", syncer="(mysql-bin.000012, 481234000)")],
        )
        service = self._make_service()
        data = self._make_data()
        result = service._schedule(data, parent_data=None)
        self.assertTrue(result)
        service.log_info.assert_called_once()
        logged = service.log_info.call_args[0][0]
        self.assertIn("延迟=8s", logged)
        self.assertIn("上游位点=(mysql-bin.000012, 482917632)", logged)
        self.assertIn("已同步位点=(mysql-bin.000012, 481234000)", logged)

    @patch(
        "backend.flow.plugins.components.collections.mysql.dts.migrate.poll_confirm_alive.MySQLDTSApi.get_task_status"
    )
    def test_no_callback_hard_fail_finishes_false(self, mock_status):
        mock_status.return_value = TaskStatusListResponse(total=1, data=[_item(stage="Paused")])
        service = self._make_service()
        data = self._make_data()
        result = service._schedule(data, parent_data=None)
        self.assertFalse(result)
        service.finish_schedule.assert_called_once()

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.poll_confirm_alive.PipelineTodo.create")
    @patch(
        "backend.flow.plugins.components.collections.mysql.dts.migrate.poll_confirm_alive.resolve_pause_ticket",
        return_value=None,
    )
    def test_execute_passes_without_ticket(self, mock_resolve, mock_todo_create):
        service = self._make_service()
        data = self._make_data(global_data={"uid": "scene-uid"})
        self.assertTrue(service._execute(data, None))
        self.assertFalse(service.need_schedule())
        mock_todo_create.assert_not_called()
        mock_resolve.assert_called_once()

    def test_component_code_excluded_from_baseline(self):
        self.assertIn(MysqlDtsPollConfirmAliveComponent.code, EXCLUDED_COMPONENT_CODES)
