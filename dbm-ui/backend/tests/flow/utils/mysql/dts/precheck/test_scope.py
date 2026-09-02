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

from backend.flow.utils.mysql.dts.precheck.collector import PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.scope import SyncScope, resolve_migration_databases, resolve_schemas


class ResolveSchemasTest(TestCase):
    schemas = ["app", "other", "mysql", "information_schema"]

    def test_table_routes_take_precedence_over_do_dbs(self):
        scope = SyncScope(
            do_dbs=["other"],
            table_routes=[{"source_db": "app", "target_db": "renamed"}],
        )
        self.assertEqual(resolve_schemas(scope, self.schemas), ["app"])

    def test_ignore_databases(self):
        scope = SyncScope(do_dbs=["*"], ignore_dbs=["other"])
        self.assertEqual(resolve_schemas(scope, self.schemas), ["app"])

    def test_unspecified_scope_means_all_user_schemas(self):
        self.assertEqual(resolve_schemas(SyncScope(), self.schemas), ["app", "other"])

    def test_table_level_ignore_is_applied_at_database_granularity(self):
        scope = SyncScope(ignore_tables=[{"db": "other", "table": "t1"}])
        self.assertEqual(resolve_schemas(scope, self.schemas), ["app"])

    def test_empty_resolved_scope_fails(self):
        with self.assertRaises(PrecheckCollectError):
            resolve_schemas(SyncScope(do_dbs=["missing"]), self.schemas)

    def test_system_schemas_are_always_excluded(self):
        scope = SyncScope(do_dbs=["mysql", "app"])
        self.assertEqual(resolve_schemas(scope, self.schemas), ["app"])

    def test_source_tables_still_honor_ignore_dbs(self):
        scope = SyncScope(source_tables=[{"db": "*"}], ignore_dbs=["other"])
        self.assertEqual(resolve_migration_databases(scope, self.schemas), ["app"])
