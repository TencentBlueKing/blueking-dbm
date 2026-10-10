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
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.components.bknodeman import client
from backend.components.bknodeman.client import (
    BKNodeManJobStatusError,
    _BKNodeManV2Api,
    _BKNodeManV3Api,
    _create_nodeman_api,
)
from backend.exceptions import ApiError
from backend.tests.mock_data.components.nodeman import MockResponse

JobStatusType = _BKNodeManV3Api.JobStatusType


def _release(version, as_default=False, os_type="linux", cpu_arch="amd64"):
    return {
        "release": {
            "name": "bkmonitorbeat",
            "version": version,
            "as_default": as_default,
            "os_type": os_type,
            "cpu_arch": cpu_arch,
            "enabled": True,
        }
    }


def _workflow_response(items):
    return MockResponse(200, {"code": 0, "message": "ok", "data": {"total": len(items), "items": items}})


class TestCreateNodeManApi(SimpleTestCase):
    def test_default_v2(self):
        with patch.object(client.env, "BKNODEMAN_API_VERSION", "v2"):
            self.assertIsInstance(_create_nodeman_api(), _BKNodeManV2Api)

    def test_v3(self):
        with patch.object(client.env, "BKNODEMAN_API_VERSION", "v3"):
            self.assertIsInstance(_create_nodeman_api(), _BKNodeManV3Api)


class TestBKNodeManV2Api(SimpleTestCase):
    def setUp(self):
        self.api = _BKNodeManV2Api()

    def test_get_job_status(self):
        response = MockResponse(200, {"result": True, "code": 0, "data": {"status": "RUNNING"}})
        with patch.object(self.api.job_details, "_send", return_value=response) as mock_send:
            self.assertEqual(self.api.get_job_status(1), JobStatusType.RUNNING)
        mock_send.assert_called_once_with(params={"job_id": 1}, headers={})

    def test_get_job_status_http_error(self):
        with patch.object(self.api.job_details, "_send", return_value=MockResponse(504)):
            with self.assertRaises(BKNodeManJobStatusError) as ctx:
                self.api.get_job_status(1)
        self.assertEqual(ctx.exception.status_code, 504)

    def test_get_job_status_result_false(self):
        response = MockResponse(200, {"result": False, "code": 1, "message": "error"})
        with patch.object(self.api.job_details, "_send", return_value=response):
            with self.assertRaises(BKNodeManJobStatusError) as ctx:
                self.api.get_job_status(1)
        self.assertIsNone(ctx.exception.status_code)

    def test_get_job_url(self):
        with patch.object(client.env, "BK_NODEMAN_URL", "http://nodeman.example.com"):
            self.assertEqual(self.api.get_job_url(1), "http://nodeman.example.com/#/task-list/detail/1")


class TestBKNodeManV3Api(SimpleTestCase):
    def setUp(self):
        self.api = _BKNodeManV3Api()

    def _operate_plugin(self, releases):
        with patch.object(
            self.api, "release_plugin_list", return_value={"items": releases}
        ) as mock_list, patch.object(self.api, "plugin_install", return_value={"workflow_id": "wf-1"}) as mock_install:
            job = self.api.operate_plugin(
                {"job_type": "MAIN_INSTALL_PLUGIN", "plugin_params": {"name": "bkmonitorbeat"}, "bk_host_id": [1, 2]}
            )
        return job, mock_list, mock_install

    def test_operate_plugin_use_default_version(self):
        releases = [
            _release("3.20.0"),
            _release("3.10.0", as_default=True),
            _release("3.10.0", True, cpu_arch="arm64"),
        ]
        job, mock_list, mock_install = self._operate_plugin(releases)

        self.assertEqual(job, {"job_id": "wf-1"})
        mock_list.assert_called_once_with(
            {
                "generation": 2,
                "page": {"offset": 0, "limit": 1000},
                "exact_include_conditions": {"name": ["bkmonitorbeat"], "enabled": [True]},
            }
        )
        mock_install.assert_called_once_with(
            {
                "plugin": [
                    {"bk_host_id": 1, "plugin_name": "bkmonitorbeat", "version": "3.10.0"},
                    {"bk_host_id": 2, "plugin_name": "bkmonitorbeat", "version": "3.10.0"},
                ]
            }
        )

    def test_operate_plugin_without_default_use_latest(self):
        releases = [_release("3.9.0"), _release("3.20.1"), _release("3.10.0")]
        with self.assertLogs(client.logger, level="WARNING") as logs:
            _, _, mock_install = self._operate_plugin(releases)
        self.assertEqual(mock_install.call_args[0][0]["plugin"][0]["version"], "3.20.1")
        self.assertIn("no default version", logs.output[0])

    def test_operate_plugin_multiple_default_use_latest(self):
        releases = [_release("3.9.0", True), _release("3.10.0", True, cpu_arch="arm64")]
        with self.assertLogs(client.logger, level="WARNING"):
            _, _, mock_install = self._operate_plugin(releases)
        self.assertEqual(mock_install.call_args[0][0]["plugin"][0]["version"], "3.10.0")

    def test_operate_plugin_without_release(self):
        with self.assertRaises(ApiError):
            self._operate_plugin([])

    def test_operate_plugin_unsupported_job_type(self):
        with self.assertRaises(ApiError):
            self.api.operate_plugin({"job_type": "MAIN_STOP_PLUGIN", "plugin_params": {"name": "x"}, "bk_host_id": []})

    def test_get_job_status(self):
        cases = {
            "running": JobStatusType.RUNNING,
            "success": JobStatusType.SUCCESS,
            "failed": JobStatusType.FAILED,
            "partial_failed": JobStatusType.FAILED,
        }
        for v3_status, expected in cases.items():
            response = _workflow_response([{"workflow_id": "wf-1", "status": v3_status}])
            with patch.object(self.api.plugin_workflow_list, "_send", return_value=response) as mock_send:
                self.assertEqual(self.api.get_job_status("wf-1"), expected)
            mock_send.assert_called_once_with(
                params={"page": {"offset": 0, "limit": 1}, "exact_include_conditions": {"workflow_id": ["wf-1"]}},
                headers={},
            )

    def test_get_job_status_not_found_is_pending(self):
        with patch.object(self.api.plugin_workflow_list, "_send", return_value=_workflow_response([])):
            self.assertEqual(self.api.get_job_status("wf-1"), JobStatusType.PENDING)

    def test_get_job_status_http_error(self):
        with patch.object(self.api.plugin_workflow_list, "_send", return_value=MockResponse(502)):
            with self.assertRaises(BKNodeManJobStatusError) as ctx:
                self.api.get_job_status("wf-1")
        self.assertEqual(ctx.exception.status_code, 502)

    def test_get_job_url(self):
        with patch.object(client.env, "BK_NODEMGR_URL", "http://nodemgr.example.com"):
            self.assertEqual(
                self.api.get_job_url("wf-1"),
                "http://nodemgr.example.com/#/node-manager/history/detail/wf-1?active=plugin",
            )

    def test_ipchooser_host_details(self):
        host_state = {1: "running", 2: "damaged", 3: "running"}

        def _topo_host_list(params, **kwargs):
            host_ids = params["exact_include_conditions"]["bk_host_id"]
            self.assertLessEqual(len(host_ids), 2)
            return {"items": [{"bk_host_id": i, "state": {"node_status": host_state[i]}} for i in host_ids]}

        params = {"host_list": [{"host_id": i, "meta": {}} for i in (1, 2, 3)], "scope_list": []}
        with patch.object(_BKNodeManV3Api, "PAGE_LIMIT", 2), patch.object(
            self.api, "topo_host_list", side_effect=_topo_host_list
        ) as mock_host_list:
            details = self.api.ipchooser_host_details(params, use_admin=True)

        self.assertEqual(mock_host_list.call_count, 2)
        self.assertEqual(mock_host_list.call_args.kwargs, {"use_admin": True})
        self.assertEqual(
            sorted(details, key=lambda d: d["host_id"]),
            [{"host_id": 1, "alive": 1}, {"host_id": 2, "alive": 0}, {"host_id": 3, "alive": 1}],
        )
