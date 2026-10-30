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

from unittest.mock import Mock, patch

import pytest

from backend.db_services.mysql.remote_service.exceptions import RemoteServiceBaseException
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler

HANDLER_PATH = "backend.db_services.mysql.remote_service.handlers"

INJECTION_PAYLOADS = [
    "' OR 1=1 -- ",
    "a' or sleep(5) or '",
    "a\\",
    "a\x00",
    "db%' union select 1 -- ",
    "a b",
    "a;b",
]
SPECIAL_REAL_DB_NAME = "#mysql50#lost+found"


def mock_rpc(params):
    return [
        {
            "address": params["addresses"][0],
            "error_msg": "",
            "cmd_results": [{"cmd": cmd, "table_data": []} for cmd in params["cmds"]],
        }
    ]


@pytest.fixture
def drs():
    cluster_handler = Mock()
    cluster_handler.cluster.bk_cloud_id = 0
    cluster_handler.cluster_id = 1
    drs_api = Mock()
    drs_api.rpc.side_effect = mock_rpc
    with patch(f"{HANDLER_PATH}.DRSApi", drs_api), patch.object(
        RemoteServiceHandler, "_get_cluster_address", return_value=(cluster_handler, "1.1.1.1:3306")
    ):
        yield drs_api


def executed_cmds(drs_api):
    return [cmd for call in drs_api.rpc.call_args_list for cmd in call.args[0]["cmds"]]


class TestShowDatabaseWithPattern:
    def test_valid_patterns(self, drs):
        RemoteServiceHandler(bk_biz_id=1).show_database_with_pattern(1, ["db%", "app_*", "db?"], ["db_bak"])

        cmds = executed_cmds(drs)
        assert "SCHEMA_NAME like 'db%'" in cmds[0]
        assert "SCHEMA_NAME like 'app\\_%'" in cmds[0]
        assert "SCHEMA_NAME like 'db_'" in cmds[0]
        assert "SCHEMA_NAME like 'db\\_bak'" in cmds[1]

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    @pytest.mark.parametrize("field", ["dbs", "ignore_dbs"])
    def test_injection_rejected(self, drs, payload, field):
        kwargs = {"dbs": ["db%"], "ignore_dbs": [], field: [payload]}

        with pytest.raises(RemoteServiceBaseException):
            RemoteServiceHandler(bk_biz_id=1).show_database_with_pattern(1, **kwargs)
        drs.rpc.assert_not_called()

    def test_show_databases_with_db_patterns_rejected(self, drs):
        infos = [{"cluster_id": 1, "dbs": ["' OR 1=1 -- "], "ignore_dbs": []}]

        with pytest.raises(RemoteServiceBaseException):
            RemoteServiceHandler(bk_biz_id=1).show_databases_with_db_patterns(infos)
        drs.rpc.assert_not_called()


class TestShowTableWithPattern:
    def test_real_db_name_with_special_chars_allowed(self, drs):
        RemoteServiceHandler(bk_biz_id=1).show_table_with_pattern(1, [SPECIAL_REAL_DB_NAME, "db1"], ["tb%"], [])

        assert f"'{SPECIAL_REAL_DB_NAME}'" in executed_cmds(drs)[0]

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    @pytest.mark.parametrize("field", ["tables", "ignore_tables"])
    def test_table_pattern_injection_rejected(self, drs, payload, field):
        kwargs = {"dbs": ["db1"], "tables": ["tb%"], "ignore_tables": [], field: [payload]}

        with pytest.raises(RemoteServiceBaseException):
            RemoteServiceHandler(bk_biz_id=1).show_table_with_pattern(1, **kwargs)
        drs.rpc.assert_not_called()

    @pytest.mark.parametrize("db", ["db1') or sleep(5) -- ", "db1\\", "db1\x00"])
    def test_db_literal_injection_rejected(self, drs, db):
        with pytest.raises(RemoteServiceBaseException):
            RemoteServiceHandler(bk_biz_id=1).show_table_with_pattern(1, [db], ["tb%"], [])
        drs.rpc.assert_not_called()


class TestShowTables:
    def test_real_db_name_with_special_chars_allowed(self, drs):
        RemoteServiceHandler(bk_biz_id=1).show_tables([{"cluster_id": 1, "dbs": [SPECIAL_REAL_DB_NAME]}])

        assert f"table_schema='{SPECIAL_REAL_DB_NAME}'" in executed_cmds(drs)[0]

    @pytest.mark.parametrize("db", ["db1' or '1'='1", "db1\\", "db1\x00"])
    def test_db_literal_injection_rejected(self, drs, db):
        with pytest.raises(RemoteServiceBaseException):
            RemoteServiceHandler(bk_biz_id=1).show_tables([{"cluster_id": 1, "dbs": [db]}])
        drs.rpc.assert_not_called()


class TestValidateTableFields:
    @pytest.fixture
    def cluster(self):
        with patch(f"{HANDLER_PATH}.Cluster") as cluster_model, patch(f"{HANDLER_PATH}.ClusterHandler"):
            cluster_model.objects.get.return_value = Mock(bk_cloud_id=0)
            yield

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    @pytest.mark.parametrize("field", ["tables", "databases"])
    def test_injection_rejected(self, drs, cluster, payload, field):
        info = {"cluster_id": 1, "tables": ["tb1"], "databases": ["db1"], field: [payload]}

        with pytest.raises(RemoteServiceBaseException):
            RemoteServiceHandler(bk_biz_id=1).validate_table_fields(info, ["id"])
        drs.rpc.assert_not_called()
