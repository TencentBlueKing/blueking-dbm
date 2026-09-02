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

from unittest import TestCase

from backend.flow.utils.mysql.dts.precheck.base import CheckContext
from backend.flow.utils.mysql.dts.precheck.collector import Endpoint
from backend.flow.utils.mysql.dts.precheck.items.advanced_objects import (
    DISPLAY_LIMIT,
    ObjectKind,
    ObjectRow,
    _forbid,
    run,
)
from backend.flow.utils.mysql.dts.precheck.scope import SyncScope


class AdvancedObjectRuleTest(TestCase):
    def test_all_three_forbidden_kinds_fail(self):
        for kind in (ObjectKind.FUNCTION, ObjectKind.TRIGGER, ObjectKind.EVENT):
            with self.subTest(kind=kind):
                result = _forbid([ObjectRow("app", "object_1")], kind)
                self.assertFalse(result.ok)
                self.assertEqual(
                    result.code,
                    f"advanced_objects.forbid_{kind.value}",
                )

    def test_empty_forbidden_kind_passes(self):
        self.assertTrue(_forbid([], ObjectKind.FUNCTION).ok)

    def test_display_is_truncated_but_total_is_complete(self):
        rows = [ObjectRow("app", f"fn_{index}") for index in range(DISPLAY_LIMIT + 3)]
        result = _forbid(rows, ObjectKind.FUNCTION)
        self.assertEqual(result.details["total"], DISPLAY_LIMIT + 3)
        self.assertEqual(len(result.details["displayed"]), DISPLAY_LIMIT)
        self.assertTrue(result.details["truncated"])

    def test_run_does_not_query_procedures_and_system_schemas(self):
        class Collector:
            endpoint = Endpoint("127.0.0.1", 3306, 0, 1)

            def __init__(self):
                self.sqls = []

            def user_schemas(self):
                return ["mysql", "app"]

            def query(self, sql):
                self.sqls.append(sql)
                return []

        collector = Collector()
        results = run(CheckContext(source=collector, target=collector, scope=SyncScope()))
        self.assertEqual(len(results), 3)
        self.assertTrue(all(result.ok for result in results))
        self.assertTrue(all("'app'" in sql and "'mysql'" not in sql for sql in collector.sqls))
        self.assertTrue(all("PROCEDURE" not in sql for sql in collector.sqls))

    def test_route_scope_only_queries_source_database(self):
        class Collector:
            endpoint = Endpoint("127.0.0.1", 3306, 0, 1)

            def user_schemas(self):
                return ["app", "other"]

            def query(self, sql):
                if "'other'" in sql:
                    raise AssertionError("out-of-scope database was queried")
                return []

        scope = SyncScope(
            do_dbs=["other"],
            table_routes=[{"source_db": "app", "target_db": "renamed"}],
        )
        self.assertTrue(
            all(result.ok for result in run(CheckContext(source=Collector(), target=Collector(), scope=scope)))
        )
