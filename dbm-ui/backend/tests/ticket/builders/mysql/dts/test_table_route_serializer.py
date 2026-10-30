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

from backend.ticket.builders.mysql.dts.mysql_dts_tickets import TableRouteSerializer

SOURCE_FIELDS = ["source_db", "source_db_pattern", "source_table", "source_table_pattern"]


class TestTableRouteSerializer:
    @pytest.mark.parametrize(
        "route",
        [
            {"source_db": "db_old", "source_table": "*", "target_db": "db_new"},
            {"source_db_pattern": "shard_*", "source_table_pattern": "t_?"},
            {"source_db_pattern": "db%", "source_table_pattern": "*"},
            {"source_db": "mysql", "source_table": "user"},
            {"source_db": "app-1", "source_db_pattern": "", "source_table": "", "source_table_pattern": ""},
        ],
    )
    def test_valid_routes(self, route):
        slz = TableRouteSerializer(data=route)

        assert slz.is_valid(), slz.errors

    @pytest.mark.parametrize("field", SOURCE_FIELDS)
    @pytest.mark.parametrize("payload", ["db' OR 1=1 -- ", "t$1", "tb.old", "表1", "a b", "a\\"])
    def test_invalid_source_names_rejected(self, field, payload):
        slz = TableRouteSerializer(data={field: payload})

        assert not slz.is_valid()
        assert field in slz.errors

    def test_target_names_not_checked(self):
        slz = TableRouteSerializer(data={"source_db": "db_old", "target_db": "db.new", "target_table": "t$1"})

        assert slz.is_valid(), slz.errors
