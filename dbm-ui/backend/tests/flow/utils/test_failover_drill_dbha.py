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

import pytest

from backend.flow.utils import failover_drill_dbha as mod

START = "2026-01-01T00:00:00Z"
END = "2026-01-01T08:00:00Z"
RECORD = {"ip": "1.1.1.1", "slave_ip": "2.2.2.2", "port": 30000, "status": "success"}


class TestQuerySwitchQueue:
    def test_v1_uses_hadb_v1_with_msg_shell(self):
        with patch.object(
            mod.HADBApi, "switch_queue", return_value={"code": 0, "msg": "ok", "data": [RECORD]}
        ) as v1, patch.object(mod.HADBApiV2, "switch_queue") as v2:
            code, msg, data = mod.query_switch_queue(
                "v1", 3, START, END, extra_v1_args={"cloud_id": 0, "ip": "1.1.1.1"}
            )

        assert (code, msg, data) == (0, "ok", [RECORD])
        v2.assert_not_called()
        query_args = v1.call_args.kwargs["params"]["query_args"]
        assert query_args == {
            "app": "3",
            "switch_start_time": START,
            "switch_finished_time": END,
            "cloud_id": 0,
            "ip": "1.1.1.1",
        }
        assert v1.call_args.kwargs["params"]["name"] == "query_switch_queue"
        assert v1.call_args.kwargs["raw"] is True

    def test_v2_uses_hadb_v2_with_message_shell_and_no_extra_keys(self):
        with patch.object(
            mod.HADBApiV2, "switch_queue", return_value={"code": 0, "message": "ok", "data": [RECORD]}
        ) as v2, patch.object(mod.HADBApi, "switch_queue") as v1:
            code, msg, data = mod.query_switch_queue(
                "v2", 3, START, END, extra_v1_args={"cloud_id": 0, "ip": "1.1.1.1"}
            )

        assert (code, msg, data) == (0, "ok", [RECORD])
        v1.assert_not_called()
        assert v2.call_args.kwargs["params"]["query_args"] == {
            "app": "3",
            "switch_start_time": START,
            "switch_finished_time": END,
        }

    def test_missing_data_returns_empty_list(self):
        with patch.object(mod.HADBApiV2, "switch_queue", return_value={"code": 1, "message": "bad", "data": None}):
            assert mod.query_switch_queue("v2", 3, START, END) == (1, "bad", [])

    def test_retry_times_override_is_restored_on_shared_client(self):
        with patch.object(mod.HADBApiV2, "switch_queue") as v2:
            v2.max_retry_times = 3

            def call(**kwargs):
                v2.max_retry_times = kwargs["retry_times"]
                raise Exception("down")

            v2.side_effect = call
            with pytest.raises(Exception, match="down"):
                mod.query_switch_queue("v2", 3, START, END, timeout=10, retry_times=1)

            assert v2.max_retry_times == 3


class TestGetDbhaV2ServiceIps:
    def test_returns_deduped_top_level_ips(self):
        resp = {
            "code": 0,
            "message": "",
            "data": {
                "servers": [{"role": "admin", "ips": ["2.2.2.2"]}],
                "ips": ["2.2.2.2", "3.3.3.3", "2.2.2.2", ""],
            },
        }
        with patch.object(mod.HADBApiV2, "ha_servers", return_value=resp) as ha_servers:
            assert mod.get_dbha_v2_service_ips(0, 1) == ["2.2.2.2", "3.3.3.3"]

        ha_servers.assert_called_once_with(params={}, raw=True)

    def test_falls_back_to_servers_ips_when_top_level_ips_missing(self):
        resp = {
            "code": 0,
            "message": "",
            "data": {
                "servers": [
                    {"role": "admin", "ips": ["2.2.2.2"]},
                    {"role": "analysis", "ips": ["2.2.2.2", "3.3.3.3"]},
                ],
                "ips": [],
            },
        }
        with patch.object(mod.HADBApiV2, "ha_servers", return_value=resp):
            assert mod.get_dbha_v2_service_ips(0, 1) == ["2.2.2.2", "3.3.3.3"]

    @pytest.mark.parametrize(
        "resp",
        [
            {"code": 1, "message": "bad", "data": {"ips": ["2.2.2.2"]}},
            {"code": 0, "message": "", "data": {"servers": [], "ips": []}},
            {"code": 0, "message": "", "data": None},
            None,
        ],
    )
    def test_unusable_response_returns_empty(self, resp):
        with patch.object(mod.HADBApiV2, "ha_servers", return_value=resp):
            assert mod.get_dbha_v2_service_ips(0, 1) == []

    def test_request_error_logs_and_returns_empty(self):
        with patch.object(mod.HADBApiV2, "ha_servers", side_effect=Exception("ha-servers down")), patch.object(
            mod.logger, "warning"
        ) as warn:
            assert mod.get_dbha_v2_service_ips(0, 1) == []

        warn.assert_called_once()
        assert "ha-servers down" in str(warn.call_args.args[-1])

    def test_invalid_ips_are_discarded_with_warning(self):
        resp = {
            "code": 0,
            "message": "",
            "data": {
                "ips": ["2.2.2.2", "2.2.2.2:8089", "bad-host", "3.3.3.3; rm -rf /", "3.3.3.3"],
            },
        }
        with patch.object(mod.HADBApiV2, "ha_servers", return_value=resp), patch.object(mod.logger, "warning") as warn:
            assert mod.get_dbha_v2_service_ips(0, 1) == ["2.2.2.2", "3.3.3.3"]

        assert warn.call_count == 3

    def test_all_invalid_ips_returns_empty(self):
        resp = {
            "code": 0,
            "message": "",
            "data": {"ips": ["2.2.2.2:8089", "not-an-ip"]},
        }
        with patch.object(mod.HADBApiV2, "ha_servers", return_value=resp):
            assert mod.get_dbha_v2_service_ips(0, 1) == []
