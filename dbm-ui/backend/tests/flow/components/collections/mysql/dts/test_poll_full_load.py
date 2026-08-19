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

from backend.components.mysqldtsapi.types import DumpStatus, LoadStatus, TaskStatusItem, TaskStatusListResponse
from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_full_load import (
    MysqlDtsPollFullLoadService,
    _ascii_progress_bar,
    _format_bytes,
    _format_dump_progress,
    _format_load_progress,
    _percent,
    evaluate_poll_full_load_tick,
)


def _item(
    *,
    stage: str = "Running",
    unit: str = "Dump",
    error_msg: str | None = None,
    source_name: str = "src1",
    name: str = "t1",
    dump_status: DumpStatus | None = None,
    load_status: LoadStatus | None = None,
) -> TaskStatusItem:
    return TaskStatusItem(
        name=name,
        source_name=source_name,
        stage=stage,
        unit=unit,
        worker_name="worker-1",
        error_msg=error_msg,
        dump_status=dump_status,
        load_status=load_status,
    )


class FormatHelperTest(SimpleTestCase):
    def test_ascii_bar_and_percent(self):
        self.assertEqual(_ascii_progress_bar(25, 100), "[##--------]")
        self.assertEqual(_percent(25, 100), 25)
        self.assertEqual(_ascii_progress_bar(100, 100), "[##########]")
        self.assertEqual(_percent(150, 100), 100)
        self.assertIsNone(_ascii_progress_bar(12, 0))
        self.assertIsNone(_percent(12, 0))

    def test_format_bytes(self):
        self.assertEqual(_format_bytes(536870912), "512.0MiB")
        self.assertEqual(_format_bytes(2147483648), "2.0GiB")

    def test_format_dump_and_load(self):
        dump = _format_dump_progress(DumpStatus(completed_tables=12, total_tables=100))
        self.assertIn("表进度=12/100", dump)
        self.assertIn("12%", dump)
        load = _format_load_progress(LoadStatus(finished_bytes=536870912, total_bytes=2147483648))
        self.assertIn("512.0MiB/2.0GiB", load)
        self.assertIn("25%", load)
        missing = _format_dump_progress(DumpStatus(completed_tables=12, total_tables=0))
        self.assertIn("12/未知", missing)
        self.assertNotIn("%", missing)


class EvaluatePollFullLoadTickTest(SimpleTestCase):
    def test_sync_running_succeeds_once(self):
        r = evaluate_poll_full_load_tick(items=[_item(stage="Running", unit="Sync")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertTrue(r.success)
        self.assertEqual(r.last_unit, "Sync")
        self.assertEqual(r.last_stage, "Running")

    def test_sync_finished_succeeds(self):
        r = evaluate_poll_full_load_tick(items=[_item(stage="Finished", unit="Sync")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertTrue(r.success)

    def test_first_poll_already_sync_succeeds_ae8(self):
        """AE8: 首次轮询已是 Sync，无 Dump/Load 先验记忆。"""
        r = evaluate_poll_full_load_tick(items=[_item(stage="Running", unit="Sync")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertTrue(r.success)

    def test_dump_or_load_continues(self):
        for unit in ("Dump", "Load"):
            r = evaluate_poll_full_load_tick(items=[_item(stage="Running", unit=unit)], fail_streak=0)
            self.assertFalse(r.finished, msg=unit)
            self.assertFalse(r.success, msg=unit)
            self.assertEqual(r.fail_streak, 0, msg=unit)

    def test_dump_running_reason_has_progress_omits_stage(self):
        dump = DumpStatus(
            completed_tables=12,
            total_tables=100,
            finished_rows=1200000,
            estimate_total_rows=10000000,
        )
        r = evaluate_poll_full_load_tick(
            items=[_item(stage="Running", unit="Dump", dump_status=dump)],
            fail_streak=0,
        )
        self.assertFalse(r.finished)
        self.assertNotIn("stage=Running", r.reason)
        self.assertIn("unit=Dump", r.reason)
        self.assertIn("表进度=12/100", r.reason)
        self.assertIn("12%", r.reason)
        self.assertIn("[", r.reason)
        self.assertIn("行进度=1200000/10000000", r.reason)

    def test_load_running_reason_human_bytes_and_percent(self):
        load = LoadStatus(finished_bytes=536870912, total_bytes=2147483648, progress="25%")
        r = evaluate_poll_full_load_tick(
            items=[_item(stage="Running", unit="Load", load_status=load)],
            fail_streak=0,
        )
        self.assertFalse(r.finished)
        self.assertNotIn("stage=Running", r.reason)
        self.assertIn("unit=Load", r.reason)
        self.assertIn("字节进度=512.0MiB/2.0GiB", r.reason)
        self.assertIn("[##--------]", r.reason)
        self.assertIn("25%", r.reason)
        self.assertIn("progress=25%", r.reason)

    def test_stopped_dump_keeps_stage_in_reason(self):
        dump = DumpStatus(completed_tables=3, total_tables=10)
        r = evaluate_poll_full_load_tick(
            items=[_item(stage="Stopped", unit="Dump", dump_status=dump)],
            fail_streak=0,
        )
        self.assertFalse(r.finished)
        self.assertIn("stage=Stopped", r.reason)
        self.assertIn("表进度=3/10", r.reason)

    def test_dump_missing_total_no_fake_percent(self):
        dump = DumpStatus(completed_tables=12, total_tables=0)
        r = evaluate_poll_full_load_tick(
            items=[_item(unit="Dump", dump_status=dump)],
            fail_streak=0,
        )
        self.assertFalse(r.finished)
        self.assertIn("表进度=12/未知", r.reason)
        self.assertNotIn("%", r.reason)
        self.assertNotIn("[", r.reason)

    def test_multi_source_waiting_reason_per_source(self):
        items = [
            _item(
                source_name="shard-a",
                unit="Dump",
                dump_status=DumpStatus(completed_tables=1, total_tables=10),
            ),
            _item(
                source_name="shard-b",
                unit="Load",
                load_status=LoadStatus(finished_bytes=100, total_bytes=400),
            ),
        ]
        r = evaluate_poll_full_load_tick(items=items, fail_streak=0)
        self.assertFalse(r.finished)
        self.assertIn("各源仍在全量导入", r.reason)
        self.assertIn("shard-a", r.reason)
        self.assertIn("shard-b", r.reason)
        self.assertIn("表进度=1/10", r.reason)
        self.assertIn("25%", r.reason)

    def test_sync_success_reason_unchanged_shape(self):
        r = evaluate_poll_full_load_tick(items=[_item(stage="Running", unit="Sync")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertTrue(r.success)
        self.assertIn("DTS 全量导入已完成", r.reason)
        self.assertNotIn("表进度=", r.reason)

    def test_stopped_dump_or_load_continues_not_hard_fail(self):
        for unit in ("Dump", "Load"):
            r = evaluate_poll_full_load_tick(items=[_item(stage="Stopped", unit=unit)], fail_streak=0)
            self.assertFalse(r.finished, msg=unit)
            self.assertFalse(r.success, msg=unit)

    def test_error_msg_hard_fail(self):
        r = evaluate_poll_full_load_tick(items=[_item(error_msg="disk full")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)

    def test_stage_failed_hard_fail(self):
        r = evaluate_poll_full_load_tick(items=[_item(stage="Failed", unit="Load")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)

    def test_stage_error_case_insensitive_hard_fail(self):
        r = evaluate_poll_full_load_tick(items=[_item(stage="TaskERROR", unit="Dump")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)

    def test_paused_hard_fail(self):
        r = evaluate_poll_full_load_tick(items=[_item(stage="Paused", unit="Load")], fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)

    def test_full_mode_finished_without_sync_succeeds(self):
        r = evaluate_poll_full_load_tick(
            items=[_item(stage="Finished", unit="Load")],
            fail_streak=0,
            task_mode="full",
        )
        self.assertTrue(r.finished)
        self.assertTrue(r.success)

    def test_all_mode_finished_without_sync_continues(self):
        r = evaluate_poll_full_load_tick(
            items=[_item(stage="Finished", unit="Load")],
            fail_streak=0,
            task_mode="all",
        )
        self.assertFalse(r.finished)

    def test_multi_source_requires_all_done(self):
        items = [
            _item(source_name="a", stage="Running", unit="Sync"),
            _item(source_name="b", stage="Running", unit="Load"),
        ]
        r = evaluate_poll_full_load_tick(items=items, fail_streak=0)
        self.assertFalse(r.finished)

    def test_multi_source_all_sync_succeeds(self):
        items = [
            _item(source_name="a", stage="Running", unit="Sync"),
            _item(source_name="b", stage="Finished", unit="Sync"),
        ]
        r = evaluate_poll_full_load_tick(items=items, fail_streak=0)
        self.assertTrue(r.finished)
        self.assertTrue(r.success)

    def test_expected_sources_partial_status_not_success(self):
        """期望两源但 status 只回一源且已 Sync → 不得成功。"""
        items = [_item(source_name="a", stage="Running", unit="Sync")]
        r = evaluate_poll_full_load_tick(
            items=items,
            fail_streak=0,
            expected_source_names=["a", "b"],
        )
        self.assertFalse(r.finished)
        self.assertFalse(r.success)
        self.assertIn("b", r.reason)

    def test_expected_sources_complete_allows_success(self):
        items = [
            _item(source_name="a", stage="Running", unit="Sync"),
            _item(source_name="b", stage="Running", unit="Sync"),
        ]
        r = evaluate_poll_full_load_tick(
            items=items,
            fail_streak=0,
            expected_source_names=["a", "b"],
        )
        self.assertTrue(r.finished)
        self.assertTrue(r.success)

    def test_multi_source_any_hard_fail_fails(self):
        items = [
            _item(source_name="a", stage="Running", unit="Sync"),
            _item(source_name="b", stage="Running", unit="Load", error_msg="boom"),
        ]
        r = evaluate_poll_full_load_tick(items=items, fail_streak=0)
        self.assertTrue(r.finished)
        self.assertFalse(r.success)

    def test_api_error_streak_then_fail(self):
        r1 = evaluate_poll_full_load_tick(items=None, fail_streak=0, max_fail_streak=3, api_error="timeout")
        self.assertFalse(r1.finished)
        self.assertEqual(r1.fail_streak, 1)

        r3 = evaluate_poll_full_load_tick(items=None, fail_streak=2, max_fail_streak=3, api_error="timeout")
        self.assertTrue(r3.finished)
        self.assertFalse(r3.success)
        self.assertEqual(r3.fail_streak, 3)

    def test_empty_items_counts_as_fail_streak(self):
        r = evaluate_poll_full_load_tick(items=[], fail_streak=0, max_fail_streak=2)
        self.assertEqual(r.fail_streak, 1)
        self.assertFalse(r.finished)


class MysqlDtsPollFullLoadServiceTest(SimpleTestCase):
    def _make_service(self):
        service = MysqlDtsPollFullLoadService()
        service.log_info = MagicMock()
        service.log_error = MagicMock()
        service.finish_schedule = MagicMock()
        return service

    def _make_data(self, *, fail_streak=0, task_name="mysql-dts-869-322-332", task_mode="all"):
        outputs = SimpleNamespace(
            task_name=task_name,
            is_full_load_done=False,
            fail_streak=fail_streak,
            last_stage="",
            last_unit="",
            task_query_result=None,
        )
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {
                "master_addr": "127.0.0.1:8261",
                "bk_cloud_id": 0,
                "task_name": task_name,
                "task_mode": task_mode,
                "max_fail_streak": 20,
            },
            "trans_data": None,
        }.get(key)
        data.get_one_of_outputs.side_effect = lambda key, default=None: getattr(outputs, key, default)
        data.outputs = outputs
        return data

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.poll_full_load.MySQLDTSApi.get_task_status")
    def test_schedule_sync_finishes_success(self, mock_status):
        resp = TaskStatusListResponse(total=1, data=[_item(stage="Running", unit="Sync")])
        mock_status.return_value = resp
        service = self._make_service()
        data = self._make_data()
        result = service._schedule(data, parent_data=None)
        self.assertTrue(result)
        service.finish_schedule.assert_called_once()
        self.assertTrue(data.outputs.is_full_load_done)
        self.assertEqual(data.outputs.task_query_result, resp.model_dump(mode="json"))

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.poll_full_load.MySQLDTSApi.get_task_status")
    def test_schedule_stopped_dump_continues(self, mock_status):
        mock_status.return_value = TaskStatusListResponse(total=1, data=[_item(stage="Stopped", unit="Dump")])
        service = self._make_service()
        data = self._make_data()
        result = service._schedule(data, parent_data=None)
        self.assertTrue(result)
        service.finish_schedule.assert_not_called()
        self.assertFalse(data.outputs.is_full_load_done)
        self.assertIsNone(data.outputs.task_query_result)
        self.assertEqual(data.outputs.last_stage, "Stopped")
        self.assertEqual(data.outputs.last_unit, "Dump")

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.poll_full_load.MySQLDTSApi.get_task_status")
    def test_schedule_error_msg_fails(self, mock_status):
        resp = TaskStatusListResponse(total=1, data=[_item(error_msg="disk full")])
        mock_status.return_value = resp
        service = self._make_service()
        data = self._make_data()
        result = service._schedule(data, parent_data=None)
        self.assertFalse(result)
        service.finish_schedule.assert_called_once()
        self.assertFalse(data.outputs.is_full_load_done)
        self.assertEqual(data.outputs.task_query_result, resp.model_dump(mode="json"))

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.poll_full_load.MySQLDTSApi.get_task_status")
    def test_schedule_api_exception_continues_under_threshold(self, mock_status):
        mock_status.side_effect = RuntimeError("timeout")
        service = self._make_service()
        data = self._make_data(fail_streak=0)
        result = service._schedule(data, parent_data=None)
        self.assertTrue(result)
        service.finish_schedule.assert_not_called()
        self.assertEqual(data.outputs.fail_streak, 1)

    @patch("backend.flow.plugins.components.collections.mysql.dts.migrate.poll_full_load.MySQLDTSApi.get_task_status")
    def test_schedule_continues_logs_progress(self, mock_status):
        mock_status.return_value = TaskStatusListResponse(
            total=1,
            data=[
                _item(
                    unit="Dump",
                    dump_status=DumpStatus(completed_tables=12, total_tables=100),
                )
            ],
        )
        service = self._make_service()
        data = self._make_data()
        result = service._schedule(data, parent_data=None)
        self.assertTrue(result)
        service.log_info.assert_called()
        logged = service.log_info.call_args[0][0]
        self.assertIn("表进度=12/100", logged)
        self.assertNotIn("stage=Running", logged)
