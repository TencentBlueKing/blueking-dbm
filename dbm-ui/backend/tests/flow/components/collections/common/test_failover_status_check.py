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

from backend.flow.plugins.components.collections.common import failover_status_check as mod
from backend.flow.utils import failover_drill_dbha


class FakeData:
    def __init__(self, kwargs):
        self.inputs = {"kwargs": kwargs}
        self.outputs = {"loop_count": 1}

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)

    def get_one_of_outputs(self, key):
        return self.outputs.get(key)

    def set_outputs(self, key, value):
        self.outputs[key] = value


def _kwargs(**extra):
    kwargs = {
        "trans_data_dataclass": "FailoverDrillContext",
        "cloud_id": 0,
        "app": "3",
        "ip": "1.1.1.1",
        "main_task_id": "task",
        "instance_role": "proxy",
    }
    kwargs.update(extra)
    return kwargs


def _service():
    service = mod.FailoverStatusCheckService()
    service.finish_schedule = MagicMock()
    service.log_info = MagicMock()
    service.log_error = MagicMock()
    service.log_exception = MagicMock()
    return service


class TestFailoverStatusCheckSchedule:
    def test_v2_hit_finishes_with_message_shell(self):
        service = _service()
        data = FakeData(_kwargs(dbha_version="v2"))
        resp = {"code": 0, "message": "ok", "data": [{"ip": "1.1.1.1", "port": 30000}]}
        with patch.object(failover_drill_dbha.HADBApiV2, "switch_queue", return_value=resp) as v2, patch.object(
            failover_drill_dbha.HADBApi, "switch_queue"
        ) as v1:
            assert service._schedule(data, None) is True

        service.finish_schedule.assert_called_once()
        service.log_error.assert_not_called()
        service.log_exception.assert_not_called()
        v1.assert_not_called()
        assert set(v2.call_args.kwargs["params"]["query_args"]) == {"app", "switch_start_time", "switch_finished_time"}

    def test_combined_version_queries_v2_queue(self):
        service = _service()
        data = FakeData(_kwargs(dbha_version="v1,v2"))
        resp = {"code": 0, "message": "ok", "data": [{"ip": "1.1.1.1", "port": 30000}]}
        with patch.object(failover_drill_dbha.HADBApiV2, "switch_queue", return_value=resp) as v2, patch.object(
            failover_drill_dbha.HADBApi, "switch_queue"
        ) as v1:
            assert service._schedule(data, None) is True

        v1.assert_not_called()
        v2.assert_called_once()
        service.finish_schedule.assert_called_once()

    def test_v2_no_hit_keeps_polling(self):
        service = _service()
        data = FakeData(_kwargs(dbha_version="v2"))
        resp = {"code": 0, "message": "ok", "data": [{"ip": "2.2.2.2", "port": 30000}]}
        with patch.object(failover_drill_dbha.HADBApiV2, "switch_queue", return_value=resp):
            service._schedule(data, None)

        service.finish_schedule.assert_not_called()
        assert data.outputs["loop_count"] == 2

    def test_v2_api_error_keeps_polling_with_short_timeout(self):
        service = _service()
        data = FakeData(_kwargs(dbha_version="v2"))
        with patch.object(failover_drill_dbha.HADBApiV2, "switch_queue", side_effect=Exception("down")) as v2:
            assert service._schedule(data, None) is True

        service.log_exception.assert_called_once()
        service.finish_schedule.assert_not_called()
        assert data.outputs["loop_count"] == 2
        assert (v2.call_args.kwargs["timeout"], v2.call_args.kwargs["retry_times"]) == (10, 1)

    def test_default_is_v1_and_passes_full_kwargs(self):
        service = _service()
        data = FakeData(_kwargs())
        resp = {"code": 0, "msg": "ok", "data": [{"ip": "1.1.1.1", "port": 30000}]}
        with patch.object(failover_drill_dbha.HADBApi, "switch_queue", return_value=resp) as v1, patch.object(
            failover_drill_dbha.HADBApiV2, "switch_queue"
        ) as v2:
            service._schedule(data, None)

        service.finish_schedule.assert_called_once()
        v2.assert_not_called()
        query_args = v1.call_args.kwargs["params"]["query_args"]
        assert query_args["cloud_id"] == 0
        assert query_args["ip"] == "1.1.1.1"
        assert query_args["main_task_id"] == "task"
