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

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.input_buffer import sqlserver_input_buffer

MODULE = "backend.dbm_aiagent.mcp_tools.sqlserver.impl.input_buffer"


class TestInputBufferValidation:
    """input_buffer 入参校验（在解析实例前即失败，不依赖 DB）"""

    def test_empty_session_ids_raises(self):
        with pytest.raises(DBMMcpBaseException, match="session_ids"):
            sqlserver_input_buffer("test.db", [])

    def test_non_int_session_id_raises(self):
        with pytest.raises(DBMMcpBaseException, match="invalid session_id"):
            sqlserver_input_buffer("test.db", ["1"])

    def test_bool_session_id_raises(self):
        # bool 是 int 的子类，必须显式排除
        with pytest.raises(DBMMcpBaseException, match="invalid session_id"):
            sqlserver_input_buffer("test.db", [True])

    def test_session_id_low_raises(self):
        with pytest.raises(DBMMcpBaseException, match="out of range"):
            sqlserver_input_buffer("test.db", [0])

    def test_session_id_high_raises(self):
        with pytest.raises(DBMMcpBaseException, match="out of range"):
            sqlserver_input_buffer("test.db", [32768])

    def test_too_many_session_ids_raises(self):
        with pytest.raises(DBMMcpBaseException, match="max batch"):
            sqlserver_input_buffer("test.db", list(range(1, 102)))

    def test_max_event_info_chars_low_raises(self):
        with pytest.raises(DBMMcpBaseException, match="max_event_info_chars"):
            sqlserver_input_buffer("test.db", [1], max_event_info_chars=255)

    def test_max_event_info_chars_high_raises(self):
        with pytest.raises(DBMMcpBaseException, match="max_event_info_chars"):
            sqlserver_input_buffer("test.db", [1], max_event_info_chars=32768)


class TestInputBufferSuccessPath:
    """input_buffer 成功路径：验证会话上下文解析 + 脱敏联动 + sp_executesql 标记"""

    @patch(f"{MODULE}.DRSApi")
    @patch(f"{MODULE}.resolve_sqlserver_addresses")
    def test_success_path_redacts_event_info(self, mock_resolve, mock_drs):
        mock_resolve.return_value = (0, [{"address": "1.1.1.1:1433", "role": "master"}])
        mock_drs.sqlserver_sys_read_rpc.return_value = [
            {
                "error_msg": "",
                "cmd_results": [
                    {
                        "error_msg": "",
                        "table_data": [
                            {
                                "session_id": 51,
                                "login_name": "sa",
                                "host_name": "h1",
                                "program_name": "p1",
                                "database_name": "db1",
                            }
                        ],
                    },
                    {
                        "error_msg": "",
                        "table_data": [
                            {"EventType": "Language Event", "EventInfo": "SELECT * FROM u WHERE phone='13800138000'"}
                        ],
                    },
                ],
            }
        ]

        result = sqlserver_input_buffer("test.db", [51])

        assert result["session_count"] == 1
        assert result["address"] == "1.1.1.1:1433"
        assert result["role"] == "master"

        ib = result["input_buffers"][0]
        assert ib["session_id"] == 51
        assert ib["login_name"] == "sa"
        # 脱敏联动：event_info 中的手机号被抹除
        assert "13800138000" not in ib["event_info"]
        assert ib["is_sp_executesql"] == 0
        assert ib["event_info_truncated"] == 0

    @patch(f"{MODULE}.DRSApi")
    @patch(f"{MODULE}.resolve_sqlserver_addresses")
    def test_sp_executesql_flag(self, mock_resolve, mock_drs):
        mock_resolve.return_value = (0, [{"address": "1.1.1.1:1433", "role": "master"}])
        mock_drs.sqlserver_sys_read_rpc.return_value = [
            {
                "error_msg": "",
                "cmd_results": [
                    {"error_msg": "", "table_data": [{"session_id": 51, "login_name": "sa"}]},
                    {
                        "error_msg": "",
                        "table_data": [{"EventType": "RPC Event", "EventInfo": "sp_executesql (@P1 int)SELECT 1"}],
                    },
                ],
            }
        ]

        result = sqlserver_input_buffer("test.db", [51])
        assert result["input_buffers"][0]["is_sp_executesql"] == 1

    @patch(f"{MODULE}.DRSApi")
    @patch(f"{MODULE}.resolve_sqlserver_addresses")
    def test_dbcc_error_raises(self, mock_resolve, mock_drs):
        mock_resolve.return_value = (0, [{"address": "1.1.1.1:1433", "role": "master"}])
        mock_drs.sqlserver_sys_read_rpc.return_value = [
            {
                "error_msg": "",
                "cmd_results": [
                    {"error_msg": "", "table_data": [{"session_id": 51, "login_name": "sa"}]},
                    {"error_msg": "DBCC failed", "table_data": []},
                ],
            }
        ]

        with pytest.raises(DBMMcpBaseException, match="DBCC INPUTBUFFER"):
            sqlserver_input_buffer("test.db", [51])
