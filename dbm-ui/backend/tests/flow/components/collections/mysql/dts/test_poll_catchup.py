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
from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_catchup import (
    MysqlDtsPollCatchupService,
    evaluate_poll_catchup_tick,
)


def _item(
    *,
    sbm: int = 0,
    master: str = "(binlog.000001, 100)",
    syncer: str = "(binlog.000001, 90)",
    error_msg: str | None = None,
    stage: str = "Running",
    source_name: str = "src1",
    name: str = "t1",
) -> TaskStatusItem:
    return TaskStatusItem(
        name=name,
        source_name=source_name,
        stage=stage,
        unit="Sync",
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


class EvaluatePollCatchupTickTest(SimpleTestCase):
    def test_happy_three_consecutive_finishes(self):
        items = [_item()]
        r1 = evaluate_poll_catchup_tick(items=items, consecutive_catchup=0, fail_streak=0, required_consecutive=3)
        self.assertFalse(r1.finished)
        self.assertEqual(r1.consecutive_catchup, 1)

        r2 = evaluate_poll_catchup_tick(
            items=items, consecutive_catchup=r1.consecutive_catchup, fail_streak=0, required_consecutive=3
        )
        self.assertFalse(r2.finished)
        self.assertEqual(r2.consecutive_catchup, 2)

        r3 = evaluate_poll_catchup_tick(
            items=items, consecutive_catchup=r2.consecutive_catchup, fail_streak=0, required_consecutive=3
        )
        self.assertTrue(r3.finished)
        self.assertTrue(r3.success)
        self.assertEqual(r3.consecutive_catchup, 3)

    def test_master_file_ahead_keeps_consecutive(self):
        # 部分同步：master file 超前仍算追平
        caught = [_item(sbm=0, master="(binlog.000002, 1)", syncer="(binlog.000002, 1)")]
        r1 = evaluate_poll_catchup_tick(items=caught, consecutive_catchup=0, fail_streak=0, required_consecutive=3)
        self.assertEqual(r1.consecutive_catchup, 1)

        master_ahead = [_item(sbm=0, master="(binlog.000003, 1)", syncer="(binlog.000002, 1)")]
        r2 = evaluate_poll_catchup_tick(
            items=master_ahead, consecutive_catchup=r1.consecutive_catchup, fail_streak=0, required_consecutive=3
        )
        self.assertFalse(r2.finished)
        self.assertEqual(r2.consecutive_catchup, 2)

    def test_syncer_ahead_resets_consecutive(self):
        caught = [_item(sbm=0, master="(binlog.000002, 1)", syncer="(binlog.000002, 1)")]
        r1 = evaluate_poll_catchup_tick(items=caught, consecutive_catchup=0, fail_streak=0, required_consecutive=3)
        syncer_ahead = [_item(sbm=0, master="(binlog.000001, 1)", syncer="(binlog.000002, 1)")]
        r2 = evaluate_poll_catchup_tick(
            items=syncer_ahead, consecutive_catchup=r1.consecutive_catchup, fail_streak=0, required_consecutive=3
        )
        self.assertEqual(r2.consecutive_catchup, 0)

    def test_nonzero_sbm_resets_consecutive(self):
        r1 = evaluate_poll_catchup_tick(items=[_item()], consecutive_catchup=0, fail_streak=0)
        r2 = evaluate_poll_catchup_tick(
            items=[_item(sbm=5)], consecutive_catchup=r1.consecutive_catchup, fail_streak=0
        )
        self.assertEqual(r2.consecutive_catchup, 0)
        self.assertFalse(r2.finished)

    def test_api_error_streak_then_fail(self):
        r1 = evaluate_poll_catchup_tick(
            items=None, consecutive_catchup=1, fail_streak=0, max_fail_streak=3, api_error="timeout"
        )
        self.assertFalse(r1.finished)
        self.assertEqual(r1.fail_streak, 1)
        self.assertEqual(r1.consecutive_catchup, 1)

        r2 = evaluate_poll_catchup_tick(
            items=None, consecutive_catchup=1, fail_streak=1, max_fail_streak=3, api_error="timeout"
        )
        r3 = evaluate_poll_catchup_tick(
            items=None, consecutive_catchup=1, fail_streak=2, max_fail_streak=3, api_error="timeout"
        )
        self.assertTrue(r3.finished)
        self.assertFalse(r3.success)
        self.assertEqual(r2.fail_streak, 2)

    def test_empty_items_counts_as_fail_streak(self):
        r = evaluate_poll_catchup_tick(items=[], consecutive_catchup=0, fail_streak=0, max_fail_streak=2)
        self.assertEqual(r.fail_streak, 1)
        self.assertFalse(r.finished)

    def test_multi_source_requires_all_caught_up(self):
        items = [
            _item(source_name="a"),
            _item(source_name="b", sbm=3),
        ]
        r = evaluate_poll_catchup_tick(items=items, consecutive_catchup=2, fail_streak=0, required_consecutive=3)
        self.assertEqual(r.consecutive_catchup, 0)
        self.assertFalse(r.finished)

    def test_expected_sources_partial_status_resets_consecutive(self):
        """期望两源但 status 只回一源且已追平 → 不得累计连续成功。"""
        items = [_item(source_name="a")]
        r = evaluate_poll_catchup_tick(
            items=items,
            consecutive_catchup=2,
            fail_streak=0,
            required_consecutive=3,
            expected_source_names=["a", "b"],
        )
        self.assertEqual(r.consecutive_catchup, 0)
        self.assertFalse(r.finished)
        self.assertFalse(r.success)
        self.assertIn("b", r.reason)

    def test_expected_sources_complete_allows_catchup(self):
        items = [_item(source_name="a"), _item(source_name="b")]
        r = evaluate_poll_catchup_tick(
            items=items,
            consecutive_catchup=2,
            fail_streak=0,
            required_consecutive=3,
            expected_source_names=["a", "b"],
        )
        self.assertTrue(r.finished)
        self.assertTrue(r.success)

    def test_hard_fail_on_error_msg(self):
        r = evaluate_poll_catchup_tick(items=[_item(error_msg="disk full")], consecutive_catchup=2, fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)


class MysqlDtsPollCatchupServiceTest(SimpleTestCase):
    def _make_service(self):
        service = MysqlDtsPollCatchupService()
        service.log_info = MagicMock()
        service.log_error = MagicMock()
        service.finish_schedule = MagicMock()
        return service

    def _make_data(self, *, consecutive=0, fail_streak=0, task_name="mysql-dts-869-322-332"):
        outputs = SimpleNamespace(
            task_name=task_name,
            is_caught_up=False,
            consecutive_catchup=consecutive,
            fail_streak=fail_streak,
            last_sbm=None,
            last_master_file="",
            last_syncer_file="",
            task_query_result=None,
        )
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {
                "master_addr": "127.0.0.1:8261",
                "task_name": task_name,
                "required_consecutive": 3,
                "max_fail_streak": 20,
            },
            "trans_data": None,
        }.get(key)
        data.get_one_of_outputs.side_effect = lambda key, default=None: getattr(outputs, key, default)
        data.outputs = outputs
        return data

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.poll_catchup.MySQLDTSApi.get_task_status")
    def test_schedule_progress_does_not_write_task_query_result(self, mock_status):
        mock_status.return_value = TaskStatusListResponse(total=1, data=[_item()])
        service = self._make_service()
        data = self._make_data(consecutive=0)
        result = service._schedule(data, parent_data=None)
        self.assertTrue(result)
        service.finish_schedule.assert_not_called()
        self.assertIsNone(data.outputs.task_query_result)
        self.assertEqual(data.outputs.consecutive_catchup, 1)
        self.assertEqual(data.outputs.task_name, "mysql-dts-869-322-332")
        self.assertEqual(data.outputs.last_sbm, 0)

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.poll_catchup.MySQLDTSApi.get_task_status")
    def test_schedule_success_writes_task_query_result(self, mock_status):
        items = [_item(name="mysql-dts-869-322-332")]
        resp = TaskStatusListResponse(total=1, data=items)
        mock_status.return_value = resp
        service = self._make_service()
        data = self._make_data(consecutive=2)
        result = service._schedule(data, parent_data=None)
        self.assertTrue(result)
        service.finish_schedule.assert_called_once()
        self.assertTrue(data.outputs.is_caught_up)
        self.assertEqual(data.outputs.consecutive_catchup, 3)
        self.assertEqual(data.outputs.task_query_result, resp.model_dump(mode="json"))
        self.assertEqual(data.outputs.task_query_result["total"], 1)
        self.assertEqual(data.outputs.task_query_result["data"][0]["name"], "mysql-dts-869-322-332")
        self.assertEqual(data.outputs.task_query_result["data"][0]["sync_status"]["seconds_behind_master"], 0)

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.poll_catchup.MySQLDTSApi.get_task_status")
    def test_schedule_hard_fail_writes_task_query_result(self, mock_status):
        items = [_item(error_msg="disk full")]
        resp = TaskStatusListResponse(total=1, data=items)
        mock_status.return_value = resp
        service = self._make_service()
        data = self._make_data(consecutive=1)
        result = service._schedule(data, parent_data=None)
        self.assertFalse(result)
        service.finish_schedule.assert_called_once()
        self.assertFalse(data.outputs.is_caught_up)
        self.assertEqual(data.outputs.task_query_result, resp.model_dump(mode="json"))
        self.assertEqual(data.outputs.task_query_result["data"][0]["error_msg"], "disk full")
