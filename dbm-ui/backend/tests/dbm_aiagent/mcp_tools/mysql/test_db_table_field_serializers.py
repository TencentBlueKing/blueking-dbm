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

import pytest

from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_construct_rollback_bill import (
    SubmitBillMySQLConstructRollbackInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.sql_syntax_check import ParseSqlExecuteObjectSerializer

INJECTION_PAYLOADS = ["' OR 1=1 -- ", "a' or sleep(5) or '", "a\\", "a b"]

ROLLBACK_PARAMS = {
    "bk_biz_id": 1,
    "cluster_domain": "src.db",
    "target_cluster_domain": "dst.db",
    "databases": ["db%"],
    "tables": ["*"],
}


class TestConstructRollbackInputSerializer:
    def test_valid_patterns(self):
        slz = SubmitBillMySQLConstructRollbackInputSerializer(data={**ROLLBACK_PARAMS, "databases": ["db%", "app_?"]})

        assert slz.is_valid(), slz.errors

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    @pytest.mark.parametrize("field", ["databases", "tables"])
    def test_injection_rejected(self, payload, field):
        slz = SubmitBillMySQLConstructRollbackInputSerializer(data={**ROLLBACK_PARAMS, field: [payload]})

        assert not slz.is_valid()
        assert field in slz.errors


class TestParseSqlExecuteObjectSerializer:
    def test_valid_patterns(self):
        slz = ParseSqlExecuteObjectSerializer(data={"dbnames": ["*"], "ignore_dbnames": ["db_bak", "app_?"]})

        assert slz.is_valid(), slz.errors

    @pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
    @pytest.mark.parametrize("field", ["dbnames", "ignore_dbnames"])
    def test_injection_rejected(self, payload, field):
        data = {"dbnames": ["db%"], "ignore_dbnames": [], field: [payload]}
        slz = ParseSqlExecuteObjectSerializer(data=data)

        assert not slz.is_valid()
        assert field in slz.errors
