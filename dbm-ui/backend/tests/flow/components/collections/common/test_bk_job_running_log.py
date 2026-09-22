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

from backend.flow.plugins.components.collections.common.base_service import BkJobService


class _JobSvc(BkJobService):
    def _execute(self, data, parent_data):
        return True


def _make(now_ts, kwargs=None):
    kwargs = kwargs if kwargs is not None else {"node_name": "介质下发"}
    data = SimpleNamespace(inputs=SimpleNamespace(kwargs=kwargs))
    svc = object.__new__(_JobSvc)
    svc.log_info = MagicMock()
    return svc, data, kwargs, now_ts


class TestBkJobRunningLogThrottle(SimpleTestCase):
    def test_first_poll_logs_then_5s_is_silent(self):
        t0 = 1_700_000_000
        svc, data, kwargs, _ = _make(t0)
        with patch("backend.flow.plugins.components.collections.common.base_service.time.time", return_value=t0):
            svc._maybe_log_job_running(data, kwargs, "介质下发")
        self.assertEqual(svc.log_info.call_count, 1)
        self.assertEqual(kwargs["介质下发_job_running_last_log_ts"], t0)
        self.assertIs(data.inputs.kwargs, kwargs)

        with patch("backend.flow.plugins.components.collections.common.base_service.time.time", return_value=t0 + 5):
            svc._maybe_log_job_running(data, kwargs, "介质下发")
        self.assertEqual(svc.log_info.call_count, 1)

        with patch("backend.flow.plugins.components.collections.common.base_service.time.time", return_value=t0 + 60):
            svc._maybe_log_job_running(data, kwargs, "介质下发")
        self.assertEqual(svc.log_info.call_count, 2)

    def test_after_one_hour_interval_becomes_five_minutes(self):
        t0 = 1_700_000_000
        svc, data, kwargs, _ = _make(t0)
        with patch("backend.flow.plugins.components.collections.common.base_service.time.time", return_value=t0):
            svc._maybe_log_job_running(data, kwargs, "介质下发")

        t_hour = t0 + 3600
        with patch("backend.flow.plugins.components.collections.common.base_service.time.time", return_value=t_hour):
            svc._maybe_log_job_running(data, kwargs, "介质下发")
        self.assertEqual(svc.log_info.call_count, 2)

        with patch(
            "backend.flow.plugins.components.collections.common.base_service.time.time", return_value=t_hour + 60
        ):
            svc._maybe_log_job_running(data, kwargs, "介质下发")
        self.assertEqual(svc.log_info.call_count, 2)

        with patch(
            "backend.flow.plugins.components.collections.common.base_service.time.time", return_value=t_hour + 300
        ):
            svc._maybe_log_job_running(data, kwargs, "介质下发")
        self.assertEqual(svc.log_info.call_count, 3)
