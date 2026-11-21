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
from backend.flow.utils.mysql.dts.precheck.collector import PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.items.target_schema import run
from backend.flow.utils.mysql.dts.precheck.scope import SyncScope


class _Collector:
    def __init__(self, databases, tables=None):
        self.databases = databases
        self.tables = tables or {}
        self.queried = False

    def user_schemas(self):
        return list(self.databases)

    def query(self, _sql):
        self.queried = True
        return [
            {"TABLE_SCHEMA": database, "TABLE_NAME": table}
            for database, tables in self.tables.items()
            for table in tables
        ]


def _run(source, target, source_tables):
    return run(CheckContext(source=source, target=target, scope=SyncScope(source_tables=source_tables)))


class TargetSchemaTest(TestCase):
    def test_database_only_fails_when_target_has_same_db(self):
        source = _Collector(["app", "pay"])
        target = _Collector(["app"])
        results = _run(source, target, [{"db": "app"}, {"db": "pay"}])

        self.assertFalse(results[0].ok)
        self.assertEqual(results[0].details["target_conflict_databases"], ["app"])
        self.assertEqual(results[0].details["source_missing_databases"], [])
        self.assertFalse(source.queried)
        self.assertFalse(target.queried)

    def test_database_only_passes_when_target_has_no_db(self):
        source = _Collector(["app"])
        target = _Collector(["other"])
        results = _run(source, target, [{"db": "app"}])

        self.assertTrue(results[0].ok)
        self.assertEqual(results[0].code, "target_schema.ok")

    def test_database_pattern_expands_on_source(self):
        source = _Collector(["app_order", "app_user", "other"])
        target = _Collector(["app_order"])
        results = _run(source, target, [{"db": "app_*"}])

        self.assertEqual(results[0].details["target_conflict_databases"], ["app_order"])

    def test_one_database_with_multiple_tables_reports_target_conflict(self):
        source = _Collector(["app"], {"app": ["t_order", "t_user"]})
        target = _Collector(["app"], {"app": ["t_order"]})
        results = _run(source, target, [{"db": "app", "tables": ["t_order", "t_user"]}])

        self.assertEqual(results[0].details["target_conflict_tables"], ["app.t_order"])
        self.assertEqual(results[0].details["source_missing_tables"], [])
        self.assertEqual(results[0].details["target_conflict_databases"], [])

    def test_table_mode_allows_target_database_without_same_tables(self):
        source = _Collector(["app"], {"app": ["t_order", "t_user"]})
        target = _Collector(["app"], {"app": ["t_other"]})
        results = _run(source, target, [{"db": "app", "tables": ["t_order", "t_user"]}])

        self.assertTrue(results[0].ok)

    def test_multiple_databases_and_table_pattern(self):
        source = _Collector(
            ["app", "pay"],
            {"app": ["t_order", "t_user"], "pay": ["order_1", "order_2"]},
        )
        target = _Collector(
            ["app", "pay"],
            {"app": ["t_other"], "pay": ["order_1"]},
        )
        results = _run(
            source,
            target,
            [
                {"db": "app", "tables": ["t_*"]},
                {"db": "pay%", "tables": ["order_*"]},
            ],
        )

        self.assertEqual(results[0].details["target_conflict_tables"], ["pay.order_1"])

    def test_single_table_field_is_checked(self):
        source = _Collector(["app"], {"app": ["t_order"]})
        target = _Collector(["app"], {"app": ["t_order"]})
        results = _run(source, target, [{"db": "app", "table": "t_order"}])

        self.assertEqual(results[0].details["target_conflict_tables"], ["app.t_order"])

    def test_unmatched_source_pattern_fails(self):
        results = _run(_Collector(["other"]), _Collector([]), [{"db": "app_*"}])

        self.assertEqual(results[0].details["source_missing_databases"], ["app_*"])

    def test_empty_source_tables_fail_without_query(self):
        source = _Collector([])
        results = _run(source, source, [])

        self.assertEqual(results[0].code, "target_schema.empty")
        self.assertFalse(source.queried)

    def test_query_error_is_a_failure(self):
        class Broken(_Collector):
            def user_schemas(self):
                raise PrecheckCollectError("DRS failed")

        results = _run(Broken([]), Broken([]), [{"db": "app"}])
        self.assertEqual(results[0].code, "target_schema.collect_error")
