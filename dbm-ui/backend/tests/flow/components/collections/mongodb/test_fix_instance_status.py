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

from backend.db_meta.enums.cluster_entry_type import ClusterEntryType
from backend.flow.consts import InstanceStatus, MongoDBClusterRole
from backend.flow.plugins.components.collections.mongodb import fix_instance_status as mod
from backend.flow.utils.clb_manage import CLBManage


class TestCLBManageGetRsWithResponse:
    def test_returns_true_on_code_zero(self):
        mgr = CLBManage("lb-1", "127.0.0.10", "lbl-1", "ap-guangzhou")
        payload = {"code": 0, "message": "ok", "data": {"ips": ["127.0.0.1:27021"]}}
        with patch("backend.flow.utils.clb_manage.NameServiceApi.clb_get_target_private_ips", return_value=payload):
            ok, res = mgr.get_clb_rs_with_response()
        assert ok is True
        assert res == payload

    def test_returns_false_on_nonzero_code(self):
        mgr = CLBManage("lb-1", "127.0.0.10", "lbl-1", "ap-guangzhou")
        payload = {"code": 1, "message": "clb error"}
        with patch("backend.flow.utils.clb_manage.NameServiceApi.clb_get_target_private_ips", return_value=payload):
            ok, res = mgr.get_clb_rs_with_response()
        assert ok is False
        assert res == payload


class TestFixInstanceClbEntry:
    def test_already_exists_skips_add_and_sleep(self):
        clb_manage = MagicMock()
        clb_manage.get_clb_rs_with_response.return_value = (
            True,
            {"code": 0, "data": {"ips": ["127.0.0.1:27021", "127.0.0.2:27021"]}},
        )

        with (
            patch.object(mod, "get_clb_by_ip", return_value=clb_manage),
            patch.object(mod.time, "sleep") as mock_sleep,
        ):
            code, msg = mod.fix_instance_clb_entry(
                clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"]
            )

        assert code == 2
        assert msg == "clb rs already exists"
        clb_manage.add_clb_rs_with_response.assert_not_called()
        mock_sleep.assert_not_called()

    def test_add_then_sleep_and_verify_success(self):
        clb_manage = MagicMock()
        clb_manage.get_clb_rs_with_response.side_effect = [
            (True, {"code": 0, "data": {"ips": ["127.0.0.2:27021"]}}),
            (True, {"code": 0, "data": {"ips": ["127.0.0.2:27021", "127.0.0.1:27021"]}}),
        ]
        clb_manage.add_clb_rs_with_response.return_value = (True, {"code": 0, "message": "ok"})

        with (
            patch.object(mod, "get_clb_by_ip", return_value=clb_manage),
            patch.object(mod.time, "sleep") as mock_sleep,
        ):
            code, msg = mod.fix_instance_clb_entry(
                clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"]
            )

        assert code == 1
        assert msg == "success"
        clb_manage.add_clb_rs_with_response.assert_called_once_with(instance_list=["127.0.0.1:27021"])
        mock_sleep.assert_called_once_with(2)
        assert clb_manage.get_clb_rs_with_response.call_count == 2

    def test_initial_get_retries_on_network_error_then_succeeds(self):
        clb_manage = MagicMock()
        clb_manage.get_clb_rs_with_response.side_effect = [
            ConnectionError("network reset"),
            (True, {"code": 0, "data": {"ips": ["127.0.0.1:27021"]}}),
        ]

        with (
            patch.object(mod, "get_clb_by_ip", return_value=clb_manage),
            patch.object(mod.time, "sleep") as mock_sleep,
        ):
            code, msg = mod.fix_instance_clb_entry(
                clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"]
            )

        assert code == 2
        assert msg == "clb rs already exists"
        assert clb_manage.get_clb_rs_with_response.call_count == 2
        mock_sleep.assert_called_once_with(2)

    def test_add_retries_on_network_error_then_succeeds(self):
        clb_manage = MagicMock()
        clb_manage.get_clb_rs_with_response.side_effect = [
            (True, {"code": 0, "data": {"ips": ["127.0.0.2:27021"]}}),
            (True, {"code": 0, "data": {"ips": ["127.0.0.2:27021"]}}),
            (True, {"code": 0, "data": {"ips": ["127.0.0.2:27021", "127.0.0.1:27021"]}}),
        ]
        clb_manage.add_clb_rs_with_response.side_effect = [
            ConnectionError("connection reset"),
            (True, {"code": 0, "message": "ok"}),
        ]

        with (
            patch.object(mod, "get_clb_by_ip", return_value=clb_manage),
            patch.object(mod.time, "sleep") as mock_sleep,
        ):
            code, msg = mod.fix_instance_clb_entry(
                clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"]
            )

        assert code == 1
        assert msg == "success"
        assert clb_manage.add_clb_rs_with_response.call_count == 2
        assert mock_sleep.call_count == 2

    def test_add_timeout_already_applied_confirmed_before_retry(self):
        clb_manage = MagicMock()
        clb_manage.get_clb_rs_with_response.side_effect = [
            (True, {"code": 0, "data": {"ips": ["127.0.0.2:27021"]}}),
            (True, {"code": 0, "data": {"ips": ["127.0.0.2:27021", "127.0.0.1:27021"]}}),
        ]
        clb_manage.add_clb_rs_with_response.side_effect = TimeoutError("read timed out")

        with (
            patch.object(mod, "get_clb_by_ip", return_value=clb_manage),
            patch.object(mod.time, "sleep") as mock_sleep,
        ):
            code, msg = mod.fix_instance_clb_entry(
                clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"]
            )

        assert code == 1
        assert msg == "success"
        assert clb_manage.add_clb_rs_with_response.call_count == 1
        mock_sleep.assert_called_once_with(2)

    def test_add_api_returns_false_exhausts_retries_and_reports_failure(self):
        clb_manage = MagicMock()
        clb_manage.get_clb_rs_with_response.return_value = (True, {"code": 0, "data": {"ips": []}})
        clb_manage.add_clb_rs_with_response.return_value = (
            False,
            {"code": 1, "message": "invalid ip format"},
        )

        with (
            patch.object(mod, "get_clb_by_ip", return_value=clb_manage),
            patch.object(mod.time, "sleep") as mock_sleep,
        ):
            code, msg = mod.fix_instance_clb_entry(
                clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"]
            )

        assert code == 0
        assert "add clb rs failed" in msg
        assert "invalid ip format" in msg
        assert clb_manage.add_clb_rs_with_response.call_count == 3
        assert mock_sleep.call_count == 2

    def test_verify_retries_on_transient_delay_then_succeeds(self):
        clb_manage = MagicMock()
        clb_manage.get_clb_rs_with_response.side_effect = [
            (True, {"code": 0, "data": {"ips": ["127.0.0.2:27021"]}}),
            ConnectionError("transient verify error"),
            (True, {"code": 0, "data": {"ips": ["127.0.0.2:27021"]}}),
            (True, {"code": 0, "data": {"ips": ["127.0.0.2:27021", "127.0.0.1:27021"]}}),
        ]
        clb_manage.add_clb_rs_with_response.return_value = (True, {"code": 0, "message": "ok"})

        with (
            patch.object(mod, "get_clb_by_ip", return_value=clb_manage),
            patch.object(mod.time, "sleep") as mock_sleep,
        ):
            code, msg = mod.fix_instance_clb_entry(
                clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"]
            )

        assert code == 1
        assert msg == "success"
        assert mock_sleep.call_count == 3

    def test_verify_after_sleep_still_missing_reports_failure(self):
        clb_manage = MagicMock()
        clb_manage.get_clb_rs_with_response.return_value = (
            True,
            {"code": 0, "data": {"ips": ["127.0.0.2:27021"]}},
        )
        clb_manage.add_clb_rs_with_response.return_value = (True, {"code": 0, "message": "ok"})

        with (
            patch.object(mod, "get_clb_by_ip", return_value=clb_manage),
            patch.object(mod.time, "sleep") as mock_sleep,
        ):
            code, msg = mod.fix_instance_clb_entry(
                clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"]
            )

        assert code == 0
        assert "clb rs not found after add" in msg
        assert "127.0.0.1:27021" in msg
        assert mock_sleep.call_count == 3

    def test_initial_get_clb_rs_failure_exhausts_retries_and_reports_failure(self):
        clb_manage = MagicMock()
        clb_manage.get_clb_rs_with_response.return_value = (False, {"code": 500, "message": "timeout"})

        with (
            patch.object(mod, "get_clb_by_ip", return_value=clb_manage),
            patch.object(mod.time, "sleep") as mock_sleep,
        ):
            code, msg = mod.fix_instance_clb_entry(
                clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"]
            )

        assert code == 0
        assert "get clb rs failed" in msg
        assert clb_manage.get_clb_rs_with_response.call_count == 3
        clb_manage.add_clb_rs_with_response.assert_not_called()
        assert mock_sleep.call_count == 2

    def test_verify_get_clb_rs_failure_exhausts_retries_and_reports_failure(self):
        clb_manage = MagicMock()
        clb_manage.get_clb_rs_with_response.side_effect = [
            (True, {"code": 0, "data": {"ips": None}}),
            (False, {"code": 500, "message": "query failed"}),
            (False, {"code": 500, "message": "query failed"}),
            (False, {"code": 500, "message": "query failed"}),
        ]
        clb_manage.add_clb_rs_with_response.return_value = (True, {"code": 0, "message": "ok"})

        with (
            patch.object(mod, "get_clb_by_ip", return_value=clb_manage),
            patch.object(mod.time, "sleep") as mock_sleep,
        ):
            code, msg = mod.fix_instance_clb_entry(
                clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"]
            )

        assert code == 0
        assert "verify clb rs failed" in msg
        assert mock_sleep.call_count == 3


class TestFixInstanceClusterEntryMongosClb:
    def test_mongos_clb_uses_colon_format_and_blocks_status_update_on_failure(self):
        cluster = SimpleNamespace(bk_biz_id=3)
        clb_entry = SimpleNamespace(cluster_entry_type=ClusterEntryType.CLB.value, entry="127.0.0.10")
        proxy = MagicMock()
        proxy.status = InstanceStatus.UNAVAILABLE.value
        proxy.cluster.first.return_value = cluster
        proxy.bind_entry.all.return_value = [clb_entry]

        svc = mod.ExecFixInstanceStatusOperation()
        svc.log_info = MagicMock()
        data = MagicMock()
        data.outputs = {}
        data.get_one_of_inputs.return_value = {
            "trans_data_var": {
                "instance": {
                    "ip": "127.0.0.1",
                    "port": 27021,
                    "bk_cloud_id": 0,
                    "role": MongoDBClusterRole.Mongos.value,
                }
            }
        }

        with (
            patch.object(mod.ProxyInstance.objects, "get", return_value=proxy),
            patch.object(mod, "fix_instance_clb_entry", return_value=(0, "add clb rs failed")) as mock_fix_clb,
        ):
            ok = svc._execute(data, None)

        assert ok is False
        mock_fix_clb.assert_called_once_with(clb_ip="127.0.0.10", bk_cloud_id=0, rs_instance_list=["127.0.0.1:27021"])
        assert proxy.status == InstanceStatus.UNAVAILABLE.value
        proxy.save.assert_not_called()
